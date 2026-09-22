from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from .analysis import build_change_summary, classify_change, meaningful_change, new_snapshot
from .collectors import CollectedContent, collect_rss, collect_website, search_searxng
from .config import SEARXNG_URL, load_competitors, load_feeds
from .models import ChangeEvent, Competitor, Snapshot, utc_now
from .store import Store, new_id


@dataclass(slots=True)
class ScanResult:
    competitor_id: str
    status: str
    changed: bool
    summary: str | None = None
    event_id: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "competitor_id": self.competitor_id,
            "status": self.status,
            "changed": self.changed,
            "summary": self.summary,
            "event_id": self.event_id,
            "error": self.error,
        }


def _source_key(collected: CollectedContent) -> str:
    identity = collected.source_key or collected.url or collected.source
    return f"{collected.source}:{identity}"


class IntelligenceService:
    def __init__(self, store: Store):
        self.store = store
        self.sync_registry()

    def sync_registry(self) -> None:
        for competitor in load_competitors():
            self.store.upsert_competitor(competitor)

    def competitors(self) -> list[Competitor]:
        return self.store.list_competitors()

    def scan(self, competitor_id: str, collected: CollectedContent | None = None) -> ScanResult:
        competitor = self.store.get_competitor(competitor_id)
        if competitor is None:
            return ScanResult(competitor_id, "not_found", False, error="Competitor is not registered")
        try:
            current = collected or collect_website(competitor.url)
            if collected is None:
                current.source_key = competitor.url
                current.market = competitor.countries[0] if competitor.countries else None
            if current.source in {"website", "changedetection"} and current.url:
                current.url = Store.canonical_url(current.url)
                source_identity = current.source_key or current.url
                if source_identity == current.url or current.source == "website":
                    current.source_key = current.url
                elif source_identity.endswith("#diff"):
                    current.source_key = f"{current.url}#diff"
                elif current.source == "changedetection":
                    current.source_key = Store.canonical_url(source_identity)
            source_key = _source_key(current)
            snapshot = new_snapshot(
                competitor.id,
                current.content,
                current.source,
                source_key,
                current.url or competitor.url,
                current.market or (competitor.countries[0] if competitor.countries else None),
                utc_now(),
                None,
            )

            def build_event(previous: Snapshot | None) -> ChangeEvent | None:
                if previous is None or not meaningful_change(previous.content, current.content):
                    return None
                snapshot.change_summary = build_change_summary(previous.content, current.content)
                classification = classify_change(
                    competitor, previous.content, current.content, current.source
                )
                return ChangeEvent(
                    id=new_id("event"),
                    competitor_id=competitor.id,
                    brand_id=competitor.brand_id,
                    country=competitor.countries[0] if competitor.countries else None,
                    source=current.source,
                    source_url=current.url or competitor.url,
                    detected_at=utc_now(),
                    **classification,
                )

            previous, changed, event_id = self.store.record_scan(snapshot, build_event)
            status = "baseline" if previous is None else ("changed" if changed else "unchanged")
            return ScanResult(competitor.id, status, changed, snapshot.change_summary, event_id)
        except Exception as exc:  # collectors are isolated; one bad site must not stop a run
            return ScanResult(competitor.id, "error", False, error=str(exc))

    def scan_all(self) -> list[ScanResult]:
        return [self.scan(competitor.id) for competitor in self.competitors()]

    def ingest_changedetection(self, payload: dict[str, Any]) -> ScanResult:
        url = str(payload.get("watch_url") or payload.get("url") or "").strip()
        competitor_id = str(payload.get("competitor_id") or "").strip()
        competitor = self.store.get_competitor(competitor_id) if competitor_id else None
        if competitor is None and url:
            competitor = self.store.find_competitor_by_url(url)
        if competitor is None:
            raise ValueError("Webhook must include competitor_id or a registered watch_url")
        raw_content = (
            payload.get("current_snapshot")
            or payload.get("current_content")
            or payload.get("content")
            or payload.get("body")
            or payload.get("new_content")
        )
        source_key = Store.canonical_url(url or competitor.url)
        if not raw_content:
            raw_content = payload.get("diff") or payload.get("text")
            source_key = f"{source_key}#diff"
        if not raw_content:
            raise ValueError("Webhook payload does not contain content")
        collected = CollectedContent(
            content=str(raw_content),
            source="changedetection",
            title=str(payload.get("title") or "") or None,
            url=url or competitor.url,
            source_key=source_key,
            market=competitor.countries[0] if competitor.countries else None,
        )
        return self.scan(competitor.id, collected)

    def poll_feeds(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for feed in load_feeds():
            url = str(feed["url"])
            source = str(feed.get("source", "rss"))
            competitor_id = str(feed.get("competitor_id", ""))
            competitor = self.store.get_competitor(competitor_id) if competitor_id else None
            if competitor is None:
                results.append({"url": url, "status": "error", "error": "Unknown competitor_id"})
                continue
            try:
                items = collect_rss(url, source)
                created = 0
                for item in items[:20]:
                    item_identity = Store.canonical_url(item.url) if item.url != url else item.title
                    result = self.scan(
                        competitor.id,
                        CollectedContent(
                            content=f"{item.title}\n{item.content}\n{item.url}",
                            source=source,
                            title=item.title,
                            url=Store.canonical_url(item.url),
                            source_key=f"{Store.canonical_url(url)}#{item_identity}",
                            market=competitor.countries[0] if competitor.countries else None,
                        ),
                    )
                    created += int(result.changed)
                results.append({"url": url, "status": "ok", "items": len(items), "events": created})
            except Exception as exc:
                results.append({"url": url, "status": "error", "error": str(exc)})
        return results

    def search(self, query: str) -> list[dict[str, str]]:
        return [
            {"title": item.title, "content": item.content, "url": item.url}
            for item in search_searxng(query)
        ]

    def events(self, filters: dict[str, str] | None = None) -> list[dict[str, Any]]:
        competitor_names = {item.id: item.name for item in self.competitors()}
        events = []
        for event in self.store.list_events(filters):
            payload = event.to_dict()
            payload["competitor_name"] = competitor_names.get(event.competitor_id, event.competitor_id)
            events.append(payload)
        return events

    def source_health(self) -> list[dict[str, str]]:
        configured_feeds = len(load_feeds())
        source_counts = self.store.source_competitor_counts()
        website_scans = source_counts.get("website", 0)
        webhook_scans = source_counts.get("changedetection", 0)
        return [
            {
                "source": "website",
                "status": "receiving" if website_scans else "ready",
                "detail": f"{website_scans}/{len(self.competitors())} URLs scanned",
            },
            {
                "source": "changedetection",
                "status": "receiving" if webhook_scans else "waiting",
                "detail": f"{webhook_scans} webhook source(s) received",
            },
            {
                "source": "rsshub",
                "status": "configured" if configured_feeds else "not_configured",
                "detail": f"{configured_feeds} feed(s) in config/feeds.json",
            },
            {
                "source": "searxng",
                "status": "configured" if SEARXNG_URL else "not_configured",
                "detail": "Search adapter available" if SEARXNG_URL else "Set SEARXNG_URL to enable",
            },
        ]

    def monitor_status(self) -> list[dict[str, Any]]:
        return self.store.monitor_status()
