# Operations and troubleshooting

## Runtime artifacts

The local launcher writes:

| Path | Contents |
| --- | --- |
| .aura/logs/api.log | FastAPI, startup, worker, and provider errors |
| .aura/logs/web.log | Next.js output |
| .aura/run/api.pid | Tracked API process |
| .aura/run/web.pid | Tracked frontend process |
| .aura/uv-cache, .aura/bun-cache | Local dependency caches |
| .aura/tmp | Launcher temporary files |
| storage/aura.db | Default SQLite state |
| storage/campaigns/ | Generated images and videos |

The clean command removes generated build/runner output and local caches. It
does not replace a database backup and should not be used as a data reset.

## Health checks

~~~bash
curl --fail http://localhost:8000/api/health
curl --fail http://localhost:8000/api/media/config
curl --fail http://127.0.0.1:5001/
~~~

The root /api/health response reports basic API status and competitor
intelligence readiness. For database and provider diagnostics, use
/api/campaigns/health. /api/media/config reports only whether a valid public
media base URL is configured; it does not verify that a particular campaign
file is reachable.

## Common failures

### Launcher says a port is busy

Run the stop command, then inspect the listener:

~~~bash
./scripts/macos/aura.sh stop
lsof -nP -iTCP:3000 -sTCP:LISTEN
lsof -nP -iTCP:8000 -sTCP:LISTEN
~~~

The launcher attempts to reclaim every listener on its configured API and web
ports, including listeners it did not start, and may force-kill them. Inspect
the listener first and do not run the launcher on a shared machine or when an
unrelated service owns either port. If that is possible, use the manual
two-terminal commands in the getting-started guide instead.

### Backend does not become ready

Inspect .aura/logs/api.log. Common causes are a bad MySQL configuration,
missing Python dependency sync, a collector initialization error, or a
provider/import error. Set AURA_COMPETITOR_INTELLIGENCE=false to separate core
API startup from collector startup.

### Frontend loads but requests fail

Check web/.env.local and confirm NEXT_PUBLIC_API_URL points to the running API.
Then call /api/health directly. Browser console errors usually indicate a
CORS/origin or API-port mismatch.

### Docker collectors fail

Check Docker Desktop and Compose:

~~~bash
docker compose --env-file .env \
  -f competitor-intelligence/compose.yaml \
  --project-directory competitor-intelligence \
  ps

docker compose --env-file .env \
  -f competitor-intelligence/compose.yaml \
  --project-directory competitor-intelligence \
  logs --tail=80 changedetection browser-chrome
~~~

The changedetection service depends on browser-chrome. SearXNG and RSSHub are
profile-based and can be unavailable without blocking direct website scans
when AURA_COMPETITOR_REQUIRED=false.

### Competitor page changes are missing

Check /api/competitors/source-health, then /api/competitors/watches and the
collector UI. Run a targeted scan or poll manually. A first observation creates
a baseline; only a meaningful normalized change creates an event. Consent
banners, market redirects, and access interstitials are intentionally rejected
as baselines.

### Buffer publication fails

Check the campaign is approved, final watermarked media exists, and
/api/media/config reports configured=true. From outside the local network,
open the generated /media URL. Buffer requires an accessible HTTP(S) URL and
will reject localhost. Inspect the publication record and API log before
retrying; duplicate publication protection may intentionally report that a
post already exists.

If the public URL is unavailable, start
scripts/macos/buffer-tunnel.sh or scripts/windows/buffer-tunnel.ps1 in a
separate terminal and keep it running. The helper checks the running API's
`/api/media/config` before starting and exits if the reserved URL is not
configured. It is intentionally not detached, so its terminal is the
operator-visible owner of the publishing dependency.

### Lead refresh or email fails

Check TinyFish_API_KEY/TINYFISH_API_KEY, LEAD_FROM_EMAIL, and
GMAIL_APP_PASSWORD. Disable the startup worker with AURA_LEAD_REFRESH=false
when external lead discovery is not wanted.

## Backup and recovery

Back up the database and storage/campaigns together. MySQL dumps do not include
local media binaries. Collector volumes contain changedetection/RSSHub runtime
state; their registries are reproducible from competitor-intelligence/config,
but history is not.

Never use AURA_ALLOW_RESET_DATA=true on a shared environment. The reset route
is destructive to campaign/review/publication/event state.
