# JA Assure Competitor Intelligence

Standalone competitor monitoring module for Jade, DoctorShield, and Jaguar
Transit. It is intentionally independent from the AURA dashboard: it owns its
configuration, SQLite database, HTTP API, and browser dashboard.

The collection pipeline is deterministic:

```text
configured URL / changedetection webhook / RSS feed
        -> normalized content
        -> hash and snapshot
        -> meaningful diff
        -> deterministic change classification
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

Provision the three product watches in changedetection.io. The API key is
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
INTEL_REQUEST_TIMEOUT=20
INTEL_WEBHOOK_TOKEN=replace-with-a-long-random-value
CHANGEDETECTION_API_URL=http://localhost:5001
CHANGEDETECTION_API_KEY=replace-with-changedetection-api-key
SEARXNG_URL=http://localhost:8080
```

The initial URL registry contains product-specific Singapore pages for Chubb
Fine Art and Valuable Goods, MSIG Professional Indemnity, and AIG Marine
Cargo. Replace these with the exact public pricing, product, and market pages
JA wants to monitor.
The service never sends credentials to monitored sites.

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
  "competitor_id": "jade-competitor-1",
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
- No LLM is required for collection or change detection. An AI analyst can be
  added later behind the stored event/evidence boundary.
- Snapshot history and event evidence live in SQLite so the module is portable.
- External collectors are best-effort and report errors in source health; one
  failing source does not stop other scans.
