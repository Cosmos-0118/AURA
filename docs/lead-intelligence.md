# Lead Intelligence

Lead Intelligence discovers prospective businesses for Jade, DoctorShield, and
Jaguar Transit, verifies evidence from public company websites, scores the fit,
and keeps outreach behind an explicit review step.

## Free-first sources

The default discovery source is Overture Maps Places. The API reads the latest
published release from Overture's STAC catalog and queries its Places
GeoParquet files with DuckDB. The current implementation uses the schema v2
`taxonomy` and `basic_category` fields; Overture's September 2026 release
removed the legacy `categories` field. See the [release notes](https://docs.overturemaps.org/blog/2026/09/23/release-notes/)
and [Places taxonomy documentation](https://docs.overturemaps.org/guides/places/taxonomy-explorer/).

The ICP configuration is [api/config/lead_icps.json](../api/config/lead_icps.json).
It defines target countries and their query bounding boxes, valid Overture
category IDs, website keywords, a minimum source confidence of 0.80, and the
qualification threshold. Update this file
when a brand's intended customer profile changes. Category IDs should be
checked against the [Overture taxonomy explorer](https://docs.overturemaps.org/guides/places/taxonomy-explorer/).

Hunter is optional. When `HUNTER_API_KEY` is configured, its free Discover
endpoint can contribute up to 100 companies per filtered request; the current
endpoint limits free users from offset pagination. The code runs one filtered
request per brand and country. Hunter Domain Search is used only for leads that
meet the qualification threshold and still lack a usable email, with a local
monthly credit cap. Review the [Hunter API reference](https://hunter.io/api-documentation#discover)
and your account plan before enabling it; availability and quotas can change.

## Pipeline and evidence

~~~text
Overture Places (+ optional Hunter Discover)
  -> confidence, status, country, and taxonomy filtering
  -> company account and location resolution
  -> robots.txt check and bounded HTTP fetch
  -> homepage, contact/about/team/location pages, sitemap, and JSON-LD
  -> evidence and contact records with source URL and observation time
  -> deterministic fit score
  -> optional Gemini classification for ambiguous cases
  -> qualified lead review
  -> approved email draft and explicit send
~~~

Normal HTML fetching uses pinned TCP connections and Beautiful Soup. It resolves
the hostname once per request, rejects any non-public DNS answer, connects to
one of the checked IP addresses, preserves the original Host header and TLS
server name, rechecks every redirect, checks the destination origin's robots
rules before following it, limits response size and page count, and does not
fetch pages disallowed by robots.txt.
Playwright is an optional JavaScript-rendering fallback. It is off by default
and can be enabled with `LEAD_PLAYWRIGHT_ENABLED=true` after installing the
`lead-browser` extra and its Chromium browser. The browser pins the company host
to a checked public IP, denies DNS for other hosts, applies the robots check to
navigation requests, and blocks cross-origin requests, WebSockets, and non-read
methods.

Each stored email, phone, website, taxonomy, keyword match, and verification
page has an evidence record with its source and observation timestamp. Website
emails are syntax-checked and checked for a working MX record; the app does not
guess person-specific email addresses. Contact and fit evidence points to the
page where it was observed. Discovery records retain their provider and
release. They do not attribute Overture or Hunter records to the business
website. Contacts absent from current website
and location evidence are marked stale and removed from the outreach fields.
Hunter email search is a last resort
for qualified leads, prefers generic addresses, and requests only addresses
whose Hunter verification status is `valid`. This uses the Domain Search
response metadata without making a separate verifier request.

## Account resolution and scoring

When a public website domain exists, AURA uses the normalized domain within a
brand as the account key, and stores each Overture place under that account as
a location. Without a domain, it groups records by normalized public business
phone, then by normalized name and country after removing location suffixes;
unresolved records stay place-scoped. Overture's stable place ID remains the
location key. Review company identity and branch grouping because open map data
can contain duplicates or incomplete properties.

The deterministic score includes taxonomy match, matching business terms on
the company site, target country, website reachability, and Overture
confidence. The version and component values are stored with each score.
Classification by Gemini is disabled by default; when explicitly enabled it
can only down-rank an ambiguous match and is not treated as evidence. A lead is
qualified only when it reaches the configured score threshold and both the
discovery source and company website support the fit.

## Lifecycle and operations

The first startup refresh checks Overture's latest release. The scheduler polls
for release and provider retries every `LEAD_REFRESH_POLL_SECONDS` (default 5
minutes), with release checks gated by `LEAD_REFRESH_HOURS` (default 720 hours).
A separate worker resumes persisted website-verification jobs every
`LEAD_JOB_POLL_SECONDS` (default 30 seconds), so job backoff is actually
observed. Source discovery persists accounts and queues website checks without
waiting for those network requests to finish. The status endpoint reports the
current discovery phase; a first Overture release scan can take several minutes.
Jobs have bounded attempts, classified errors, and backoff for
retryable failures. Overture candidate, changelog, and Hunter checkpoints retry
independently; a failed changelog read is never recorded as complete. A new
data release uses Overture's changelog to flag removed or materially changed
place records for review while preserving existing rejections and completed or
uncertain outreach states. If the worker missed an intervening release, it
compares tracked place IDs against the latest Places snapshot before advancing
the changelog checkpoint.

## Large lead lists

The lead list API uses keyset pagination with a stable ordering and a bounded
`LIMIT + 1` query. It returns at most 100 records, a `has_more` flag, and an
opaque `next_cursor`; it does not run an exact total-count query or use a growing
SQL `OFFSET`. Composite indexes support fit/name ordering with and without a
brand filter. Search, contact filters, and sorting run in the database before
the page is returned.

The frontend keeps only the current page in memory and provides previous/next
navigation plus a page-size control. Changing a brand, search, contact filter,
sort order, or page size starts a fresh cursor chain. Search matches company
name or domain prefixes. Lead records are not copied into browser local storage;
existing saved lead fixtures are stripped from the previous browser-store key
when the app loads. API failures appear as errors instead of falling back to
preset companies.

Useful API routes:

- `GET /api/leads/status` — current source release, discovery phase, and refresh state.
- `POST /api/leads/refresh` — start a refresh in the background.
- `GET /api/leads?brand_id=jade&contact=email&search=diamond&sort=fit&limit=40` — first page.
- `GET /api/leads?brand_id=jade&sort=fit&limit=40&cursor=...` — next page when `has_more` is true.
- `GET /api/leads/{lead_id}` — account details with locations, contacts,
  evidence, score breakdown, and score history.
- `POST /api/leads/{lead_id}/review` — approve or reject with a reviewer name
  and optional note. Outreach approval is limited to qualified leads.
- `POST /api/leads/suppressions` — suppress an account domain or email from
  future contact and revoke any existing outreach approval.
- `GET /api/leads/draft?lead_id=...` and `POST /api/leads/send` — prepare and
  send the configured email after approval.

The backend checks the suppression list, current qualification, contact details,
and approval inside an atomic send claim. A changed fit score or evidence resets
approval and requires another human review. SMTP failures and database errors
after SMTP acceptance use `delivery_uncertain`; further sends stay locked until
someone checks the sender's Sent folder. Gmail delivery is a real external side
effect and requires `LEAD_FROM_EMAIL` plus `GMAIL_APP_PASSWORD`.

## Configuration

Provider settings for Hunter, Gemini, and Playwright:

| Variable | Default | Purpose |
| --- | --- | --- |
| `AURA_LEAD_REFRESH` | `true` | Start release-check and enrichment worker loops |
| `LEAD_REFRESH_HOURS` | `720` | Release-check interval |
| `LEAD_REFRESH_POLL_SECONDS` | `300` | Scheduler poll interval; minimum 60 seconds |
| `LEAD_JOB_POLL_SECONDS` | `30` | Enrichment job poll interval; minimum 5 seconds |
| `LEAD_MAX_JOBS_PER_RUN` | `300` | Maximum enrichment jobs per run |
| `LEAD_CRAWL_DELAY_SECONDS` | `0.35` | Delay between website jobs |
| `LEAD_HUNTER_RETRY_HOURS` | `6` | Delay before retrying a failed Hunter monthly discovery |
| `DUCKDB_EXTENSION_DIRECTORY` | `.aura/duckdb_extensions` | Writable cache directory for DuckDB HTTP extensions |
| `HUNTER_API_KEY` | empty | Enables optional Hunter discovery and capped email search |
| `LEAD_HUNTER_DISCOVER_ENABLED` | `true` | Disable Hunter discovery even with a key |
| `LEAD_HUNTER_MONTHLY_CREDIT_LIMIT` | `45` | Local ceiling for paid-credit Domain Search requests |
| `LEAD_PLAYWRIGHT_ENABLED` | `false` | Enable optional JavaScript rendering |
| `LEAD_GEMINI_ENABLED` | `false` | Enable ambiguous-case classifier |
| `LEAD_GEMINI_MODEL` | empty | Model name used by the optional classifier |

No Hunter, Gemini, or Gmail key is needed to discover and score leads from
Overture and public websites. Gemini sends website text to Google when enabled;
review the provider terms and data handling before turning it on.
