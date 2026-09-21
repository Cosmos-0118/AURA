# Team Member 1 — Integration and demo owner

## Mission

Keep `main` runnable while the four feature branches land. You own the shared
surfaces, the AURA Overview, integration checks, and the demo. The original
scaffold is complete; do not rebuild it.

Read `AGENTS.md`, `docs/TEAM-PLAN.md`, Contracts sections 1, 6, 8, and 9, then
this card.

## Branch and owned paths

Branch: `feat/m1-platform`

You own:

```text
db/**
api/main.py
api/db.py
api/schemas.py
api/graph.py
api/routes/**
api/agents/_stubs.py
api/tests/integration/**
api/pyproject.toml
api/uv.lock
web/src/lib/api/**
web/src/config/nav-config.ts
web/src/app/dashboard/layout.tsx
web/src/app/dashboard/page.tsx
web/src/app/dashboard/overview/**
web/src/features/overview/**
README.md
docs/**
.env.example
docker-compose.yml
```

Do not edit M2/M3 feature or route folders, or M4/M5 real agent modules. When a
branch fails, identify whether the defect is in your integration surface or the
owner's module and send evidence to the owner.

## Deliverables in order

### 1. Prove the scaffold

- Apply `db/schema.sql`, `db/seed.sql`, and `db/demo.sql` to the shared DB.
- Boot FastAPI and verify health, brands, queue, one asset, lessons, and metrics.
- Reject the seeded failed asset with an empty note and confirm both a review and
  a lesson are written.
- Re-run `db/demo.sql` so teammates receive the expected fixture.

### 2. Integrate M4 and M5

- Merge their PRs without changing their public signatures.
- Run a campaign once with `AURA_MOCK_AGENTS=true` and once with it `false`.
- A network/LLM failure may reduce output quality, but must not leave a campaign
  permanently running or crash the API process.
- A compliance `FAIL` is stored as `compliance_failed` and remains visible in
  `GET /api/assets?status=queue`.

### 3. Replace the starter Overview

Build a compact AURA command center using the existing client only:

- metrics cards;
- pending-review count and link to Review;
- recent campaigns or recent assets;
- one clear Create Campaign action;
- loading, empty, and API-error states.

Do not build a second Insights page. Overview is a quick operational summary.

### 4. Make integration repeatable

Add a small integration smoke check under `api/tests/integration/` or document a
single repeatable command sequence. Cover the campaign and review loop, not every
501 placeholder. Keep demo SQL repeatable.

### 5. Merge and rehearse

- Merge small PRs as soon as their focused checks pass.
- Run backend compile checks and frontend typecheck/build on merged `main`.
- Click the six-step checkpoint in `docs/TEAM-PLAN.md`.
- Reset demo data, capture screenshots, and rehearse twice after T+6:30.

## Acceptance

- `main` boots both processes without code changes.
- Mock mode completes a campaign and produces reviewable assets.
- Seeded `Guaranteed protection` is rejectable with an empty note.
- The rejection creates a lesson visible through `/api/lessons`.
- Overview contains only AURA data; generic starter sales/product charts are gone.
- M2 and M3 never need to call raw `fetch()`.
- M4 and M5 can merge without editing routes or schemas.

## Escalation decisions

Approve a contract change only when the current shape cannot represent a
must-ship behavior. If approved, update Python schema, route behavior, TypeScript
type/client, and Contracts in one M1 commit. Otherwise point the member to the
existing field or endpoint.

## Give your coding agent this task

```text
Read AGENTS.md, docs/TEAM-PLAN.md, and docs/members/TEAM-MEMBER-1.md. The scaffold
is complete. Work only in M1-owned paths. First verify the existing API and demo
fixture, then build the AURA Overview, integrate M4/M5 without changing frozen
contracts, and add a repeatable smoke check. Run focused checks after each step.
Do not edit another member's feature files or implement out-of-scope endpoints.
```
