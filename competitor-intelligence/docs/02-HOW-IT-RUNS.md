# Competitor Intelligence: How It Runs

## One launcher

Run AURA through the main macOS launcher:

```bash
./scripts/macos/aura.sh up       # clean, build, start production AURA
./scripts/macos/aura.sh dev      # start API and Next.js with hot reload
./scripts/macos/aura.sh start    # start an existing production build
./scripts/macos/aura.sh stop     # stop AURA and collector containers
```

The launcher no longer starts a separate intelligence server. When competitor
intelligence is enabled it automatically starts the collector dependencies,
waits for their health endpoints, exports their AURA connection settings, and
provisions configured changedetection watches to the main AURA webhook.

## Collector services

The Compose file in this directory supplies:

| Service | Default endpoint | Role |
| --- | --- | --- |
| `changedetection` | `http://127.0.0.1:5001` | Browser/page history and webhooks |
| `browser-chrome` | internal Compose network | Chrome CDP runtime for difficult pages |
| `searxng` | `http://127.0.0.1:8080` | Optional discovery search |
| `rsshub` | `http://127.0.0.1:1200` | Optional LinkedIn/YouTube/public feed adapter |
| `rsshub-redis` | internal Compose network | RSSHub cache |

The AURA API itself remains on port `8000`; the Next.js app remains on port
`3000`. Port `8787` is no longer part of the AURA runtime.

## Environment controls

These values belong in the root `.env` file:

```dotenv
AURA_COMPETITOR_INTELLIGENCE=true
AURA_COMPETITOR_REQUIRED=true
AURA_COMPETITOR_DISCOVERY=true
AURA_COMPETITOR_REFRESH=true
AURA_COMPETITOR_SCAN_INTERVAL=900
CHANGEDETECTION_PORT=5001
SEARXNG_PORT=8080
RSSHUB_PORT=1200
CHANGEDETECTION_API_KEY=
INTEL_WEBHOOK_TOKEN=
GEMINI_API_KEY=
GEMINI_MODEL=gemini-2.0-flash
```

`AURA_COMPETITOR_REQUIRED=true` makes startup fail when Docker Compose or
changedetection cannot start. Set it to `false` when direct website scans are
enough and collector containers should be best-effort. Set
`AURA_COMPETITOR_INTELLIGENCE=false` to run AURA without starting any
competitor collector containers.

The launcher reads the changedetection API token from the local datastore when
`CHANGEDETECTION_API_KEY` is empty. It then provisions the watch registry with
the webhook target:

```text
post://host.docker.internal:8000/api/competitors/webhooks/changedetection
```

If a webhook token is configured, it is attached to the provisioned watch and
validated by the AURA route.

On the first API startup after this integration, rows from the former
`competitor-intelligence/data/intelligence.db` are imported into
`storage/aura.db` without overwriting existing IDs. Set
`AURA_INTELLIGENCE_LEGACY_DB` when the old database is stored elsewhere. The
collector store currently requires SQLite; when `DB_ENGINE=mysql` is selected,
the competitor routes report that requirement instead of quietly reading a
separate database.

## Manual collector operations

The main launcher is the normal entry point. For collector-only maintenance,
use the Compose file from this directory:

```bash
docker compose --env-file ../.env \
  --profile discovery --profile social \
  up -d changedetection searxng rsshub-redis rsshub

docker compose --env-file ../.env \
  --profile discovery --profile social \
  down --remove-orphans
```

Manual operations do not start another intelligence API. The AURA API must be
running for webhooks and the native dashboard.

## Health and troubleshooting

1. Open `http://localhost:8000/api/health` to check the main API.
2. Open `/dashboard/competitor-intelligence` in AURA and inspect Collector
   health.
3. Check `http://127.0.0.1:5001/` for changedetection.
4. Check the AURA API log under `.aura/logs/api.log` for worker errors.
5. Check Compose logs with `docker compose logs --tail=80 changedetection`.

If Docker is unavailable, direct website scans can still work when
`AURA_COMPETITOR_REQUIRED=false`; changedetection, RSSHub, and SearXNG will be
reported as unavailable instead of blocking the app.
