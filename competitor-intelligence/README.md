# JA Assure Competitor Intelligence

Standalone competitor monitoring module for Jade, DoctorShield, and Jaguar
Transit. It owns its configuration, SQLite database, HTTP API, and browser
dashboard. The 5001 changedetection UI is a source of snapshots; the main
Intelligence feed is served by this module on port 8787.

The collection pipeline is deterministic:

```text
configured URL / changedetection history or webhook / RSS feed
        -> normalized content
        -> hash and snapshot
        -> structured premium, new-link, or meaningful text diff
        -> deterministic change classification and optional Gemini analysis
        -> event and evidence in the dashboard
```

The module uses mature monitoring tools as optional collectors rather than
copying their source code:

- changedetection.io can POST page changes to `/api/webhooks/changedetection`.
- RSSHub feeds can be listed in `config/feeds.json`.
- SearXNG JSON search is available through `POST /api/search` when configured.
- YouTube public channel RSS feeds can be listed alongside RSSHub feeds.

The built-in website collector also works without any external service. It is a
useful baseline for a local demo and for sources that do not need JavaScript
rendering.

The Compose defaults keep browser checks conservative: one changedetection
worker, two isolated Chrome sessions, a larger shared memory area, a readiness
healthcheck, and a 60-second CDP keepalive. The browser URL disables HTTP/2 and
QUIC and uses headful Chrome because some publishers fail HTTP/2 navigation or
serve an anti-bot challenge to headless browsers. Liberty watches use the
plain HTTP collector because those pages do not require JavaScript.

## Run with the upstream tools

The optional `compose.yaml` runs this module next to the upstream projects; it
does not copy or vendor their source code:

```bash
docker compose up --build
SEARXNG_URL=http://searxng:8080 docker compose --profile discovery --profile social up --build
```

This exposes the intelligence dashboard on `8787`, changedetection.io on
`5001`, SearXNG on `8080`, and RSSHub on `1200`. Port `5001` avoids the macOS
AirPlay service commonly occupying host port `5000`. In changedetection.io, point a
watch webhook at:

```text
http://intelligence:8787/api/webhooks/changedetection
```

The module consumes RSSHub and YouTube public feeds through `config/feeds.json`,
and sends discovery queries to the SearXNG service URL. The worker scans the
website registry and polls configured feeds every 15 minutes by default. These
services are optional: the direct website collector and webhook endpoint still
work when only the intelligence container is running.

`./run.sh` loads the repository root `.env` for Compose interpolation. It passes
only `GEMINI_API_KEY` and `GEMINI_MODEL` to the intelligence container. Local
Python mode reads those two settings directly from the root `.env` when they
are not already in the process environment. The Gemini key is never sent to
the browser. Set `CHANGEDETECTION_API_KEY` in the shell or Compose environment
if the changedetection API requires a key; find it under changedetection
Settings → API.

The compose setup also enables changedetection.io's `Visual / Image screenshot
change detection` processor. The AURA-provisioned watchlist intentionally
remains `Webpage Text/HTML, JSON and PDF changes` because the intelligence
webhook needs text for deterministic classification. Use the visual processor
for a separate watch when you need before/after screenshot diffs; it requires
the configured Playwright browser backend.

## Connect changedetection to Intelligence

The source list is `config/watches.json`. It currently has 35 page watches
across 12 active competitor relationships. Product and pricing pages run every
6 hours, logistics and insights every 12 hours, news listings every 6 hours,
and the Parcel Pro homepage every 24 hours. Each page has its own baseline.

After both services start, run `python -m competitor_intelligence
provision-changedetection` with the changedetection API key to create or update
the configured watches and webhooks. The Intelligence page's **Sync 5001
changes** button imports existing changedetection history, including changes
that predate webhook setup. The collector worker also syncs on each polling
cycle. Only snapshots newer than the stored cursor are imported, so repeated
syncs do not create duplicate events. The first snapshot of each source is a
baseline; the next meaningful difference creates a feed event.

For local Python mode, `./run.sh --local` reads the API credential from the
running local changedetection container and uses history polling. For immediate
webhook delivery, run Intelligence through Compose so the `intelligence`
container hostname in the watch notification URL resolves. Existing
changedetection watches outside `config/watches.json` are preserved and do not
appear in the JA feed until explicitly mapped to a brand source.

For a source-specific direct check, use its Scan button in the Intelligence
watchlist. **Scan watchlist** checks all configured URLs, which can take several
minutes. A failed or blocked source reports an error; it does not erase the
previous baseline. Some publishers block automated requests or render news
links only in a browser, so source health should be reviewed before relying on
an empty feed.

G4S currently returns Radware's HTTP 247 bot-protection challenge from this
runtime. The collector identifies that challenge and refuses to store it as a
baseline. G4S watches therefore use the headful Chrome backend; if the
publisher continues to challenge the runtime, the watch remains an explicit
blocked source instead of producing false changes.

Income's medical indemnity premium table is parsed into risk category,
annual premium, discount, and effective date. A category price change produces
a high impact event with explicit before and after prices. News and insights
pages compare article URLs and titles. New articles are fetched and screened
for brand relevance before an event is created; Gemini is used for that screen
when configured, with a local keyword screen otherwise. Open an event to see
the captured diff and choose **Analyze with AI** for a Gemini summary, why it
matters, and a suggested next action. Gemini analysis is on demand and does
not rewrite the stored evidence.

## Run it

From this directory, with Python 3.11 or newer:

```bash
python -m competitor_intelligence
```

Open <http://127.0.0.1:8787>. The first run creates `data/intelligence.db` and
loads the editable registry from `config/competitors.json`.

Run one scan without starting the server:

```bash
python -m competitor_intelligence scan-all
```

Run the persistent collector worker:

```bash
python -m competitor_intelligence worker
```

Provision the active competitor watchlist in changedetection.io. The API key is
available under changedetection.io Settings → API; it is not stored in this
repository:

```bash
CHANGEDETECTION_API_URL=http://localhost:5001 \
CHANGEDETECTION_API_KEY=replace-me \
python -m competitor_intelligence provision-changedetection
```

Configuration can be changed with environment variables:

```text
INTEL_HOST=127.0.0.1
INTEL_PORT=8787
INTEL_DB_PATH=data/intelligence.db
INTEL_COMPETITORS=config/competitors.json
INTEL_FEEDS=config/feeds.json
INTEL_WATCHES=config/watches.json
INTEL_REQUEST_TIMEOUT=20
INTEL_WEBHOOK_TOKEN=replace-with-a-long-random-value
CHANGEDETECTION_API_URL=http://localhost:5001
CHANGEDETECTION_API_KEY=replace-with-changedetection-api-key
GEMINI_API_KEY=replace-with-personal-gemini-key
GEMINI_MODEL=gemini-3.6-flash
SEARXNG_URL=http://localhost:8080
DISABLED_PROCESSORS=
```

The registry contains twelve active monitor relationships across Jade,
DoctorShield, and Jaguar Transit, plus a non-scanned Liberty relationship that
records Jaguar's partner/market-overlap context. Repeated organizations such as
Howden, Chubb, and Liberty have separate brand relationships rather than being
flattened into a boolean `competitor` flag.
The service never sends credentials to monitored sites.

## Registry model

Each entry in `config/competitors.json` is a monitor relationship, not a unique
company record. `organization_id` groups a company across brands, while
`relationship` captures the role it plays for that JA brand:

```text
organization_id + name + website
        |
        +-- brand_id + relationship + market + product_category + priority
```

Supported relationship values are `DIRECT_COMPETITOR`, `INDIRECT_COMPETITOR`,
`PARTNER`, `UNDERWRITER`, `DISTRIBUTOR`, `SECURE_LOGISTICS_COMPETITOR`, and
`ADJACENT`. Set `monitor` to `false` when a relationship should remain visible
as strategic context without creating a changedetection watch or participating
in the active scan-all operation.

## changedetection.io webhook

Configure a changedetection.io watch to POST JSON to:

```text
http://<this-machine>:8787/api/webhooks/changedetection
```

The webhook accepts `watch_url`, `url`, `title`, `current_snapshot`, `body`,
`content`, `diff`, and optional `competitor_id` fields. A URL is matched
against the registry when an ID is not supplied. Configure changedetection to
send the full current snapshot, not only the diff, for example with a JSON
notification body:

```json
{
  "competitor_id": "jade-howden",
  "watch_url": "{{watch_url}}",
  "current_snapshot": "{{current_snapshot}}",
  "diff": "{{diff}}"
}
```

Every accepted webhook is stored in its own source stream and becomes an event
only when the content is meaningfully different from the previous snapshot in
that same stream.

Set `INTEL_WEBHOOK_TOKEN` in production. When configured, the provisioning
command embeds the same value as an `X-Webhook-Token` header in each
changedetection notification URL. Manually configured watches must send the
same header.

## Design boundaries

- No AURA API, frontend route, or shared contract is required.
- No crawler framework is vendored.
- No LLM is required for collection or change detection. Gemini is used for
  optional relevance screening and on-demand evidence analysis.
- Snapshot history and event evidence live in SQLite so the module is portable.
- External collectors are best-effort and report errors in source health; one
  failing source does not stop other scans.
