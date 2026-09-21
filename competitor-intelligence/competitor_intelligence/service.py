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
            previous = self.store.latest_snapshot(competitor.id)
            summary = None
            event_id = None
            changed = previous is not None and meaningful_change(previous.content, current.content)
            if changed and previous is not None:
                summary = build_change_summary(previous.content, current.content)
                classification = classify_change(
                    competitor, previous.content, current.content, current.source
                )
                event = ChangeEvent(
                    id=new_id("event"),
                    competitor_id=competitor.id,
                    brand_id=competitor.brand_id,
                    country=competitor.countries[0] if competitor.countries else None,
                    source=current.source,
                    detected_at=utc_now(),
                    **classification,
                )
                self.store.add_event(event)
                event_id = event.id
            snapshot = new_snapshot(
                competitor.id,
                current.content,
                current.source,
                utc_now(),
                summary,
            )
            self.store.add_snapshot(snapshot)
            return ScanResult(competitor.id, "changed" if changed else "baseline", changed, summary, event_id)
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
        raw_content = payload.get("content") or payload.get("body") or payload.get("new_content")
        if not raw_content:
            raw_content = payload.get("diff") or payload.get("text")
        if not raw_content:
            raise ValueError("Webhook payload does not contain content")
        collected = CollectedContent(
            content=str(raw_content),
            source="changedetection",
            title=str(payload.get("title") or "") or None,
            url=url or competitor.url,
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
                    result = self.scan(
                        competitor.id,
                        CollectedContent(
                            content=f"{item.title}\n{item.content}\n{item.url}",
                            source=source,
                            title=item.title,
                            url=item.url,
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
        return [
            {
                "source": "website",
                "status": "ready",
                "detail": f"{len(self.competitors())} registered URLs",
            },
            {
                "source": "changedetection",
                "status": "webhook_ready",
                "detail": "POST /api/webhooks/changedetection",
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
