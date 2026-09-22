from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .config import (
    CHANGEDETECTION_API_KEY,
    CHANGEDETECTION_API_URL,
    WEBHOOK_TOKEN,
    load_competitors,
    load_watches,
)


WEBHOOK_PATH = "/api/competitors/webhooks/changedetection"
WATCH_TITLE_PREFIX = "JA Assure competitor intelligence ·"


def _fetch_backend(url: str) -> str:
    """Prefer plain HTTP when the page does not need JavaScript.

    Chrome CDP capacity is limited; routing static pages through html_requests
    keeps sockpuppetbrowser free for bot-protected / JS-heavy origins (G4S, Chubb).
    """
    hostname = (urllib.parse.urlsplit(url).hostname or "").lower()
    http_ok = (
        hostname.endswith("libertyinternational.com")
        or hostname.endswith("libertyspecialtymarkets.com")
        or hostname.endswith("income.com.sg")
        or hostname.endswith("marsh.com")
        or hostname.endswith("howdengroup.com")
        or hostname.endswith("parcelpro.com")
        or hostname.endswith("upscapital.com")
        or hostname.endswith("malca-amit.com")
        or hostname.endswith("malacamit.com")
        or hostname.endswith("brinkssingapore.com")
        or hostname.endswith("brinks.com")
        or hostname.endswith("angloeast.com.hk")
        or hostname.endswith("medicalprotection.org")
    )
    if http_ok:
        return "html_requests"
    return "html_webdriver"


def _is_g4s(url: str) -> bool:
    hostname = (urllib.parse.urlsplit(url).hostname or "").lower()
    return hostname == "g4s.com" or hostname.endswith(".g4s.com")


def _watch_fetch_options(url: str) -> dict[str, Any]:
    """Extra changedetection fields for origins that need a real browser wait."""
    if not _is_g4s(url):
        return {}
    # Radware returns HTTP 247 + a JS challenge. Ignore the interstitial status,
    # wait for client-side navigation, and reject snapshots that are still the
    # challenge page instead of product content.
    return {
        "ignore_status_codes": True,
        "webdriver_delay": 25,
        "headers": {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
        },
        # Fail the check (do not baseline) if Radware challenge markers remain.
        "text_should_not_be_present": [
            "kramericaindustries",
            "rbzns",
            "Access Denied",
        ],
    }


def _canonical_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url.strip())
    path = parsed.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, ""))


def _notification_url() -> str:
    # Changedetection runs in Docker while AURA owns the host API. The main
    # launcher overrides this with the configured API port when needed.
    host = os.getenv("INTEL_WEBHOOK_HOST", "host.docker.internal:8000").strip() or "host.docker.internal:8000"
    url = f"post://{host}{WEBHOOK_PATH}"
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
    active_competitors = {competitor.id: competitor for competitor in load_competitors() if competitor.monitor}
    watches = load_watches()
    watches_by_url: dict[str, list[Any]] = {}
    for watch in watches:
        watches_by_url.setdefault(_canonical_url(watch.url), []).append(watch)
    for watch_group in watches_by_url.values():
        watch = watch_group[0]
        competitor = active_competitors.get(watch.competitor_id)
        if competitor is None:
            raise ValueError(f"Watch {watch.id} references an inactive competitor")
        competitor_ids = [item.competitor_id for item in watch_group]
        if any(item not in active_competitors for item in competitor_ids):
            raise ValueError(f"Watch {watch.id} references an inactive competitor")
        notification_body = (
            '{"competitor_ids": ' + json.dumps(competitor_ids) + ', '
            '"watch_url": {{watch_url|tojson}}, '
            '"current_snapshot": {{current_snapshot|tojson}}, '
            '"diff": {{diff|tojson}}}'
        )
        payload = {
            "url": watch.url,
            "title": f"{WATCH_TITLE_PREFIX} {competitor.name} · {watch.id}",
            "fetch_backend": _fetch_backend(watch.url),
            "notification_urls": [_notification_url()],
            "notification_body": notification_body,
            "notification_format": "text",
            "time_between_check_use_default": False,
            "time_between_check": {"hours": watch.interval_hours, "minutes": 0, "seconds": 0},
            # G4S serves Radware HTTP 247 from this runtime even with headful
            # Chrome + stealth + long waits. Keep the watches visible but paused;
            # LinkedIn/YouTube feeds in config/feeds.json remain the live G4S signal.
            "paused": _is_g4s(watch.url),
            **_watch_fetch_options(watch.url),
        }
        existing_watch = existing_by_url.get(_canonical_url(watch.url))
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
                        "watch_id": watch.id,
                        "status": "updated" if existing_watch else "created",
                        "http_status": response.status,
                        "url": watch.url,
                    }
                )
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"failed to create watch for {watch.id}: HTTP {exc.code}") from exc

    return results
