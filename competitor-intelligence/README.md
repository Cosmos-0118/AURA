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
- SearXNG JSON search can be polled with `python -m competitor_intelligence poll-search`.
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

The module consumes RSSHub and YouTube public feeds through `config/feeds.json`
and sends discovery queries to the SearXNG service URL. These services are
optional: the direct website collector and webhook endpoint still work when
only the intelligence container is running.

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

Configuration can be changed with environment variables:

```text
INTEL_HOST=127.0.0.1
INTEL_PORT=8787
INTEL_DB_PATH=data/intelligence.db
INTEL_COMPETITORS=config/competitors.json
INTEL_FEEDS=config/feeds.json
INTEL_REQUEST_TIMEOUT=20
INTEL_WEBHOOK_TOKEN=replace-with-a-long-random-value
SEARXNG_URL=http://localhost:8080
```

The initial URL registry is deliberately editable. Replace the example URLs
with the exact public pricing, product, and market pages JA wants to monitor.
The service never sends credentials to monitored sites.

## changedetection.io webhook

Configure a changedetection.io watch to POST JSON to:

```text
http://<this-machine>:8787/api/webhooks/changedetection
```

The webhook accepts `watch_url`, `url`, `title`, `body`, `content`, `diff`, and
optional `competitor_id` fields. A URL is matched against the registry when an
ID is not supplied. Every accepted webhook is stored as a snapshot and becomes
an event only when the content is meaningfully different from the previous
snapshot.

Set `INTEL_WEBHOOK_TOKEN` in production. When configured, changedetection.io
must send the same value in the `X-Webhook-Token` header.

## Design boundaries

- No AURA API, frontend route, or shared contract is required.
- No crawler framework is vendored.
- No LLM is required for collection or change detection. An AI analyst can be
  added later behind the stored event/evidence boundary.
- Snapshot history and event evidence live in SQLite so the module is portable.
- External collectors are best-effort and report errors in source health; one
  failing source does not stop other scans.
