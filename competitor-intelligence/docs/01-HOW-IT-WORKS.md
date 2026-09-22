# Competitor Intelligence: How It Works

## Purpose

Competitor Intelligence is AURA's evidence-first monitoring lane. It watches
public competitor pages and feeds, detects meaningful changes, classifies their
business impact, and exposes the result inside the normal AURA dashboard.

The module is not a second web application. The FastAPI process in `api/`
owns the HTTP routes, background refresh worker, webhook receiver, and shared
SQLite data store at `storage/aura.db`. The Next.js page calls those AURA
routes directly; it does not use an iframe or a port-8787 server.

## Data flow

```text
competitor registry + watch registry
        |
        +--> direct website collector
        +--> changedetection.io webhook/history
        +--> RSS/RSSHub feed collector
        +--> optional SearXNG search adapter
        |
        v
        normalize content -> hash source stream -> compare with last snapshot
        |
        +--> baseline snapshot
        +--> meaningful change classification
                    |
                    v
              stored change event
                    |
                    +--> AURA dashboard feed
                    +--> optional Gemini explanation
```

Each competitor can have several watch streams. A product page, pricing page,
news page, and feed are kept separate so one source cannot overwrite another
source's history. A first observation creates a baseline; later meaningful
content changes create an event with impact, evidence, confidence, and a
recommended action.

Website and changedetection text is normalized before comparison. Consent
banners, market or country prompts, and their short controls are removed when
they are recognizable as transient UI. Captures that contain only transient UI,
an access interstitial, or an unexpected market redirect are rejected so they
cannot replace a valid baseline. Stored event evidence is normalized as well,
including evidence from older snapshots, before it is shown or sent to the
optional AI analyst.

## What it uses

- `competitor_intelligence/models.py` — competitor, watch, snapshot, event,
  and scan-result data objects.
- `competitor_intelligence/collectors.py` — website, RSS, changedetection
  content, and optional SearXNG collection.
- `competitor_intelligence/analysis.py` — content hashing, diff summaries,
  deterministic change classification, and confidence scoring.
- `competitor_intelligence/service.py` — registry sync, scans, feed polling,
  changedetection reconciliation, event filtering, and analysis orchestration.
- `competitor_intelligence/store.py` — SQLite persistence, source-stream
  history, event deduplication, and legacy-column migration.
- `competitor_intelligence/ai.py` — optional Gemini analysis. Deterministic
  keyword relevance remains available when no Gemini key is configured.
- `config/competitors.json` — the competitor registry.
- `config/watches.json` — the page watches and polling intervals.
- `config/feeds.json` — RSS/RSSHub feeds associated with competitors.

## AURA API surface

All routes are served by the main API at `http://localhost:8000`:

- `GET /api/competitors` — contract-compatible competitor list.
- `GET /api/competitors/dashboard` — summary, competitors, monitors, watches,
  events, and source health for the native dashboard.
- `POST /api/competitors/{id}/scan` — scan one competitor and return its latest
  persisted snapshot.
- `POST /api/competitors/scan-all` — run all configured watches/competitors.
- `GET /api/competitors/events` — filter the event feed by brand, country,
  impact, change type, source, or search text.
- `GET /api/competitors/events/{id}/diff` — retrieve before/after evidence.
- `POST /api/competitors/events/{id}/analyze` — request optional Gemini
  analysis for a stored event.
- `POST /api/competitors/webhooks/changedetection` — receive collector events.
- `POST /api/competitors/sync-changedetection` — import missed history.
- `POST /api/competitors/poll-feeds` — poll configured RSS/RSSHub feeds.
- `POST /api/competitors/search` — query the optional SearXNG adapter.

## Background behavior

On AURA startup, the API initializes the registry and starts a daemon refresh
worker unless `AURA_COMPETITOR_REFRESH=false` or tests are running. The worker
periodically reconciles changedetection history, scans due watches, and polls
configured feeds. Its interval is controlled by
`AURA_COMPETITOR_SCAN_INTERVAL` and defaults to 900 seconds.

The worker is deliberately best-effort: a failing website or unavailable
optional collector is isolated and logged, while the AURA API stays available.
