# Team Member 5 — Compliance and Learning

You are the safety officer and the memory. The demo wins when a bad claim is **caught** with a Python scanner, the reviewer tags it, and a **lesson** is stored.

You do **not** generate marketing copy, add routes, edit the dashboard, crawl the web, or find leads.

**Time: 6–8 hours. Must = banned-term FAIL on "guaranteed" + lessons write/read. LLM reviewer is optional. Research and leads are out.**

## Read these first

1. [../00-START-HERE.md](../00-START-HERE.md)
2. [../03-CONTRACTS.md](../03-CONTRACTS.md) — `ComplianceResult`, lessons functions, metrics
3. [../04-WORKFLOW-RULES.md](../04-WORKFLOW-RULES.md)
4. [../06-DEMO-SCRIPT.md](../06-DEMO-SCRIPT.md) — you must FAIL "Guaranteed protection"
5. [../../AGENTS.md](../../AGENTS.md)

Concept.md §8–9 is useful. Implement **Layer 1 (YAML scanner)** for sure. Layer 3 (Gemini) only if Layer 1 and lessons already work. Skip Layer 2 if short on time.

## Your branch

`feat/m5-compliance`

## Files you own

```text
api/agents/compliance.py
api/agents/lessons.py
api/rules/banned_terms.yaml
api/prompts/compliance/reviewer.md    # only if you attempt Layer 3
```

Also add stub files so M1 imports do not crash:

```text
api/agents/research.py   # scan_competitor returns {changed: false, summary: "skipped"}
api/agents/leads.py      # find_leads returns []
```

Do not implement crawl or lead search.

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

# api/agents/leads.py  (stub only this sprint)
def find_leads(brand_id: str, country: str, limit: int = 10) -> list[dict]:
    ...
```

`check_compliance` is **pure**: no DB writes. M1 stores the result.

`record_lesson` / `get_relevant_lessons` **do** talk to Postgres (`lessons` table).

Never raise into the pipeline. On LLM failure: still return the **hard-rule** result (Python scanner). If the scanner found issues, `result="FAIL"`. If not, `result="REVIEW"`, `risk="MEDIUM"`, reason `LLM_UNAVAILABLE`.

---

## Compliance — Layer 1 is the product

```text
text → YAML banned-term scanner → (optional) Gemini JSON → ComplianceResult
```

**Layer 1 is mandatory.** The demo is dead if "Guaranteed protection" does not FAIL.

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

### Layer 2 — skip

Do not build the hedge checker unless Layer 1 + lessons are done and you still have an hour.

### Layer 3 — Gemini (only if Must is done)

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

`lessons.note` is `NOT NULL` and the reviewer UI does not force a note, so coalesce: `note = note or reason_tag or "OTHER"`. Do not let an empty note become a NOT NULL violation — that 500 lands on the single loudest click of the demo.

`get_relevant_lessons` SELECT `note` FROM lessons WHERE brand_id = %s ORDER BY created_at DESC LIMIT n. If `platform` matches some rows, prefer those first, then fill with other platforms for that brand.

Return **plain strings** (the note, optionally prefixed with the tag):

```text
TOO_SALESY: Never describe coverage as guaranteed. Use "coverage subject to policy terms".
```

M4 injects these strings. If you return empty list forever, the learning demo dies.

Use the same DB helper as M1 if importable (`from db import get_conn`). If not, read `DATABASE_URL` with psycopg. Do not create a second schema.

---

## Research and leads

**Do not implement.** Stubs only:

```python
def scan_competitor(competitor_id: str) -> dict:
    return {"competitor_id": competitor_id, "hash": "", "changed": False, "summary": "skipped"}

def find_leads(brand_id: str, country: str, limit: int = 10) -> list[dict]:
    return []
```

---

## Metrics SQL

Give M1 this comment at the bottom of `lessons.py`. Do not create `metrics.py`.

```sql
-- rejection_rate = rejected / (approved+rejected)
-- lessons_count = count(*) from lessons
-- compliance_failure_rate = assets with a FAIL check / all assets
-- avg_edits_per_post = reviews where edited_body is not null / reviewed assets
```

---

## Must vs skip

### Must

| Task | Acceptance |
|---|---|
| YAML scanner | `check_compliance("Guaranteed protection for your jewellery business", "jade", "instagram").result == "FAIL"` |
| Works without Gemini | Still FAIL if no API key |
| `record_lesson` + `get_relevant_lessons` | Round-trip against Supabase |
| `suggested_revision` | Non-empty on FAIL (string replace is fine) |

```bash
cd api
uv run python -c "
from agents.compliance import check_compliance
r = check_compliance('Guaranteed protection for your jewellery business', 'jade', 'instagram')
print(r)
assert r.result == 'FAIL'
"
```

### If time

Layer 3 Gemini merge. Not required.

### Do not build

`scan_competitor` crawl, Crawl4AI, leads, LinkedIn scrape, Layer 2.

---

## Cursor agent prompts (paste as-is)

### Prompt A — scanner + compliance

```text
You are Team Member 5 for AURA. Read AGENTS.md, docs/03-CONTRACTS.md §4–5, and docs/members/TEAM-MEMBER-5.md.

Create api/rules/banned_terms.yaml with the CLAIM_001–007 rules from the member doc.

Create api/agents/compliance.py with:

def check_compliance(text, brand_id, platform) -> ComplianceResult

Layer 1 only unless Layer 1 already works: case-insensitive scan of yaml patterns; issues[].text is the substring from the original text; rules list of ids; worst risk wins. suggested_revision can be a simple string replace of the banned phrase.

Do not call Gemini in the first version. Never raise.

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
Create api/agents/research.py and api/agents/leads.py as stubs only:

scan_competitor returns {"competitor_id": competitor_id, "hash": "", "changed": False, "summary": "skipped"}
find_leads returns []

Do not fetch URLs. Do not use Crawl4AI.
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

Your FAIL on "guaranteed" is what M2 highlights. Your lesson strings are what M4 puts in the prompt. Test the python -c snippet before you call the work done.

## Done for demo

Opening the seeded (or live) Instagram post shows FAIL / HIGH / CLAIM_001. Insights shows a lesson after reject. Regenerated copy is less likely to say guaranteed because `get_relevant_lessons` returned the note.
