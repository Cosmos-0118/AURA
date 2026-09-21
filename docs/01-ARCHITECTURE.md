# Architecture

This is the system we are actually building in 24–48 hours. If it disagrees with `Concept.md`, this file wins. `Concept.md` is product thinking; this file is the build.

## Picture

```text
                     ┌──────────────────────────┐
                     │  Next.js dashboard (web) │
                     │  M2 Review  |  M3 Studio │
                     └────────────┬─────────────┘
                                  │ REST  localhost:8000
                     ┌────────────▼─────────────┐
                     │     FastAPI  (api)       │
                     │     Team Member 1        │
                     │  routes → graph.py       │
                     └────────────┬─────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
     M5 research.py      M4 content.py +        M5 compliance.py
     (optional scan)     M4 localize.py         M5 lessons.py
              │                   │                   │
              └───────────────────┴───────────────────┘
                                  │
                          persist content_assets
                          status = pending_review
                                  │
                          ┌───────▼────────┐
                          │    Supabase    │
                          │    Postgres    │
                          └────────────────┘
```

There is **no** Redis, Kafka, Celery, Mongo, or second database. Background work is FastAPI `BackgroundTasks` (or a simple `asyncio.create_task`). Fine for a hackathon.

## Why these choices (so nobody "improves" the stack mid-hackathon)

| Decision | Why |
|---|---|
| One FastAPI process, not agent-service-toolkit | That repo is a **chat** service (threads, token streaming, Streamlit). We are a **batch pipeline + review queue**. Adapting it costs more than writing ~400 lines of FastAPI. |
| LangGraph in **one file** (`api/graph.py`), owned by M1 | Four people editing a graph = merge hell. M4 and M5 export plain functions. M1 wires them. |
| Linear graph: research → content → compliance → persist | Not a swarm. Agents do not call each other. |
| Kiranism dashboard, Clerk stripped | We do not have time for auth. Cleanup script exists. Tables/forms already work. |
| Supabase hosted Postgres | Nobody installs Postgres locally. One project, everyone uses the same URL. |
| Per-person Gemini keys | Five Cursor agents on one free-tier key will 429. |
| `httpx` + `trafilatura` first | Crawl4AI wants Playwright/Docker. Phase 3 upgrade only. |
| Reel = script + TTS + stills; MP4 is stretch | FFmpeg debugging eats a night. Judges can see a storyboard. |
| No Project 2 publisher in the default plan | Concept.md is explicit: polish Project 1 first. Approved rows in the DB **are** the bridge. |

## Data flow (one campaign)

```text
M3 Studio form
  POST /api/campaigns  { brand_id, topic, country, goal, platforms, language }
        │
        ▼
M1 creates campaigns row (status=running)
M1 kicks graph.py in the background
        │
        ├─ M5 get_relevant_lessons(brand_id, platform)
        ├─ M5 scan_competitor  (skip if none / mock)
        ├─ M4 generate_content(ContentRequest)  → list[GeneratedAsset]
        ├─ for each asset:
        │     M5 check_compliance(text, brand_id, platform)
        │     status = pending_review  (even FAIL still goes to review — humans decide)
        │     compliance_checks row written
        └─ campaign status=completed
        │
M2 Review Queue  GET /api/assets?status=pending_review
        │
        ├─ Approve  POST /api/assets/{id}/approve
        ├─ Edit     PATCH body, then approve
        └─ Reject   POST /api/assets/{id}/reject  { reason_tag, note, edited? }
                    M1 also calls M5 record_lesson(...)
        │
Regenerate  POST /api/assets/{id}/regenerate
        │   M1 rebuilds ContentRequest with fresh lessons
        │   M4 generate_content again → new asset row
        ▼
Insights  GET /api/metrics  GET /api/lessons
```

**Important:** compliance FAIL does **not** hide the asset. It marks `compliance_failed` **or** still `pending_review` with `risk=HIGH` (see contracts). Humans are the final authority. The system never auto-publishes.

## Folder map of the monorepo

```text
AURA/
  AGENTS.md                 # rules for Cursor agents
  Concept.md                # original thinking (not the build spec)
  README.md                 # M1 writes a short runbook after setup
  .env.example
  docker-compose.yml        # optional; local run without Docker is the default
  db/
    schema.sql              # M1
    seed.sql                # M1, idempotent
  api/                      # Python, uv
    main.py                 # M1
    db.py                   # M1
    schemas.py              # M1, FROZEN
    graph.py                # M1
    routes/                 # M1 only
    agents/
      _stubs.py             # M1, until M4/M5 land
      content.py            # M4
      localize.py           # M4
      compliance.py         # M5
      lessons.py            # M5
      research.py           # M5
      leads.py              # M5 Phase 3
    prompts/content/        # M4
    prompts/compliance/     # M5
    rules/banned_terms.yaml # M5
  web/                      # Next.js 16 app (Kiranism clone)
    src/app/dashboard/...   # route files; M2 and M3 own their route folders
    src/features/...        # feature modules; do not share folders
    src/lib/api/            # M1 typed client
    src/config/nav-config.ts# M1
    src/components/ui/      # nobody edits
    src/components/aura/m2/ # M2 shared-within-M2
    src/components/aura/m3/ # M3 shared-within-M3
  docs/                     # this pack
```

## Status field (heart of the product)

`content_assets.status` is the only workflow state. Do not invent a second state machine.

```text
draft → (pipeline writes) → pending_review → approved
                          ↘                 ↘ rejected
                           compliance_failed   (still reviewable)
```

Bonus values, unused until Project 2: `scheduled`, `published`. You may store them in the CHECK constraint so we do not migrate later. Do not build publisher UI.

## Who talks to Gemini

| Module | Owner | Calls Gemini? |
|---|---|---|
| `content.py` / `localize.py` | M4 | Yes — generation |
| `compliance.py` (LLM pass only) | M5 | Yes — structured JSON review |
| `research.py` (summarise diff) | M5 | Yes — short report |
| `lessons.py` retrieve | M5 | No — SQL |
| `graph.py` | M1 | No — only calls the functions above |
| Frontend | M2 / M3 | Never. Browser has no API key. |

Hard-rule scanning, hashing, status writes, metrics: **plain Python**. Do not ask Gemini "does this seem compliant?" as the only check.

## Combining at the end

Because each person owns disjoint files:

- M1's routes already `from agents.content import generate_content`. When M4 replaces the stub, the import path does not change.
- M2/M3 already call `web/src/lib/api`. When mocks become real DB rows, the JSON shape does not change.
- Integration is: merge branches, run seed, click through the demo script. Not "rewrite the glue".
