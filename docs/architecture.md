# Architecture

## System boundary

AURA is a single repository with two application processes and an optional
collector stack:

~~~text
Browser
  |
  v
Next.js dashboard (web/) :3000
  |
  | fetches NEXT_PUBLIC_API_URL
  v
FastAPI application (api/) :8000
  |-- route modules for campaigns, assets, review, leads, video, publishing
  |-- deterministic compliance rules
  |-- content/image/video provider adapters
  |-- background lead refresh and competitor refresh workers
  |-- SQLite or MySQL application data
  |-- /media and /storage static mounts
  |
  +--> optional Docker collectors
       changedetection + browser-chrome
       SearXNG discovery profile
       RSSHub + Redis social-feed profile
~~~

The collector package in competitor-intelligence is imported into the FastAPI
process. It is not a second HTTP application and it does not use an iframe.
The API owns startup, routes, the shared AURA SQLite path, and the refresh
worker.

## Main product flow

~~~text
Campaign brief
  |
  +--> brand profile + previously saved lessons
  |
  +--> content generation
  |      demo/local deterministic path, or Groq-backed path
  |
  +--> platform content + optional image/video media persisted
  |
  +--> deterministic compliance checks where the pipeline invokes them
  |
  +--> human review queue
          |-- approve -> final media + optional Buffer publication
          |-- edit    -> new content version and optional lesson
          |-- reject  -> reason + lesson for later generation
~~~

There are two campaign entry paths in the current code:

1. Standard campaign: POST /api/campaigns creates a draft and schedules
   api/graph.py run_pipeline as a FastAPI background task. That pipeline loads
   lessons, generates one asset per platform, runs the compliance gate, and
   stores content_assets and compliance_checks.
2. Campaign Studio: POST /api/campaigns/studio/generate loads lessons, calls
   the Studio content generator synchronously in demo or Groq mode, and stores
   the complete multi-platform package in campaigns and
   campaign_platform_content. Studio then supports media generation,
   watermarking, review submission, editing, resubmission, and publishing.

The two paths share database tables and review/publishing concepts but are not
the same implementation. Do not describe AURA as a LangGraph workflow: the
current pipeline is intentionally small and does not import LangGraph.

## Review and learning loop

Review decisions are stored in review_queue, reviews, campaign_events, and
lessons. A rejection records a reason tag and reviewer note. Those lessons are
loaded into later generation prompts for the same brand and can be scoped to a
platform. Resubmission creates a new review cycle while preserving prior
history.

The compliance implementation is deterministic and local. The rules live in
api/rules/insurance_compliance/rubric.py and the gate lives in
api/rules/insurance_compliance/gate.py. It is a product safety aid, not legal
or regulatory approval.

## Competitor intelligence flow

~~~text
competitor registry + watch registry + feed registry
  |
  +--> direct website collector
  +--> changedetection webhook/history
  +--> RSS/RSSHub feeds
  +--> optional SearXNG search
  |
  v
normalize transient UI -> hash -> compare snapshot
  |
  +--> baseline snapshot
  +--> meaningful change event
          |-- evidence and confidence in SQLite
          |-- optional Gemini explanation
          +-- native dashboard via /api/competitors/*
~~~

The worker initializes registries at API startup and, unless disabled, loops at
AURA_COMPETITOR_SCAN_INTERVAL seconds. Individual source failures are logged
and isolated so the API can remain available. See the specialized competitor
documents for watch provisioning and collector operations.

## Persistence and files

- Structured data: storage/aura.db by default, or MySQL when configured.
- Generated media: storage/campaigns/{campaign_id}/.
- API logs: .aura/logs/api.log.
- Frontend logs: .aura/logs/web.log.
- Launcher PID files: .aura/run/.
- Collector volumes: Docker-managed volumes declared in
  competitor-intelligence/compose.yaml.

api/main.py mounts storage at both /media and /storage. Publishing uses /media
and requires a public base URL because Buffer cannot read localhost. When the
configured public media host is used, middleware allows only read-only
`/media/*` requests and `GET /api/health`; the local origin retains the full
development API.

## External boundaries

Provider integrations are deliberately kept behind small adapters:

- Groq: text generation in api/services/content_generator.py.
- FAL: image/video generation when real generation is enabled.
- Gemini: optional competitor-event analysis and legacy test helpers.
- TinyFish: lead discovery.
- Gmail SMTP/app password: lead email sending.
- Buffer: queued social publication.

Provider credentials are read by the backend. They must not be moved into
NEXT_PUBLIC_* variables, which are visible to the browser.
