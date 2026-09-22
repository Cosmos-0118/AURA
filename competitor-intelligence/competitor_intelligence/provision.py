from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .config import (
    CHANGEDETECTION_API_KEY,
    CHANGEDETECTION_API_URL,
    WEBHOOK_TOKEN,
    load_competitors,
)


WEBHOOK_PATH = "/api/webhooks/changedetection"


def _canonical_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url.strip())
    path = parsed.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, ""))


def _notification_url() -> str:
    url = f"post://intelligence:8787{WEBHOOK_PATH}"
    if WEBHOOK_TOKEN:
        token = urllib.parse.quote(WEBHOOK_TOKEN, safe="")
        url += f"?+X-Webhook-Token={token}"
    return url


def provision_changedetection() -> list[dict[str, Any]]:
    if not CHANGEDETECTION_API_KEY:
        raise ValueError("CHANGEDETECTION_API_KEY is required to provision watches")

    endpoint = f"{CHANGEDETECTION_API_URL}/api/v1/watch"
    headers = {"x-api-key": CHANGEDETECTION_API_KEY}
    request = urllib.request.Request(endpoint, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            existing = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"changedetection watch listing failed with HTTP {exc.code}") from exc

    existing_by_url: dict[str, dict[str, Any]] = {}
    watch_items = (
        existing.items()
        if isinstance(existing, dict)
        else (
            ((item.get("uuid", ""), item) for item in existing if isinstance(item, dict))
            if isinstance(existing, list)
            else ()
        )
    )
    for watch_id, item in watch_items:
        if not isinstance(item, dict) or not item.get("url"):
            continue
        existing_by_url[_canonical_url(item["url"])] = {"uuid": watch_id, **item}
    results: list[dict[str, Any]] = []
    notification_body = (
        '{"competitor_id": "COMPETITOR_ID", '
        '"watch_url": {{watch_url|tojson}}, '
        '"current_snapshot": {{current_snapshot|tojson}}, '
        '"diff": {{diff|tojson}}}'
    )
    for competitor in load_competitors():
        payload = {
            "url": competitor.url,
            "title": f"{competitor.name} · {competitor.niche}",
            "fetch_backend": "html_webdriver",
            "notification_urls": [_notification_url()],
            "notification_body": notification_body.replace("COMPETITOR_ID", competitor.id),
            "notification_format": "text",
            "time_between_check_use_default": True,
            "paused": False,
        }
        existing_watch = existing_by_url.get(_canonical_url(competitor.url))
        method = "PUT" if existing_watch else "POST"
        target = f"{endpoint}/{existing_watch['uuid']}" if existing_watch else endpoint
        create_request = urllib.request.Request(
            target,
            data=json.dumps(payload).encode("utf-8"),
            headers={**headers, "Content-Type": "application/json"},
            method=method,
        )
        try:
            with urllib.request.urlopen(create_request, timeout=20) as response:
                results.append(
                    {
                        "competitor_id": competitor.id,
                        "status": "updated" if existing_watch else "created",
                        "http_status": response.status,
                        "url": competitor.url,
                    }
                )
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"failed to create watch for {competitor.id}: HTTP {exc.code}") from exc
    return results
