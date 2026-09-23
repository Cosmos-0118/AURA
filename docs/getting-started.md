# Getting started and runbook

## Prerequisites

Install:

- Python 3.12 or newer
- uv
- Bun
- Docker Desktop with Docker Compose if competitor collectors are enabled
- curl (included on current macOS and Windows 10+)

The macOS launcher requires uv, Bun, and curl. The Windows launcher accepts Bun
or npm for the frontend, but uv and curl.exe are still required.

## First-time setup

From the repository root:

~~~bash
cp .env.example .env
cp web/env.example.txt web/.env.local
~~~

Keep secrets only in these ignored local files. The templates contain both
current and legacy provider variables; use the configuration guide to decide
which ones are needed.

The launcher creates storage and .aura runtime directories as needed. With the
default DB_ENGINE=auto and no reachable MySQL host, the API initializes
storage/aura.db automatically and seeds baseline brands/lessons.

## Recommended launcher commands

macOS/Linux:

~~~bash
# Interactive menu: build only, build + run, just run, or dev mode
./scripts/macos/start.sh

# Clean generated output, install locked dependencies, typecheck, build
./scripts/macos/aura.sh build

# Start API and Next.js with hot reload
./scripts/macos/aura.sh dev

# Clean, build, then start production frontend + API
./scripts/macos/aura.sh up

# Start an existing web/.next production build
./scripts/macos/aura.sh start

# Stop tracked processes, free ports, and stop collector containers
./scripts/macos/aura.sh stop
~~~

Convenience wrappers are available as build.sh, clean.sh, start.sh, stop.sh,
and up.sh in scripts/macos/.

Windows PowerShell:

~~~powershell
.\scripts\windows\start.ps1
.\scripts\windows\build.ps1
.\scripts\windows\aura.ps1 dev
.\scripts\windows\up.ps1
.\scripts\windows\stop.ps1
~~~

The Windows interactive menu and the macOS menu have the same four modes.

## Manual development fallback

Use two terminals when the launcher is not suitable:

~~~bash
# Terminal 1
cd api
uv sync --frozen
uv run uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2
cd web
bun install --frozen-lockfile
bun run dev
~~~

Set web/.env.local with NEXT_PUBLIC_API_URL=http://localhost:8000 before
starting the frontend. The frontend defaults to that URL when the variable is
missing.

## URLs and ports

| Service | Default URL | Purpose |
| --- | --- | --- |
| Dashboard | http://localhost:3000 | Next.js application |
| API | http://localhost:8000 | FastAPI |
| Swagger | http://localhost:8000/docs | Interactive API docs |
| Health | http://localhost:8000/api/health | API and intelligence readiness |
| Changedetection | http://127.0.0.1:5001 | Browser/page collector UI |
| SearXNG | http://127.0.0.1:8080 | Optional discovery search |
| RSSHub | http://127.0.0.1:1200 | Optional feed adapter |

Ports can be changed through API_PORT, WEB_PORT, CHANGEDETECTION_PORT,
SEARXNG_PORT, and RSSHUB_PORT in the root `.env`; the launchers import these
values before starting or stopping the stack. API_HOST is a shell/environment
override: macOS/Linux defaults to 0.0.0.0 and Windows defaults to 127.0.0.1.
If API_PORT changes, update `NEXT_PUBLIC_API_URL` in `web/.env.local` before
building the frontend because the browser API origin is bundled at build time.
The reserved Buffer/ngrok workflow is intentionally fixed to API_PORT=8000 and
the exact command documented below.

## Collector modes

The launcher enables competitor intelligence by default. Docker is required
when AURA_COMPETITOR_REQUIRED=true.

To run only the API and frontend:

~~~bash
AURA_COMPETITOR_INTELLIGENCE=false ./scripts/macos/aura.sh dev
~~~

If collectors are useful but Docker is temporarily unavailable, set
AURA_COMPETITOR_REQUIRED=false. The launcher continues with the application and
reports collector health as unavailable. See the competitor runbook for manual
Compose commands.

## Production build lifecycle

The launcher owns only local processes. build runs uv sync, Python compilation,
Bun lockfile installation, frontend typecheck, and Next.js build. start requires
web/.next/BUILD_ID and starts the production frontend plus the API. up performs
clean, build, and start. dev skips the production build and starts Next.js in
development mode.

## First verification

After startup:

~~~bash
curl http://localhost:8000/api/health
curl http://localhost:8000/api/media/config
~~~

Open the dashboard at /dashboard/studio and confirm that the Studio page can
load brands. If the API is not ready, inspect .aura/logs/api.log and
.aura/logs/web.log.

## Buffer publishing prerequisite

Buffer cannot download media from localhost. If the review workflow includes
image or video publishing, start the reserved ngrok tunnel in a separate
terminal after the API is listening. Install ngrok from its official
distribution, authenticate it with your team account, and confirm that the
reserved domain is assigned to that account before starting:

~~~bash
ngrok config add-authtoken <your-ngrok-authtoken>
~~~

Then start the tunnel:

~~~bash
ngrok http --url=perceptually-homocentric-lindy.ngrok-free.dev 8000
~~~

Leave that process running continuously while Buffer is being used. In the
root .env, set:

~~~dotenv
MEDIA_PUBLIC_BASE_URL=https://perceptually-homocentric-lindy.ngrok-free.dev
~~~

Then verify both sides:

~~~bash
curl http://localhost:8000/api/media/config
curl --fail https://perceptually-homocentric-lindy.ngrok-free.dev/api/health
~~~

The first command checks AURA configuration; the second confirms that the
reserved public origin is currently forwarding to port 8000. This is a
publishing prerequisite, not an optional convenience.
