# Team Member 5 — Compliance and Learning

You are the safety officer and the memory. Content generation without you is just another GPT wrapper. The demo wins when a bad claim is **caught**, the reviewer tags it, and the **next** draft improves.

You do **not** generate marketing copy. You do **not** add FastAPI routes (M1 wires you). You do **not** edit the dashboard.

## Read these first

1. [../00-START-HERE.md](../00-START-HERE.md)
2. [../03-CONTRACTS.md](../03-CONTRACTS.md) — `ComplianceResult`, lessons functions, metrics
3. [../04-WORKFLOW-RULES.md](../04-WORKFLOW-RULES.md)
4. [../06-DEMO-SCRIPT.md](../06-DEMO-SCRIPT.md) — you must FAIL "Guaranteed protection"
5. [../../AGENTS.md](../../AGENTS.md)

Concept.md §8–9 is useful product context. Implement the **three-layer** check described here, not "ask the LLM if it seems fine".

## Your branch

`feat/m5-compliance`

## Files you own

```text
api/agents/compliance.py
api/agents/lessons.py
api/agents/research.py
api/agents/leads.py          # Phase 3
api/rules/banned_terms.yaml
api/rules/fixtures/          # optional HTML snapshots
api/prompts/compliance/
```

## Never touch

```text
api/schemas.py
api/graph.py
api/routes/**
api/agents/content.py
api/agents/localize.py
web/**
```

Need `pyyaml`, `trafilatura`, `google-genai`? Ask M1 to add them.

---

## Function signatures (copy exactly)

```python
# api/agents/compliance.py
from schemas import ComplianceResult

def check_compliance(text: str, brand_id: str, platform: str) -> ComplianceResult:
    ...

# api/agents/lessons.py
def get_relevant_lessons(brand_id: str, platform: str, limit: int = 5) -> list[str]:
    ...

def record_lesson(
    asset_id: str,
    reason_tag: str,
    note: str,
    original: str,
    edited: str | None,
    brand_id: str,
    platform: str | None = None,
) -> None:
    ...

# api/agents/research.py
def scan_competitor(competitor_id: str) -> dict:
    # { competitor_id, hash, changed, summary }
    ...

# api/agents/leads.py  (Phase 3)
def find_leads(brand_id: str, country: str, limit: int = 10) -> list[dict]:
    ...
```

`check_compliance` is **pure**: no DB writes. M1 stores the result.

`record_lesson` / `get_relevant_lessons` **do** talk to Postgres (`lessons` table).

Never raise into the pipeline. On LLM failure: still return the **hard-rule** result (Python scanner). If the scanner found issues, `result="FAIL"`. If not, `result="REVIEW"`, `risk="MEDIUM"`, reason `LLM_UNAVAILABLE`.

---

## Compliance — three layers

```text
text
  → Layer 1 hard-rule scanner (Python, yaml)
  → Layer 2 claim evidence (Phase 2: if a sentence asserts coverage, require it is hedged)
  → Layer 3 Gemini structured JSON
  → merge into one ComplianceResult
```

### Layer 1 — `api/rules/banned_terms.yaml`

```yaml
rules:
  - id: CLAIM_001
    pattern: "guaranteed"
    reason: "Unsupported absolute insurance claim"
    risk: HIGH
  - id: CLAIM_002
    pattern: "100% covered"
    reason: "Unsupported completeness claim"
    risk: HIGH
  - id: CLAIM_003
    pattern: "always covered"
    reason: "Unsupported absolute insurance claim"
    risk: HIGH
  - id: CLAIM_004
    pattern: "zero risk"
    reason: "Misleading risk statement"
    risk: HIGH
  - id: CLAIM_005
    pattern: "best insurance"
    reason: "Unsubstantiated superlative"
    risk: MEDIUM
  - id: CLAIM_006
    pattern: "cheapest insurance"
    reason: "Unsubstantiated price claim"
    risk: MEDIUM
  - id: CLAIM_007
    pattern: "claim guaranteed"
    reason: "Unsupported claims promise"
    risk: HIGH
```

Match **case-insensitive**. Record the actual substring in `issues[].text` (prefer the original casing from the source text).

Demo requirement: body containing `Guaranteed protection` → at least `CLAIM_001`, `result="FAIL"`, `risk="HIGH"`.

### Layer 2 — hedge check (simple)

If the text talks about cover/coverage/protect/protection **and** does not contain a hedge like `subject to policy` / `policy terms` / `may` / `designed to`, add:

```text
id: CLAIM_010
reason: "Coverage language without qualification"
risk: MEDIUM
```

Do not pretend this is a real regulator rulebook. Comments in yaml: "Hackathon heuristic, not legal advice."

### Layer 3 — Gemini

Prompt `api/prompts/compliance/reviewer.md`. Input: brand_id, platform, text, already-found issues.

Output JSON only:

```json
{
  "result": "FAIL",
  "risk": "HIGH",
  "rules": ["CLAIM_001"],
  "issues": [
    { "text": "Guaranteed coverage", "reason": "Unsupported absolute insurance claim", "rule_id": "CLAIM_001" }
  ],
  "suggested_revision": "..."
}
```

Merge: **worst wins**. If any layer FAIL → FAIL. Else if any REVIEW or MEDIUM+ → REVIEW. Else PASS.

`suggested_revision` from the LLM; if missing, a simple Python rewrite that replaces banned phrases with "cover subject to policy terms".

---

## Lessons

`record_lesson` INSERT into `lessons`. You need `brand_id` (now in the signature — contracts include it).

`get_relevant_lessons` SELECT `note` FROM lessons WHERE brand_id = %s ORDER BY created_at DESC LIMIT n. If `platform` matches some rows, prefer those first, then fill with other platforms for that brand.

Return **plain strings** (the note, optionally prefixed with the tag):

```text
TOO_SALESY: Never describe coverage as guaranteed. Use "coverage subject to policy terms".
```

M4 injects these strings. If you return empty list forever, the learning demo dies.

Use the same DB helper as M1 if importable (`from db import get_conn`). If not, read `DATABASE_URL` with psycopg. Do not create a second schema.

---

## Research (Phase 2)

```python
def scan_competitor(competitor_id: str) -> dict:
```

1. Load competitor URL from DB.
2. Fetch with `httpx` (timeout 15s). Extract text with `trafilatura` (or strip tags).
3. `hash = sha256(text).hexdigest()`
4. Compare to latest `research_snapshots.content_hash` for that competitor.
5. If different, ask Gemini for a 3-bullet `summary` of what changed vs previous content (truncate inputs).
6. INSERT snapshot.
7. Return `{ competitor_id, hash, changed, summary }`.

On fetch failure: return `{ changed: false, summary: "scan_failed: ..." }` — do not raise.

Do **not** start with Crawl4AI. Optional Phase 3 swap only.

Do **not** scrape LinkedIn.

---

## Metrics SQL (M1 may put this in a route; you may provide a function)

If you have time, add `api/agents/lessons.py` or a small `api/agents/metrics.py` — **metrics.py is not in your ownership table.** Prefer giving M1 this SQL in a comment at the bottom of `lessons.py` and letting M1 paste it into `routes/metrics.py`.

If you want to own a helper, **ask M1** to add `api/agents/metrics.py` to your zone. Default: SQL snippet only.

```sql
-- rejection_rate = rejected / (approved+rejected)
-- first_pass_approval = approved with no prior reject on same campaign? keep it simple:
--   approved / (approved+rejected)
-- compliance_failure_rate = assets with a FAIL check / all assets
-- avg_edits_per_post = reviews where edited_body is not null / reviewed assets
```

Simple is fine. Do not build a time-travel dashboard.

---

## Leads (Phase 3 only)

Public search queries like `jewellery stores Kuala Lumpur`. You may use a search API if you have a key (Tavily/Serper) — **personal key in .env**, tell M1 the env name.

Score 0–100 with a short Gemini or heuristic (jewellery + luxury + inventory words). INSERT `leads`. Return list of dicts matching the `Lead` model without `id` (M1 or you inserts).

Empty list on failure.

---

## Phases

### Phase 1

| Task | Acceptance |
|---|---|
| YAML scanner | `check_compliance("Guaranteed protection for your jewellery business", "jade", "instagram").result == "FAIL"` |
| LLM merge | Still FAIL if LLM is down |
| `record_lesson` + `get_relevant_lessons` | Round-trip against Supabase |
| `suggested_revision` | Non-empty on FAIL |

```bash
cd api
uv run python -c "
from agents.compliance import check_compliance
r = check_compliance('Guaranteed protection for your jewellery business', 'jade', 'instagram')
print(r)
assert r.result == 'FAIL'
"
```

### Phase 2

Layer 2 hedges. `scan_competitor` with hash diff. Metrics SQL handed to M1.

### Phase 3

Leads. Crawl4AI only if scan already works and you are bored.

---

## Cursor agent prompts (paste as-is)

### Prompt A — scanner + compliance

```text
You are Team Member 5 for AURA. Read AGENTS.md, docs/03-CONTRACTS.md §4–5, and docs/members/TEAM-MEMBER-5.md.

Create api/rules/banned_terms.yaml with the CLAIM_001–007 rules from the member doc.

Create api/agents/compliance.py with:

def check_compliance(text, brand_id, platform) -> ComplianceResult

Layer 1: case-insensitive scan of yaml patterns; issues[].text is the substring from the original text; rules list of ids; worst risk wins.

Layer 3: if GEMINI_API_KEY set and AURA_MOCK_AGENTS is not true, call Gemini for JSON ComplianceResult using api/prompts/compliance/reviewer.md. Strip fences. Retry once.

Merge: FAIL wins over REVIEW wins over PASS.

Never raise. If LLM fails, return layer-1 result (or REVIEW LLM_UNAVAILABLE if layer-1 clean).

Do not write to the database in this function. Do not edit schemas.py, graph.py, routes, content.py, or web/.
```

### Prompt B — lessons

```text
Create api/agents/lessons.py with get_relevant_lessons and record_lesson exactly matching docs/03-CONTRACTS.md signatures (including brand_id and optional platform on record_lesson).

Use DATABASE_URL / api/db.py if importable. INSERT/SELECT the lessons table columns from the schema in contracts.

get_relevant_lessons returns list[str] notes, newest first, prefer matching platform.

Never raise: log and return [] / no-op.

Do not create HTTP routes.
```

### Prompt C — research

```text
Create api/agents/research.py scan_competitor(competitor_id) as specified in docs/members/TEAM-MEMBER-5.md.

httpx + trafilatura + sha256. Insert research_snapshots. Compare to previous hash. Summarize with Gemini only when changed.

Return dict keys: competitor_id, hash, changed, summary.

On any network error return changed=false and summary starting with scan_failed. Do not use Crawl4AI. Do not scrape LinkedIn. Do not edit files outside api/agents/research.py and api/rules/fixtures.
```

### Prompt D — unit-ish check

```text
Add api/agents/compliance.py docstring tests or a function _demo() that asserts the guaranteed-protection string FAILs.

Do not add pytest fixtures in the web app. Do not modify pyproject.toml unless you only append pytest at the end AND M1 already uses it.

Stay in M5 files.
```

---

## Combining

M1 calls you in this order:

```text
get_relevant_lessons → (M4 generate) → check_compliance → M1 insert
reject → record_lesson
```

Your FAIL on "guaranteed" is what M2 highlights. Your lesson strings are what M4 puts in the prompt. If either side is empty, the story breaks — test the python -c snippet before you sleep.

## Done for demo

Opening the seeded (or live) Instagram post shows FAIL / HIGH / CLAIM_001. Insights shows a lesson after reject. Regenerated copy is less likely to say guaranteed because `get_relevant_lessons` returned the note.
