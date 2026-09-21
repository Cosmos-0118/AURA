# Team Member 5 — Compliance and learning owner

## Mission

Guarantee that unsafe absolute claims are caught deterministically and that human
corrections can be saved and retrieved for the next generation run.

Read `AGENTS.md`, `docs/TEAM-PLAN.md`, Contracts sections 1, 4, 5, and 9, then
this card.

## Branch and owned paths

Branch: `feat/m5-compliance`

```text
api/agents/compliance.py
api/agents/lessons.py
api/agents/research.py
api/agents/leads.py
api/rules/**
api/prompts/compliance/**
api/tests/compliance/**
```

Do not edit schemas, routes, graph, dependencies, M4 files, or `.env`. Research
and leads are out of scope; do not create them unless a contract-compatible stub
is needed for an import.

## Frozen public functions

```python
def check_compliance(text: str, brand_id: str, platform: str) -> ComplianceResult: ...

def get_relevant_lessons(
    brand_id: str,
    platform: str,
    limit: int = 5,
) -> list[str]: ...

def record_lesson(
    asset_id: str,
    reason_tag: str,
    note: str,
    original: str,
    edited: str | None,
    brand_id: str,
    platform: str | None = None,
) -> None: ...
```

Import models from `api/schemas.py` and the DB helper as `get_connection` from
`api/db.py`.

## Deterministic compliance layer

Rules live under `api/rules/`. At minimum, case-insensitively catch:

| Phrase | Rule | Result |
|---|---|---|
| `guaranteed` | `CLAIM_001` | `FAIL / HIGH` |
| `100% covered` | `CLAIM_002` | `FAIL / HIGH` |
| `zero risk` | `CLAIM_003` | `FAIL / HIGH` |
| `always covered` or `claim guaranteed` | absolute coverage rule | `FAIL / HIGH` |

Every issue includes the matched text, a plain-language reason, and rule ID.
Every fail includes a usable suggested revision. Clean text returns `PASS / LOW`.
Hard rules always win over any model result.

Do not add a YAML dependency. Either use a data format the standard library can
read or keep parsing deliberately small and tested.

## Lessons

- `record_lesson` writes through `get_connection()` using parameterized SQL.
- Empty `note` falls back to `reason_tag` or `Reviewer correction` so the NOT NULL
  database column is never violated.
- `get_relevant_lessons` returns newest matching-brand lessons, preferring the
  requested platform while allowing platform-null lessons, capped by `limit`.
- DB errors in retrieval return an empty list so generation can continue; write
  errors should remain visible to M1's route fallback.

## Stretch after the checkpoint

Add a structured Gemini second pass for claims not covered by hard rules. Validate
its shape and merge conservatively: it may raise a clean result to `REVIEW` or
`FAIL`, but it may never downgrade a deterministic failure. Provider failures
must return the deterministic result.

Do not implement competitor crawling, lead generation, localization, or metrics.

## Acceptance

- The seeded `Guaranteed protection` text returns `FAIL`, `HIGH`, `CLAIM_001`.
- Matching is case-insensitive and clean copy passes.
- Multiple violations produce multiple issues without duplicate rules.
- Suggested revision removes or qualifies the absolute claim.
- A lesson written with an empty note can be retrieved for the same brand/platform.
- Retrieval is ordered, limited, and safe when the DB is unavailable.
- Focused tests under `api/tests/compliance/` and the targeted backend compile check pass.

## Give your coding agent this task

```text
Read AGENTS.md, docs/TEAM-PLAN.md, docs/members/TEAM-MEMBER-5.md, and the linked
contract sections. Work only in M5-owned paths. Implement and test deterministic
hard-rule compliance plus DB-backed lesson write/read using exact frozen function
signatures. Guaranteed protection must be FAIL/HIGH/CLAIM_001 with a revision.
Only after that works, add a validated optional Gemini second pass that can never
downgrade hard-rule failures. Do not edit routes, graph, schemas, or dependencies.
```
