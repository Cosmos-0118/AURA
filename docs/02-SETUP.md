# Setup

Do this in order. If a command fails, open [troubleshooting.md](troubleshooting.md) before installing random packages.

## Accounts (everyone, Hour 0)

1. **GitHub** — you need write access to the team AURA repo (Team Member 1 creates it and adds you).
2. **Google AI Studio** — [https://aistudio.google.com/apikey](https://aistudio.google.com/apikey) — create **your own** Gemini API key. Put it only in your local `.env`. Never Slack it. Never commit it.
3. **Supabase** — Team Member 1 creates one free project named `aura`. Everyone else waits for M1 to paste the URL + keys into the team channel (or a 1Password/Bitwarden item). You do **not** create your own project.

## Tools (everyone)

| Tool | Version | Install |
|---|---|---|
| Git | any recent | already on macOS |
| Node.js | 20+ | [https://nodejs.org](https://nodejs.org) or `brew install node` |
| Bun | latest | `curl -fsSL https://bun.sh/install \| bash` then restart the terminal |
| uv (Python) | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` then restart the terminal |
| Python | 3.12 | `uv` will fetch it if missing |
| Cursor | latest | you are using it |

Check:

```bash
git --version
node -v          # v20 or v22
bun -v
uv --version
```

You do **not** need Docker for the default path. You do **not** need Redis.

## Clone (after Team Member 1 posts "repo is ready")

```bash
git clone git@github.com:<ORG>/AURA.git
cd AURA
git checkout -b feat/mN-<short>    # use YOUR branch from docs/04-WORKFLOW-RULES.md
```

Until M1 has pushed the initial `web/` and `api/` skeletons, you can still clone and read docs. Do not invent a parallel project in another folder.

## Environment files

There are two env files. Copy the examples; never commit the real ones.

```bash
cp .env.example .env                 # repo root, used by api/
cp web/env.example.txt web/.env.local   # name may be env.example.txt from Kiranism
```

Minimum in **root** `.env`:

```bash
GEMINI_API_KEY=your_personal_key_here
GEMINI_MODEL=gemini-2.0-flash
DATABASE_URL=postgresql://postgres:<password>@db.<ref>.supabase.co:5432/postgres
SUPABASE_URL=https://<ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<m1_will_give_this>
AURA_MOCK_AGENTS=true
API_HOST=0.0.0.0
API_PORT=8000
```

`AURA_MOCK_AGENTS=true` means no Gemini call happens anywhere. Two places honour it and that is deliberate: `graph.py` imports from `agents/_stubs.py` when the flag is on, and M4/M5's real functions also check it internally so they stay safe if M1 calls them directly. Flip to `false` once M4/M5 work; flip it back the instant Gemini 429s during the demo.

Frontend `web/.env.local`:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Do not put the Gemini key in the frontend env. The browser must never see it.

## Backend (api/)

From the repo root, after M1 has committed `api/pyproject.toml`:

```bash
cd api
uv sync
uv run uvicorn main:app --reload --port 8000
```

Open [http://localhost:8000/docs](http://localhost:8000/docs). You should see the FastAPI Swagger UI. Hit `GET /api/health` — it should return `{"ok": true}`.

If `api/` does not exist yet, you are before Hour 3. Wait.

## Frontend (web/)

Team Member 1 does the clone + cleanup **once** on `main`. Everyone else just installs:

```bash
cd web
bun install
bun run dev
```

Open [http://localhost:3000](http://localhost:3000). Dashboard should load.

### What Team Member 1 runs once (Hour 0, do not repeat)

```bash
# from repo root, empty web/ not yet present
git clone https://github.com/Kiranism/next-shadcn-dashboard-starter.git web
cd web
rm -rf .git
bun install
bun run cleanup clerk sentry kanban chat ai-chat notifications examples --force
# keep product + users + overview for copy-paste patterns; do not delete during the 8h sprint
rm -f AGENTS.md CLAUDE.md          # the starter ships its own; ours must win
cp env.example.txt .env.local
# set NEXT_PUBLIC_API_URL=http://localhost:8000
bun install
bun run dev
```

Those seven are the **only** valid feature names (verified against `scripts/cleanup.js`). `billing`, `workspaces`, `exclusive`, and `profile` are folders *inside* the `clerk` feature — passing them separately just prints "Unknown feature" and moves on. If the names ever change, run `bun run cleanup --list`.

Deleting the starter's `AGENTS.md` / `CLAUDE.md` matters: they land at `web/AGENTS.md`, Cursor auto-applies them to everything under `web/`, and they tell your agent to use Clerk and Sentry. Keep the notes elsewhere if you want them, just not at `web/`.

**Timebox: 25 minutes.** If Clerk removal leaves the app broken past that, stop cleaning and move on — a dead `/dashboard/profile` route costs nothing because it is not in the nav.

Then commit `web/` from the repo root (the inner `.git` was deleted, so it is just files).

## Database (Team Member 1 only)

1. Create a Supabase project `aura` (Singapore region is fine).
2. Project Settings → Database → copy URI. Use the **transaction** pooler or the direct URI; if `uv` / psycopg has SSL issues see troubleshooting.
3. SQL Editor → paste `db/schema.sql` → run.
4. SQL Editor → paste `db/seed.sql` → run.
5. SQL Editor → paste `db/demo.sql` → run. **This is part of Hour 0**, not the last hour — M2 has nothing to build against until the FAIL row exists.
6. Put `DATABASE_URL` and service role key in the team secret store. Members copy into local `.env`.

Resetting mid-sprint has to be safe, because the demo fallback is "re-run seed then demo":

- `seed.sql` only ever uses `insert ... on conflict do nothing`. **No `TRUNCATE`, no `DELETE`** — truncating `brands` cascades into every asset and review the team has created.
- `demo.sql` hardcodes its primary keys as fixed UUIDs and starts by deleting *those ids only*, so it is re-runnable and the demo asset URL never changes between rehearsal and performance.

## How a member verifies "I am unblocked"

You are unblocked when **all** of these work on your laptop:

1. `cd api && uv run uvicorn main:app --reload --port 8000` — `/api/health` 200.
2. `cd web && bun run dev` — dashboard renders.
3. Swagger `GET /api/brands` returns Jade, DoctorShield, Jaguar Transit (from seed).
4. You are on **your** branch, not `main`.

If (1) or (2) fail, you have a local install problem — do not wait for other members. If (3) fails, M1's seed is not in yet — work against the mock types in `docs/03-CONTRACTS.md` and keep files in your zone.

## Two terminals, always

| Terminal | Command | Port |
|---|---|---|
| A | `cd api && uv run uvicorn main:app --reload --port 8000` | 8000 |
| B | `cd web && bun run dev` | 3000 |

You do not run other people's agents as extra processes. They are Python functions imported by FastAPI.

## Optional: Docker

Only if M1 has spare time. Default path is local `uv` + `bun`. Do not spend Hour 0 on Docker.
