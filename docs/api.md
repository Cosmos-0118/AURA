# API and frontend integration

## API contract

The FastAPI app is created in api/main.py and listens on port 8000 by default.
When it is running, the generated contract is available at:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

The frontend API base is web/src/lib/api/client.ts and comes from
NEXT_PUBLIC_API_URL, defaulting to http://localhost:8000. The browser does not
call provider APIs directly.

## Route matrix

| Prefix | Responsibilities | Main callers |
| --- | --- | --- |
| /api/health, /api/logos | Health, readiness, available logos | launcher, layout, diagnostics |
| /api/brands | Brand profiles | Studio, brand selectors |
| /api/campaigns | Standard and Studio campaigns, media, review, history, publishing | Studio, Review, History |
| /api/assets | Standard-pipeline asset queue, approval, rejection, edits, localization | review/asset surfaces |
| /api/lessons | Saved reviewer guidance | Insights and generation |
| /api/metrics | Counts and compliance/review metrics | Overview |
| /api/leads | Lead list, refresh, email draft/send | Leads page |
| /api/video | Video generation, attachment, exports, history, config | Video page |
| /api/media | Local media configuration diagnostics | publishing setup |
| /api/buffer | Buffer status, channels, publish helper | publishing setup |
| /api/competitors | Registry, scans, events, evidence, webhooks, feeds, search | Competitor Intelligence |

## Key campaign lifecycle endpoints

~~~text
POST /api/campaigns/studio/generate
GET  /api/campaigns/{id}/studio
POST /api/campaigns/{id}/generate-image
POST /api/campaigns/{id}/generate-video
POST /api/campaigns/{id}/apply-watermark
POST /api/campaigns/{id}/submit-review
GET  /api/campaigns/review-queue
POST /api/campaigns/{id}/approve
POST /api/campaigns/{id}/reject
POST /api/campaigns/{id}/edit
POST /api/campaigns/{id}/resubmit
POST /api/campaigns/{id}/publish/{platform}
GET  /api/campaigns/{id}/history
GET  /api/campaigns/{id}/publications
~~~

Publishing accepts linkedin, instagram, and x. It requires an approved
campaign, current content, completed final watermarked media, a reachable
public media URL, and valid Buffer configuration.

## Competitor intelligence endpoints

~~~text
GET  /api/competitors/dashboard
GET  /api/competitors
POST /api/competitors/{competitor_id}/scan
POST /api/competitors/scan-all
POST /api/competitors/watches/{watch_id}/scan
GET  /api/competitors/events
GET  /api/competitors/events/{event_id}/diff
POST /api/competitors/events/{event_id}/analyze
POST /api/competitors/webhooks/changedetection
POST /api/competitors/sync-changedetection
POST /api/competitors/poll-feeds
POST /api/competitors/search
~~~

The webhook optionally checks X-Webhook-Token against INTEL_WEBHOOK_TOKEN.

## Frontend behavior

The dashboard pages are under web/src/app/dashboard:

- overview: metrics and operating summary
- studio: campaign generation, media, watermarking, submission
- review: human decisions, edits, rejection lessons, publication
- history: campaign audit history and resubmission
- leads: discovery and outreach
- video: video generation and export history
- publish: Buffer channel and publication actions
- competitor-intelligence: watches, scans, evidence, and events

web/src/lib/api/client.ts centralizes request construction and JSON error
handling. Some read paths have local demo fallback data when the API request
fails, while mutation paths generally surface the error. The current
getStoredApiMode implementation always returns real, so do not use a fallback
as proof that the backend is healthy.

The repository also contains Next.js demo/API-template routes under
web/src/app/api and web/src/lib/demo. They are not a replacement for the
FastAPI API and should not be treated as an independently deployed backend.
