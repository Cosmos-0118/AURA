# Configuration and environment variables

AURA reads the root .env through python-dotenv. The browser-facing Next.js
process reads web/.env.local. Do not put provider secrets in web/.env.local
unless the variable is explicitly NEXT_PUBLIC_*; Next.js exposes
NEXT_PUBLIC_* values to the browser.

Copy the templates first:

~~~bash
cp .env.example .env
cp web/env.example.txt web/.env.local
~~~

## Required for the default local demo

| Variable | Default | Meaning |
| --- | --- | --- |
| DEMO_MODE | true in the template | Studio uses deterministic/local generation instead of Groq |
| AURA_MOCK_AGENTS | true in the template | The older standard pipeline uses local agent stubs |
| DB_ENGINE | auto | Try MySQL when configured, otherwise use SQLite |
| API_HOST / API_PORT | platform default / 8000 | FastAPI bind address and port; macOS/Linux defaults to 0.0.0.0, Windows to 127.0.0.1 |
| NEXT_PUBLIC_API_URL | http://localhost:8000 | API origin used by the browser |
| NEXT_PUBLIC_APP_URL | http://localhost:3000 | Frontend public origin used for metadata |

The launcher requires the root .env file to exist. It does not require a
DATABASE_URL for the active SQLite/MySQL connection layer despite the legacy
wording in the launcher error message.

## Database

| Variable | Meaning |
| --- | --- |
| DB_ENGINE=auto | Use MySQL when MYSQL_HOST is set and reachable; otherwise SQLite |
| DB_ENGINE=sqlite | Force storage/aura.db |
| DB_ENGINE=mysql | Require MySQL; fail instead of falling back |
| MYSQL_HOST | MySQL host; leaving it empty enables SQLite fallback |
| MYSQL_PORT | MySQL port, normally 3306 |
| MYSQL_DATABASE | Database name, normally aura |
| MYSQL_USER / MYSQL_PASSWORD | MySQL credentials |
| AURA_INTELLIGENCE_DB | Optional SQLite path for competitor intelligence |
| AURA_INTELLIGENCE_LEGACY_DB | Optional path to an older intelligence.db to import |

Competitor intelligence currently requires SQLite when DB_ENGINE is explicitly
mysql. With the default auto mode, the main application may use MySQL while the
competitor intelligence service still uses its SQLite store; choose this
deliberately and document the split for any shared environment.

## Demo and AI providers

| Variable | Used by | Notes |
| --- | --- | --- |
| DEMO_MODE | Campaign Studio | Set false to request Groq-backed Studio generation |
| GROQ_API_KEY | Studio/content generator | Required when real text generation is selected |
| GROQ_MODEL | Studio/content generator | Model name; code supplies a fallback |
| AURA_MOCK_AGENTS | Standard api/graph.py pipeline | true selects deterministic stubs |
| GEMINI_API_KEY / GEMINI_MODEL | Competitor event analysis and legacy helpers | Optional; deterministic analysis remains available |
| FAL_KEY or FAL_AI_API_KEY | Image/video providers | Required for real media generation |
| IMAGE_MODEL | Image generation | Provider model identifier |
| VIDEO_MODEL | Video generation | Provider model identifier |

The API exposes the current mode and provider-key presence through campaign
mode/health routes without returning secret values.

## Competitor intelligence

| Variable | Default | Meaning |
| --- | --- | --- |
| AURA_COMPETITOR_INTELLIGENCE | true | Start collector support |
| AURA_COMPETITOR_REQUIRED | true | Fail startup when required collectors cannot start |
| AURA_COMPETITOR_DISCOVERY | true | Start the discovery profile for SearXNG |
| AURA_COMPETITOR_REFRESH | true | Start the API background refresh worker |
| AURA_COMPETITOR_SCAN_INTERVAL | 900 | Minimum worker interval in seconds; code clamps to 60 seconds |
| CHANGEDETECTION_PORT | 5001 | Host port for changedetection |
| SEARXNG_PORT | 8080 | Host port for SearXNG |
| RSSHUB_PORT | 1200 | Host port for RSSHub |
| CHANGEDETECTION_API_KEY | empty | Optional explicit changedetection API key |
| CHANGEDETECTION_API_URL | http://changedetection:5000 | Collector-internal URL |
| INTEL_WEBHOOK_TOKEN | empty | Optional X-Webhook-Token expected by the API |
| SEARXNG_URL | empty | Optional direct search endpoint |
| INTEL_COMPETITORS / INTEL_WATCHES / INTEL_FEEDS | bundled paths | Override JSON registry files |

Advanced Compose settings such as CHANGEDETECTION_BIND_HOST,
PLAYWRIGHT_DRIVER_URL, FETCH_WORKERS, and browser temporary-directory limits
are defined in competitor-intelligence/compose.yaml. Keep changedetection
bound to localhost unless it is protected by an access-controlled proxy.

## Publishing, media, leads, and email

| Variable | Feature | Notes |
| --- | --- | --- |
| BUFFER_API_KEY | Buffer publishing | Server-side secret |
| BUFFER_ORGANIZATION_ID | Buffer | Optional organization override |
| BUFFER_LINKEDIN_CHANNEL_ID / BUFFER_INSTAGRAM_CHANNEL_ID / BUFFER_X_CHANNEL_ID | Buffer | Optional channel overrides |
| BUFFER_PUBLISH_MODE | Buffer | Defaults to addToQueue |
| MEDIA_PUBLIC_BASE_URL | Buffer media | Public HTTP(S) origin for /media; localhost is rejected by the backend validator. The documented local Buffer workflow uses the reserved HTTPS ngrok origin |
| SKIP_MEDIA_URL_REACHABILITY_CHECK | Buffer media | Only use for controlled tests |
| AURA_LEAD_REFRESH | Lead worker | Defaults to true; set false to disable the startup worker |
| LEAD_REFRESH_HOURS | Lead worker | Minimum age before checking for a newer Overture release; defaults to 720 hours |
| LEAD_REFRESH_POLL_SECONDS | Lead worker | Retry/release-check poll interval; defaults to 300 seconds and has a 60-second minimum |
| LEAD_JOB_POLL_SECONDS | Lead worker | Website enrichment queue poll interval; defaults to 30 seconds and has a 5-second minimum |
| LEAD_MAX_JOBS_PER_RUN | Lead worker | Website jobs to process in one run; defaults to 300 |
| LEAD_CRAWL_DELAY_SECONDS | Lead worker | Pause between company websites; defaults to 0.35 seconds |
| LEAD_HUNTER_RETRY_HOURS | Lead worker | Delay before retrying failed monthly Hunter discovery; defaults to 6 hours |
| DUCKDB_EXTENSION_DIRECTORY | Overture query | Writable DuckDB extension cache; defaults to `.aura/duckdb_extensions` under the application root |
| HUNTER_API_KEY | Optional lead discovery and email enrichment | Hunter Discover adds a secondary source; Domain Search is used only for qualified leads that lack a public email |
| LEAD_HUNTER_DISCOVER_ENABLED | Hunter Discover | Defaults to true when a Hunter key is configured; set false to disable secondary discovery |
| LEAD_HUNTER_MONTHLY_CREDIT_LIMIT | Hunter Domain Search | Local monthly cap, defaults to 45 to leave quota headroom |
| LEAD_PLAYWRIGHT_ENABLED | Optional JS website fallback | Defaults to false; requires installing the `lead-browser` extra and Chromium |
| LEAD_GEMINI_ENABLED / LEAD_GEMINI_MODEL | Optional ambiguous-fit classification | Defaults to disabled; uses `GEMINI_API_KEY` only when enabled and configured |
| LEAD_FROM_EMAIL | Lead email | Sender mailbox |
| GMAIL_APP_PASSWORD | Lead email | Gmail app password, never a normal account password |

The Lead Intelligence core does not require Hunter, Gemini, or a paid search
provider. Overture Places is queried from its public GeoParquet release and
websites are fetched directly. See [Lead Intelligence](lead-intelligence.md)
for the source, scoring, refresh, and review workflow.

Buffer publication is an external side effect. Configure and test
MEDIA_PUBLIC_BASE_URL and /api/media/config before enabling it. See
buffer-publishing.md for the complete tunnel and reachability flow.

For this project local Buffer flow, the expected value is
https://perceptually-homocentric-lindy.ngrok-free.dev and the tunnel command
is:

~~~bash
ngrok http --url=perceptually-homocentric-lindy.ngrok-free.dev 8000
~~~

The ngrok process must stay running for the entire publish session. If the
reserved domain is unavailable, do not silently substitute localhost; update
the environment value and verify the replacement origin first.

## Frontend and build variables

| Variable | Meaning |
| --- | --- |
| NEXT_PUBLIC_API_URL | API origin embedded into browser-side requests |
| NEXT_PUBLIC_APP_URL | Frontend origin used for Open Graph/Twitter metadata |
| BUILD_STANDALONE=true | Enables Next.js standalone output in next.config.ts |
| PORT | Runtime frontend port; launcher sets it from WEB_PORT |
| WEB_PORT | Launcher frontend port, default 3000; if API_PORT changes, update web/.env.local before building |
| UV_CACHE_DIR / BUN_INSTALL_CACHE_DIR | Optional local cache locations |

## Legacy or misleading template entries

DATABASE_URL and SUPABASE_* are retained in the template for historical
experiments. The active database code uses MYSQL_* or SQLite and does not read
those variables. FAL_KEY appears more than once in the current template; keep
one effective value. Clean up legacy variables only after checking their
callers with a repository search.
