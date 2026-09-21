# AURA — Agent Rules (read this before writing any code)

This file is for AI coding agents working in this repo. Humans and agents also
read `docs/TEAM-PLAN.md` and only their own `docs/members/TEAM-MEMBER-N.md`.

## Current sprint state

The database, FastAPI routes, campaign pipeline, frozen contracts, typed frontend
client, navigation, and deterministic stubs are already on `main`. Do not rebuild
the scaffold. The remaining work is the five parallel lanes in
`docs/TEAM-PLAN.md`.

## What this project is

AURA is an **8-hour** hackathon marketing dashboard. It is **not a chatbot**. The pipeline is:

```
campaign → generate content → compliance check → human review → learn from corrections
```

Differentiator: **Compliance + Human Review + Feedback Learning**. Not "we generated 100 posts".

## The three rules that keep this team from colliding

1. **You write only inside your owner's folders.** If a file is not in your zone, do not open it to "fix" it. Stop and tell the human to message Team Member 1.
2. **Contracts are frozen.** `api/schemas.py`, `docs/03-CONTRACTS.md`, `web/src/lib/api/types.ts`, and `web/src/config/nav-config.ts` are owned by Team Member 1. Do not change shapes, field names, status values, or endpoint paths. If you need a new field, stop and ask.
3. **Mock-first.** Every function you own ships a working hardcoded return first. Then replace the mock with the real implementation. The rest of the team must be able to run against your mock.

## Ownership map (do not cross)

| Who | Writes only these paths | Branch |
|---|---|---|
| Team Member 1 | `db/**`, `api/main.py`, `api/db.py`, `api/schemas.py`, `api/graph.py`, `api/routes/**`, `api/agents/_stubs.py`, `api/tests/integration/**`, `api/pyproject.toml`, `api/uv.lock`, `web/src/lib/api/**`, `web/src/config/nav-config.ts`, `web/src/app/dashboard/layout.tsx`, `web/src/app/dashboard/page.tsx`, `web/src/app/dashboard/overview/**`, `web/src/features/overview/**`, `docs/**`, `docker-compose.yml`, `.env.example`, `README.md` | `feat/m1-platform` |
| Team Member 2 | `web/src/features/review/**`, `web/src/features/library/**`, `web/src/app/dashboard/review/**`, `web/src/app/dashboard/library/**`, `web/src/components/aura/m2/**` | `feat/m2-review-ui` |
| Team Member 3 | `web/src/features/studio/**`, `web/src/features/brands/**`, `web/src/features/insights/**`, `web/src/app/dashboard/studio/**`, `web/src/app/dashboard/brands/**`, `web/src/app/dashboard/insights/**`, `web/src/components/aura/m3/**` | `feat/m3-studio-ui` |
| Team Member 4 | `api/agents/content.py`, `api/agents/localize.py`, `api/prompts/content/**`, `api/tests/content/**` | `feat/m4-content` |
| Team Member 5 | `api/agents/compliance.py`, `api/agents/lessons.py`, `api/agents/research.py`, `api/agents/leads.py`, `api/rules/**`, `api/prompts/compliance/**`, `api/tests/compliance/**` | `feat/m5-compliance` |

Shared folders that **nobody except Team Member 1** may edit:

- `api/schemas.py` (frozen contract)
- `api/routes/**` (M1 wires your functions; you do not add routes)
- `web/src/components/ui/**` (shadcn primitives — import them, never edit them)
- `web/src/lib/api/**` (typed fetch client — M1 owns this)
- `web/package.json` / `web/bun.lock` — the sprint needs no new frontend dependency; ask M1 before adding one
- `api/pyproject.toml` / `api/uv.lock` — M4/M5 ask M1 for dependency changes

If you need a new shared component, put it in `web/src/components/aura/m2/` or `web/src/components/aura/m3/` (your own folder). Do not dump it in `components/ui`.

## How to call other people's work

- Frontend (M2, M3): import types and fetchers from `web/src/lib/api/`. Never `fetch()` raw URLs. Never invent response shapes.
- Backend agents (M4, M5): import Pydantic models from `api/schemas.py`. Your public functions must match the signatures in `docs/03-CONTRACTS.md` exactly.
- Orchestrator (M1): calls M4/M5 functions. If those files do not exist yet, M1 uses the stubs in `api/agents/_stubs.py`.

## Git rules for agents

- Work on the owner's branch listed above. Never commit to `main`.
- Never `git rebase`. Never `--force` push. Never `--no-verify`.
- Before committing: `git pull origin main` (merge, not rebase).
- Do not commit `.env`, API keys, `node_modules`, `.venv`, or generated MP4/WAV files larger than 5 MB.
- Commit messages: one sentence, present tense, scoped to your zone. Example: `Add review queue table with status filter`.

## What not to build

- Do not add Clerk, Sentry, Redis, Kafka, Celery, Mongo, Docker, or a second database.
- Do not fork or copy Postiz source (AGPL). Do not vendor Crawl4AI. Do not add FFmpeg, leads, localization, X, blog, or reels.
- Do not turn this into a chat UI. There is no "talk to the agent" page.
- Do not introduce LangGraph APIs. `graph.py` is a plain `run_pipeline` function.
- The only allowed stretch work is listed in `docs/TEAM-PLAN.md`, and it starts
  only after the T+4:30 vertical-slice checkpoint passes.

## When you are stuck

1. Read `docs/03-CONTRACTS.md` again. Most bugs are shape mismatches.
2. Read `docs/troubleshooting.md`.
3. If the contract is missing a field you genuinely need, stop coding and tell the human: "Ask Team Member 1 to add X to the contract. Do not patch it locally."
