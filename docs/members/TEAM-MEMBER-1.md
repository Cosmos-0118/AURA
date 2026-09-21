# Team Member 1 — Platform and Integration Lead

You are the only person who edits shared files. You write **no marketing-agent logic**. You make it possible for the other four to work in parallel and for the demo to boot from `main`.

If anyone is stuck past 45 minutes, you drop new work and unblock them. A working vertical slice beats a fourth platform.

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

Hour 0 you may commit the skeleton straight to `main` so others can clone. After T+3, use the branch + PRs like everyone else.

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

## Phase 0 (T+0–T+3) — you work alone

### Task 0.1 — GitHub repo

- New repo `AURA` (or the name the team already uses).
- Add the other four as write collaborators.
- Push this docs pack (`docs/`, `AGENTS.md`, `Concept.md`) first so they can read while you scaffold.

**Done when:** others can `git clone` and open `docs/00-START-HERE.md`.

### Task 0.2 — Supabase

- One free project `aura`.
- Apply `db/schema.sql` then `db/seed.sql` (you write both from [03-CONTRACTS.md](../03-CONTRACTS.md)).
- Share `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` in the team secret place.

**Done when:** SQL editor `select * from brands;` returns 3 rows.

### Task 0.3 — Frontend skeleton

Exact commands are in [02-SETUP.md](../02-SETUP.md) (clone Kiranism into `web/`, delete inner `.git`, cleanup clerk/sentry/chat/kanban/billing).

Then:

- Set `NEXT_PUBLIC_API_URL=http://localhost:8000` in `web/.env.local` and document it in `.env.example`.
- Edit nav to the routes listed in contracts §8.
- Placeholder `page.tsx` files ("Team Member 2/3 will build this") are allowed **only in Hour 0 on `main`, before anyone else branches**. After T+3, do not touch those route files again — M2/M3 own them. If you skip placeholders, a 404 until they merge is fine.

**Done when:** `bun run dev` shows the AURA sidebar. Clerk sign-in is gone.

### Task 0.4 — FastAPI skeleton

`api/pyproject.toml` deps (do not add more without a reason):

```text
fastapi
uvicorn[standard]
pydantic
pydantic-settings
psycopg[binary]
httpx
python-dotenv
langgraph
langchain-google-genai   # only if graph needs it; prefer M4/M5 own the Gemini client
```

M4/M5 should own Gemini calls. `graph.py` does not call Gemini.

Files:

- `main.py` — CORS `http://localhost:3000`, include routers, `/api/health`
- `db.py` — connection pool from `DATABASE_URL`
- `schemas.py` — copy from contracts §4
- `routes/*.py` — one router per resource
- `_stubs.py` — mock `generate_content`, `check_compliance`, `get_relevant_lessons`, `record_lesson`, `scan_competitor`

**Done when:** Swagger at `http://localhost:8000/docs` lists every endpoint in contracts §6. `GET /api/brands` hits the real DB.

### Task 0.5 — Typed frontend client

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

## Phase 1 (T+3–T+12)

### Task 1.1 — `POST /api/campaigns` + `graph.py`

Linear LangGraph (or even a plain async function if LangGraph fights you — a function named `run_pipeline(campaign_id)` is acceptable; do not burn 3 hours on graph APIs):

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

### Task 1.2 — Review writes

`POST approve` / `POST reject` / `PATCH body` as in contracts §9.

Reject **must** call `record_lesson(...)`. If `_stubs.record_lesson` is a no-op, that is fine until M5 lands.

**Acceptance:** rejecting the seeded FAIL Instagram row sets `rejected`, inserts `reviews`, and does not 500.

### Task 1.3 — Merge hygiene

Merge M2–M5 PRs at T+6 even if incomplete, as long as `main` boots.

---

## Phase 2 (T+18–T+30)

### Task 2.1 — regenerate + localize endpoints

- `regenerate`: load asset + brand, `get_relevant_lessons`, call `generate_content` for **that platform only**, compliance, insert **new** row (do not overwrite the rejected one).
- `localize`: call `localize(...)`, compliance, insert new row with new `language` and `variant` like `loc-ms`.

### Task 2.2 — `GET /api/metrics`

If M5 ships SQL, call it. If not, you write a simple SQL aggregation so M3's charts have numbers. Prefer M5 — if they are behind, you do the SQL in `routes/metrics.py` (this is allowed; it is your route file).

### Task 2.3 — `db/demo.sql`

See [06-DEMO-SCRIPT.md](../06-DEMO-SCRIPT.md). Must be re-runnable.

---

## Phase 3 (only if `main` slice is solid)

Pick: deploy (Vercel + Render/Fly) **or** help M4/M5. Do not start Postiz.

---

## Phase 4

You run the demo. Three rehearsals. Screenshots if Wi-Fi dies.

---

## How `graph.py` should look (shape, not extra features)

```python
# api/graph.py  OWNER: Team Member 1
async def run_pipeline(campaign_id: str) -> None:
    campaign = load_campaign(campaign_id)
    set_status(campaign_id, "running")
    try:
        lessons: list[str] = []
        for p in campaign.platforms:
            lessons.extend(get_relevant_lessons(campaign.brand_id, p))
        research = None  # optional scan_competitor
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

Do not: implement real Gemini, edit feature UI folders after T+3, add Clerk, add Redis.

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
Create db/demo.sql that is re-runnable and plants the backup data in docs/06-DEMO-SCRIPT.md:
- Jade Instagram pending/compliance_failed with body containing "Guaranteed protection"
- matching compliance_checks FAIL HIGH CLAIM_001
- one lessons row TOO_SALESY for jade
- one approved DoctorShield LinkedIn educational post
Do not truncate brands. Use fixed UUIDs so we can re-run the script.
```

---

## Daily checklist

- [ ] `main` boots (API + web)
- [ ] PRs merged or blocked with a written reason
- [ ] Contract change requests answered within 30 minutes
- [ ] Nobody else has committed to `schemas.py`
