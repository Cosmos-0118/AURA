# Team Member 1 — Platform and Integration Lead

You are the only person who edits shared files. You write **no marketing-agent logic**. You make it possible for the other four to work in parallel and for the demo to boot from `main`.

**Time: 6–8 hours.** Foundation in **90 minutes** including `demo.sql`. Skip LangGraph, deploy, localize, competitors. If anyone is stuck past 20 minutes, you sit with them.

## Read these first

1. [../00-START-HERE.md](../00-START-HERE.md)
2. [../02-SETUP.md](../02-SETUP.md) — you execute the M1-only parts
3. [../03-CONTRACTS.md](../03-CONTRACTS.md) — you implement this, you do not invent a second version
4. [../04-WORKFLOW-RULES.md](../04-WORKFLOW-RULES.md) — you merge all PRs
5. [../05-TIMELINE.md](../05-TIMELINE.md)
6. [../06-DEMO-SCRIPT.md](../06-DEMO-SCRIPT.md)
7. [../../AGENTS.md](../../AGENTS.md)

## Your branch

`feat/m1-platform`

Hour 0 you may commit the skeleton straight to `main` so others can clone. After **T+1.5h**, use the branch + PRs like everyone else. Merge PRs the minute they are green enough to boot.

You have **6–8 hours total**. `db/demo.sql` is part of foundation, not a last-hour task. Skip LangGraph — `run_pipeline` only. Skip deploy.

## Files you own

```text
db/schema.sql
db/seed.sql
db/demo.sql
api/main.py
api/db.py
api/schemas.py
api/graph.py
api/routes/          (all files)
api/agents/_stubs.py
api/pyproject.toml
api/uv.lock
web/src/lib/api/**   (types.ts, client.ts)
web/src/config/nav-config.ts
web/src/app/dashboard/layout.tsx   (nav only — do not restyle M2/M3 pages)
docker-compose.yml                 (optional)
.env.example
README.md
```

You also: create the GitHub repo, create the Supabase project, add collaborators, merge PRs.

## Never touch

```text
web/src/features/**
web/src/app/dashboard/review/**
web/src/app/dashboard/library/**
web/src/app/dashboard/studio/**
web/src/app/dashboard/brands/**
web/src/app/dashboard/insights/**
web/src/app/dashboard/competitors/**
web/src/app/dashboard/leads/**
web/src/components/aura/**
api/agents/content.py
api/agents/localize.py
api/agents/compliance.py
api/agents/lessons.py
api/agents/research.py
api/agents/leads.py
api/prompts/**
api/rules/**
```

If those files are missing, import `_stubs.py`. Do not write the real agent.

---

## Phase 0 (T+0–T+1.5) — you work alone on *shared* files; others code mocks in parallel

Ninety minutes for all six tasks below is the tightest window in the sprint, and four people are blocked behind it. Run **two Cursor agents at once** — the file sets are disjoint, so they will not collide: one on `db/` + `api/` (Prompts A and E), one on the `web/` clone, cleanup, nav, and typed client (Prompt D). Do the Supabase project by hand while they work. Ship `db/` and `web/src/lib/api/` first; those two unblock the most people.

### Task 0.1 — GitHub repo [DONE]

- New repo `AURA` (or the name the team already uses).
- Add the other four as write collaborators.
- Push this docs pack (`docs/`, `AGENTS.md`, `Concept.md`) first so they can read while you scaffold.

**Done when:** others can `git clone` and open `docs/00-START-HERE.md`.

### Task 0.2 — Supabase [DONE]

- One free project `aura`.
- Apply `db/schema.sql` then `db/seed.sql` **and `db/demo.sql`** (FAIL Instagram + DoctorShield approved post + one lesson). Demo data is required at T+1.5, not at freeze.
- Share `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` in the team secret place.

**Done when:** SQL editor `select * from brands;` returns 3 rows.

### Task 0.3 — Frontend skeleton [DONE]

Exact commands are in [02-SETUP.md](../02-SETUP.md) (clone Kiranism into `web/`, delete inner `.git`, cleanup clerk/sentry/chat/kanban/billing).

Then:

- Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `web/.env.local` and document it in `.env.example`.
- Edit nav to the routes listed in contracts §8.
- Placeholder `page.tsx` files ("Team Member 2/3 will build this") are allowed **only in the first 90 minutes on `main`, before anyone else branches**. After T+1.5h, do not touch those route files again — M2/M3 own them. If you skip placeholders, a 404 until they merge is fine.

**Done when:** `bun run dev` shows the AURA sidebar. Clerk sign-in is gone.

### Task 0.4 — FastAPI skeleton [DONE]

`api/pyproject.toml` deps (do not add more without a reason):

```text
fastapi
uvicorn[standard]
pydantic
pydantic-settings
psycopg[binary]
httpx
python-dotenv
```

Do **not** add langgraph. M4/M5 own Gemini. `graph.py` does not call Gemini.

Files:

- `main.py` — CORS `http://localhost:3000`, include routers, `/api/health`
- `db.py` — connection pool from `DATABASE_URL`
- `schemas.py` — copy from contracts §4
- `routes/*.py` — one router per resource
- `_stubs.py` — mock `generate_content`, `check_compliance`, `get_relevant_lessons`, `record_lesson`, `scan_competitor`

**Done when:** Swagger at `http://localhost:8000/docs` lists every endpoint in contracts §6 and `GET /api/brands` hits the real DB.

Only these eleven need a real body in Hour 0 — `health`, `brands`, `brands/{id}`, `POST campaigns`, `GET campaigns/{id}`, `GET assets`, `GET assets/{id}`, `approve`, `reject`, `lessons`, `metrics`. Declare the rest (competitors scan, regenerate, localize, leads) and `raise HTTPException(501, "not in this sprint")` so the shape is visible without costing you time.

### Task 0.5 — Typed frontend client [DONE]

`web/src/lib/api/types.ts` + `client.ts` with the function names in contracts §7. Use `fetch` + `NEXT_PUBLIC_API_URL`. No axios unless it is already in the starter.

**Done when:** M2 can `import { listAssets, approveAsset } from "@/lib/api/client"`.

### Task 0.6 — Announce freeze

Team channel:

```text
contracts are in main
clone, bun install, uv sync, copy .env
your branch names are in docs/04-WORKFLOW-RULES.md
```

---

## Must (T+1.5–T+5)

### Task 1.1 — `POST /api/campaigns` + `run_pipeline` in `graph.py` [DONE]

**Do not use LangGraph.** A function named `run_pipeline(campaign_id)` is the whole orchestrator.

```text
running → lessons + optional research → generate_content → for each asset check_compliance → insert rows → completed
```

Wrap in try/except: on failure `campaigns.status='failed'` and `error=str(e)`.

Use `AURA_MOCK_AGENTS=true` to call stubs. When M4/M5 files exist:

```python
try:
    from agents.content import generate_content
except ImportError:
    from agents._stubs import generate_content
```

**Acceptance**

- POST returns a campaign with `status=running` in < 200ms.
- Within ~30s (mock: ~1s) GET campaign is `completed` and GET assets by `campaign_id` returns ≥1 row.
- FAIL compliance → `status=compliance_failed` plus a `compliance_checks` row.
- Crashing Gemini does not leave `running` forever.

### Task 1.2 — Review writes [DONE]

`POST approve` / `POST reject` / `PATCH body` as in contracts §9.

Reject **must** call `record_lesson(...)`. If `_stubs.record_lesson` is a no-op, that is fine until M5 lands.

Pass `note or reason_tag` — never `None`. `lessons.note` is `NOT NULL` and M2's note field is optional, so an empty textarea would otherwise 500 on the demo's biggest click.

**Acceptance:** rejecting the seeded FAIL Instagram row **with an empty note** sets `rejected`, inserts `reviews`, inserts a lesson, and does not 500.

### Task 1.3 — Merge hygiene

Merge M2–M5 PRs at **T+3** even if incomplete, as long as `main` boots.

Write `GET /api/metrics` yourself with simple SQL. Do not wait for M5. Guard every denominator — an empty DB must return zeros with a 200, or M3's Insights page is a white screen from T+3 until someone rejects something.

`db/demo.sql` should already exist from Phase 0. If not, write it **before** T+3 so M2 has the FAIL row.

## If time (only after T+5 slice works, 8h track)

Regenerate endpoint (`POST /api/assets/{id}/regenerate`). No localize. No deploy. No competitors scan.

## Freeze

You run the demo. Two rehearsals. Screenshots of Studio, Review FAIL, Brands, Insights.

---

## How `graph.py` should look (shape, not extra features)

```python
# api/graph.py  OWNER: Team Member 1
async def run_pipeline(campaign_id: str) -> None:
    campaign = load_campaign(campaign_id)
    set_status(campaign_id, "running")
    try:
        lessons = get_relevant_lessons(campaign.brand_id, "linkedin")
        research = None  # skip competitor scan in this sprint
        req = ContentRequest(
            brand_id=campaign.brand_id,
            topic=campaign.topic,
            country=campaign.country,
            goal=campaign.goal,
            platforms=campaign.platforms,
            language=campaign.language,
            lessons=lessons,
            research_summary=research,
        )
        generated = generate_content(req)
        for asset in generated:
            check = check_compliance(asset.body, campaign.brand_id, asset.platform)
            status = "compliance_failed" if check.result == "FAIL" else "pending_review"
            insert_asset_and_check(campaign_id, asset, check, status)
        set_status(campaign_id, "completed")
    except Exception as e:
        set_status(campaign_id, "failed", error=str(e))
```

Keep it this boring.

---

## Cursor agent prompts (paste as-is)

### Prompt A — Hour 0 scaffold

```text
You are Team Member 1 for AURA. Read AGENTS.md, docs/02-SETUP.md, and docs/03-CONTRACTS.md.

Your only job this session: scaffold the monorepo so the other four members can start.

Do:
1. Create db/schema.sql and db/seed.sql exactly from docs/03-CONTRACTS.md (brands jade, doctorshield, jaguar).
2. Create api/ as a uv FastAPI app with main.py (CORS localhost:3000), db.py, schemas.py copied from the contracts, routes for every endpoint in contracts §6. Endpoints may return empty lists if the table is empty, except GET /api/brands which reads Postgres.
3. Create api/agents/_stubs.py implementing generate_content, localize, check_compliance, get_relevant_lessons, record_lesson, scan_competitor with realistic hardcoded returns matching the mock payload in contracts §10.
4. Create web/src/lib/api/types.ts and client.ts from contracts §7.
5. Add nav items from contracts §8. Placeholder page.tsx files that say which member owns the page.
6. Root .env.example.
7. Optional Hour-0 only: placeholder page.tsx under dashboard routes. After that, never edit M2/M3 folders.

Do not: implement real Gemini in this session, edit M2/M3 folders after T+1.5h, add Clerk, add Redis, add LangGraph.

AURA_MOCK_AGENTS=true should make graph.py (or run_pipeline) use stubs.

Work only in files listed as M1-owned in AGENTS.md.
```

### Prompt B — pipeline

```text
Read docs/03-CONTRACTS.md §9 and docs/members/TEAM-MEMBER-1.md.

Implement api/graph.py run_pipeline(campaign_id) and wire POST /api/campaigns to start it via FastAPI BackgroundTasks.

Import agent functions with try/except ImportError falling back to agents._stubs.

Respect AURA_MOCK_AGENTS. On any exception set campaigns.status=failed.

Do not write content.py or compliance.py. Do not change schemas.py field names.

Add a tiny test or a README snippet: curl POST campaign then GET assets.
```

### Prompt C — review endpoints

```text
Implement POST /api/assets/{id}/approve, /reject, PATCH /api/assets/{id} exactly as docs/03-CONTRACTS.md §9.

reject calls record_lesson with brand_id and platform from the asset row.

approve sets approved_at, approved_by from ReviewAction.

If edited_body is present, update body and record a lesson when original != edited.

Stay in api/routes/ and api/graph.py / db.py only.
```

### Prompt D — typed client

```text
Write web/src/lib/api/types.ts and client.ts from docs/03-CONTRACTS.md §7.

Use fetch and process.env.NEXT_PUBLIC_API_URL. snake_case JSON. No camelCase mapping.

Export the exact function names listed in the contracts. Do not add extra wrappers.

Do not edit any file under web/src/features.
```

### Prompt E — demo seed

```text
Create db/demo.sql in the same session as schema/seed (see docs/06-DEMO-SCRIPT.md). Do not leave it for later.

Plant: the Jade Instagram compliance_failed row whose body contains "Guaranteed protection for your jewellery business", its FAIL / HIGH / CLAIM_001 compliance_checks row, one Jade lesson, one approved DoctorShield LinkedIn post, and two reviews so metrics are not all zero.

Use hardcoded UUID literals for every id, and start the file by deleting those exact ids. Re-running demo.sql must be safe and must not change the asset URL. Never TRUNCATE.

Stay in db/. Do not touch api/ or web/ in this session.
```

---

## Daily checklist

- [ ] `main` boots (API + web)
- [ ] PRs merged or blocked with a written reason
- [ ] Contract change requests answered within 30 minutes
- [ ] Nobody else has committed to `schemas.py`
