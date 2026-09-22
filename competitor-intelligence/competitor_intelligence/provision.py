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
WATCH_TITLE_PREFIX = "JA Assure competitor intelligence ·"
LEGACY_WATCH_URLS = frozenset(
    {
        "https://www.chubb.com/sg-en/business/fine-art-valuable-goods-insurance.html",
        "https://www.msig.com.sg/commercial/professional-indemnity",
        "https://www.aig.sg/home/solutions/business-products-and-services/marine/marine-cargo",
    }
)


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


def _is_aura_watch(watch: dict[str, Any]) -> bool:
    title = str(watch.get("title") or "")
    if title.startswith(WATCH_TITLE_PREFIX):
        return True
    notification_urls = watch.get("notification_urls") or []
    if isinstance(notification_urls, str):
        notification_urls = [notification_urls]
    return any(
        "intelligence:8787/api/webhooks/changedetection" in str(url)
        for url in notification_urls
    )


def _legacy_watch_is_aura_owned(
    watch: dict[str, Any], endpoint: str, headers: dict[str, str]
) -> bool:
    if _is_aura_watch(watch):
        return True
    watch_id = watch.get("uuid")
    if not watch_id:
        return False
    try:
        request = urllib.request.Request(f"{endpoint}/{watch_id}", headers=headers)
        with urllib.request.urlopen(request, timeout=20) as response:
            details = json.loads(response.read().decode("utf-8"))
    except (urllib.error.HTTPError, urllib.error.URLError, json.JSONDecodeError, UnicodeDecodeError):
        return False
    return isinstance(details, dict) and _is_aura_watch({**watch, **details})


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
    active_competitors = [competitor for competitor in load_competitors() if competitor.monitor]
    active_urls = {_canonical_url(competitor.url) for competitor in active_competitors}
    notification_body = (
        '{"competitor_id": "COMPETITOR_ID", '
        '"watch_url": {{watch_url|tojson}}, '
        '"current_snapshot": {{current_snapshot|tojson}}, '
        '"diff": {{diff|tojson}}}'
    )
    for competitor in active_competitors:
        payload = {
            "url": competitor.url,
            "title": f"{WATCH_TITLE_PREFIX} {competitor.name} · {competitor.niche}",
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

    for watch_url, existing_watch in existing_by_url.items():
        if (
            watch_url in active_urls
            or watch_url not in LEGACY_WATCH_URLS
            or not _legacy_watch_is_aura_owned(existing_watch, endpoint, headers)
        ):
            continue
        watch_id = existing_watch.get("uuid")
        if not watch_id:
            continue
        target = f"{endpoint}/{watch_id}"
        pause_request = urllib.request.Request(
            target,
            data=json.dumps({"paused": True}).encode("utf-8"),
            headers={**headers, "Content-Type": "application/json"},
            method="PUT",
        )
        try:
            with urllib.request.urlopen(pause_request, timeout=20) as response:
                results.append(
                    {
                        "watch_id": watch_id,
                        "status": "paused",
                        "http_status": response.status,
                        "url": watch_url,
                    }
                )
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"failed to pause legacy watch {watch_id}: HTTP {exc.code}") from exc
    return results
