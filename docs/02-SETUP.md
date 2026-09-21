# Local setup

The repository is already scaffolded. Members install dependencies and run it;
only M1 applies database SQL or changes shared environment examples.

## Prerequisites

- Git
- Node.js 20+
- Bun
- uv with Python 3.12+
- access to the shared Supabase database
- a personal Gemini key only if working on M4/M5's optional live path

No Docker or local Postgres is required.

## Branch

```bash
git fetch origin
git switch <your-branch>
git merge origin/main
```

Use the exact branch from your member card. Never work on `main`, rebase, or
force-push.

## Environment

```bash
cp .env.example .env
cp web/env.example.txt web/.env.local
```

Root `.env` needs:

```dotenv
DATABASE_URL=<shared-postgres-url>
GEMINI_API_KEY=<personal-key-if-needed>
GEMINI_MODEL=<team-selected-model>
AURA_MOCK_AGENTS=true
```

`web/.env.local` needs:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Never put a Gemini or Supabase service key in the frontend environment. Never
commit `.env` or `web/.env.local`.

## Install and run

```bash
# terminal 1
cd api
uv sync
uv run uvicorn main:app --reload --port 8000

# terminal 2
cd web
bun install
bun run dev
```

Verify:

- http://localhost:8000/api/health returns `{"ok":true}`.
- http://localhost:8000/api/brands returns three brands.
- http://localhost:8000/api/assets?status=queue returns the seeded failed asset.
- http://localhost:3000 loads the dashboard shell.

If brands or queue data is missing, tell M1. Do not create a second database or
hardcode a different response shape.

## M1 database setup

In Supabase SQL Editor, apply in this order:

1. `db/schema.sql`
2. `db/seed.sql`
3. `db/demo.sql`

`seed.sql` and `demo.sql` are designed to be rerun. Do not truncate the database.
M1 reruns `demo.sql` before integration testing and before the presentation.

## Checks

```bash
cd api && uv run python -m compileall main.py db.py schemas.py graph.py routes agents
cd web && bun run typecheck && bun run build
```

Use [troubleshooting.md](troubleshooting.md) for known failures. If still blocked,
post the exact command, full error, operating system, and whether health/brands
work; do not send only a screenshot or “it does not run.”
