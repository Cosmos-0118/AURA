from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import unified_diff
import json
import threading
import time
import urllib.request
from typing import Any

from .ai import analyze_diff, article_relevant
from .analysis import (build_change_summary, classify_change, confidence_for_change,
                       content_hash, meaningful_change, new_snapshot)
from .collectors import (CollectedContent, collect_rss, collect_watch, collect_website,
                         extract_income_pricing_text, search_searxng)
from .config import (CHANGEDETECTION_API_KEY, CHANGEDETECTION_API_URL, COMPETITORS_PATH,
                     REQUEST_TIMEOUT, SEARXNG_URL, load_competitors, load_feeds, load_watches)
from .models import ChangeEvent, Competitor, Snapshot, WatchSource, utc_now
from .store import Store, new_id


LEGACY_REGISTRY_IDS = frozenset(
    {
        "jade-competitor-1",
        "doctorshield-competitor-1",
        "jaguar-competitor-1",
    }
)
FEED_EVENT_SOURCES = frozenset({"rss", "rsshub", "linkedin", "youtube", "news"})


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
        self._analysis_lock = threading.Lock()
        self._analysis_calls: list[float] = []
        self._analysis_cache: dict[str, dict[str, str]] = {}
        self._analysis_inflight: set[str] = set()
        self._registry_loaded = False
        self._registry_signature: tuple[int, int] | None = None
        # When True, first-seen RSS/RSSHub/YouTube items become feed events.
        # First poll of each feed seeds baselines silently so the dashboard is
        # not flooded with historical posts.
        self._emit_new_feed_items = False
        self.sync_registry()

    def sync_registry(self) -> None:
        try:
            registry_stat = COMPETITORS_PATH.stat()
            registry_signature = (registry_stat.st_mtime_ns, registry_stat.st_size)
        except FileNotFoundError:
            registry_signature = None
        if self._registry_loaded and registry_signature == self._registry_signature:
            return

        registry = load_competitors(COMPETITORS_PATH)
        for competitor in registry:
            self.store.upsert_competitor(competitor, registry_managed=True)
        if registry or COMPETITORS_PATH.exists():
            self.store.retire_missing_competitors(
                {competitor.id for competitor in registry}, LEGACY_REGISTRY_IDS
            )
        self._registry_signature = registry_signature
        self._registry_loaded = True

    def competitors(self) -> list[Competitor]:
        self.sync_registry()
        return self.store.list_competitors()

    def active_competitors(self) -> list[Competitor]:
        self.sync_registry()
        return self.store.list_competitors(active_only=True)

    def scan(self, competitor_id: str, collected: CollectedContent | None = None) -> ScanResult:
        self.sync_registry()
        competitor = self.store.get_competitor(competitor_id)
        if competitor is None:
            return ScanResult(competitor_id, "not_found", False, error="Competitor is not registered")
        try:
            current = collected or collect_website(competitor.url)
            watch = next((item for item in load_watches() if item.competitor_id == competitor.id
                          and Store.canonical_url(item.url) == Store.canonical_url(current.url or competitor.url)), None)
            if watch and watch.kind == "pricing" and current.source == "changedetection":
                current.content = extract_income_pricing_text(current.content)
                current.source_key = f"{watch.url}#pricing"
            if collected is None:
                current.source_key = competitor.url
                current.market = competitor.countries[0] if competitor.countries else None
            if current.source in {"website", "changedetection"} and current.url:
                current.url = Store.canonical_url(current.url)
                source_identity = current.source_key or current.url
                if source_identity == current.url:
                    current.source_key = current.url
                elif current.source == "website" and source_identity.endswith(("#pricing", "#links")):
                    current.source_key = f"{current.url}#{source_identity.rsplit('#', 1)[1]}"
                elif current.source == "website":
                    current.source_key = current.url
                elif source_identity.endswith("#diff"):
                    current.source_key = f"{current.url}#diff"
                elif current.source == "changedetection":
                    current.source_key = (f"{current.url}#pricing" if source_identity.endswith("#pricing")
                                          else Store.canonical_url(source_identity))
            source_key = _source_key(current)
            snapshot = new_snapshot(
                competitor.id,
                current.content,
                current.source,
                source_key,
                current.url or competitor.url,
                current.market or (competitor.countries[0] if competitor.countries else None),
                current.observed_at or utc_now(),
                None,
            )

            def build_event(previous: Snapshot | None) -> ChangeEvent | None:
                if previous is None:
                    if (
                        self._emit_new_feed_items
                        and current.source in FEED_EVENT_SOURCES
                    ):
                        classification = classify_change(
                            competitor, "", current.content, current.source
                        )
                        classification["summary"] = (
                            f"New public post from {competitor.name}"
                            + (f": {current.title}" if current.title else ".")
                        )
                        if current.title:
                            classification["current_value"] = current.title
                        snapshot.change_summary = str(classification["summary"])
                        return ChangeEvent(
                            id=new_id("event"),
                            competitor_id=competitor.id,
                            brand_id=competitor.brand_id,
                            country=competitor.countries[0] if competitor.countries else None,
                            source=current.source,
                            source_url=current.url or competitor.url,
                            detected_at=current.observed_at or utc_now(),
                            **classification,
                        )
                    return None
                if watch and watch.kind == "pricing" and (current.source == "website" or current.source_key.endswith("#pricing")):
                    if previous.content == current.content:
                        return None
                    classification = self._price_change(
                        competitor, previous.content, current.content, current.source
                    )
                elif watch and watch.kind in {"news", "insights"}:
                    classification = self._article_change(
                        competitor, previous.content, current.content, current.source
                    )
                    if classification is None:
                        return None
                else:
                    if not meaningful_change(previous.content, current.content):
                        return None
                    classification = classify_change(
                        competitor, previous.content, current.content, current.source
                    )
                snapshot.change_summary = build_change_summary(previous.content, current.content)
                if watch and watch.kind in {"pricing", "news", "insights"}:
                    snapshot.change_summary = str(classification["summary"])
                return ChangeEvent(
                    id=new_id("event"),
                    competitor_id=competitor.id,
                    brand_id=competitor.brand_id,
                    country=competitor.countries[0] if competitor.countries else None,
                    source=current.source,
                    source_url=current.url or competitor.url,
                    detected_at=current.observed_at or utc_now(),
                    **classification,
                )

            previous, changed, event_id = self.store.record_scan(snapshot, build_event)
            status = "baseline" if previous is None else ("changed" if changed else "unchanged")
            return ScanResult(competitor.id, status, changed, snapshot.change_summary, event_id)
        except Exception as exc:  # collectors are isolated; one bad site must not stop a run
            return ScanResult(competitor.id, "error", False, error=str(exc))

    def scan_all(self) -> list[ScanResult]:
        watches = load_watches()
        return [self.scan_watch(watch) for watch in watches] if watches else [
            self.scan(competitor.id) for competitor in self.active_competitors()
        ]

    def scan_watch(self, watch: WatchSource) -> ScanResult:
        try:
            current = collect_watch(watch.url, watch.kind)
        except Exception as exc:
            return ScanResult(watch.competitor_id, "error", False, error=f"{watch.url}: {exc}")
        suffix = "#pricing" if watch.kind == "pricing" else "#links" if watch.kind in {"news", "insights"} else ""
        current.source_key = f"{watch.url}{suffix}"
        return self.scan(watch.competitor_id, current)

    def due_watches(self) -> list[WatchSource]:
        now = datetime.now(timezone.utc)
        due = []
        for watch in load_watches():
            snapshot = self.store.latest_snapshot(watch.competitor_id, self._watch_source_key(watch))
            if snapshot is None or (now - datetime.fromisoformat(snapshot.scraped_at)).total_seconds() >= watch.interval_hours * 3600:
                due.append(watch)
        return due

    @staticmethod
    def _price_change(
        competitor: Competitor,
        old: str,
        new: str,
        source: str = "website",
    ) -> dict[str, object]:
        before, after = json.loads(old), json.loads(new)
        old_prices, new_prices = before.get("premiums", {}), after.get("premiums", {})
        changed = [(category, old_prices.get(category), new_prices.get(category))
                   for category in sorted(set(old_prices) | set(new_prices))
                   if old_prices.get(category) != new_prices.get(category)]
        if changed:
            details = [f"{category}: {previous or 'not listed'} → {current or 'not listed'}"
                       for category, previous, current in changed]
            summary = f"{competitor.name}: annual premiums changed for {len(changed)} risk categor{'y' if len(changed) == 1 else 'ies'}: {'; '.join(details)}."
            previous_value = "; ".join(f"{category}: {previous or 'not listed'}" for category, previous, _ in changed)
            current_value = "; ".join(f"{category}: {current or 'not listed'}" for category, _, current in changed)
        else:
            summary = f"{competitor.name}: premium discount or effective date changed."
            previous_value, current_value = before.get("discount"), after.get("discount")
        return {"change_type": "price_change", "impact": "high", "summary": summary,
                "previous_value": previous_value, "current_value": current_value,
                "why_it_matters": f"Published medical indemnity pricing affects {competitor.brand_id} comparisons.",
                "recommended_action": "Review the published rate and date with the DoctorShield owner before responding.",
                "evidence": json.dumps({"before": before, "after": after}, ensure_ascii=False)[:3000],
                "confidence": confidence_for_change(old, new, source, "price_change")}

    @staticmethod
    def _article_change(
        competitor: Competitor,
        old: str,
        new: str,
        source: str = "news",
    ) -> dict[str, object] | None:
        old_urls = {line.split("\t", 1)[0] for line in old.splitlines()}
        additions = [line.split("\t", 1) for line in new.splitlines()
                     if "\t" in line and line.split("\t", 1)[0] not in old_urls]
        relevant = []
        for url, title in additions:
            article = collect_website(url).content
            if article_relevant(competitor.brand_id, title, article):
                relevant.append((url, title, article[:500]))
        if not relevant:
            return None
        url, title, excerpt = relevant[0]
        confidence = confidence_for_change(old, new, source, "article")
        # Multiple independently relevant additions strengthen the evidence,
        # but never allow the count alone to create false certainty.
        confidence = min(0.98, round(confidence + min(0.06, 0.02 * (len(relevant) - 1)), 2))
        return {"change_type": "article", "impact": "medium",
                "summary": f"New relevant article from {competitor.name}: {title}",
                "previous_value": None, "current_value": f"{len(relevant)} new relevant article(s)",
                "why_it_matters": f"New public content may affect {competitor.brand_id} positioning.",
                "recommended_action": "Read the article and compare its claims with the JA brand's current messaging.",
                "evidence": f"{url}\n{excerpt}", "confidence": confidence}

    def watch_status(self) -> list[dict[str, Any]]:
        rows = []
        for watch in load_watches():
            snapshot = self.store.latest_snapshot(watch.competitor_id, self._watch_source_key(watch))
            rows.append({**watch.to_dict(), "last_checked": snapshot.scraped_at if snapshot else None})
        return rows

    @staticmethod
    def _watch_source_key(watch: WatchSource) -> str:
        suffix = "#pricing" if watch.kind == "pricing" else "#links" if watch.kind in {"news", "insights"} else ""
        return f"website:{Store.canonical_url(watch.url)}{suffix}"

    def watches(self) -> list[WatchSource]:
        return load_watches()

    def sync_changedetection(self) -> dict[str, Any]:
        endpoint = f"{CHANGEDETECTION_API_URL}/api/v1/watch"
        headers = {"x-api-key": CHANGEDETECTION_API_KEY} if CHANGEDETECTION_API_KEY else {}
        def read(url: str) -> bytes:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=REQUEST_TIMEOUT) as response:
                return response.read()
        remote = json.loads(read(endpoint))
        entries = remote.items() if isinstance(remote, dict) else ((item.get("uuid"), item) for item in remote)
        configured: dict[str, list[WatchSource]] = {}
        for watch in load_watches():
            configured.setdefault(Store.canonical_url(watch.url), []).append(watch)
        imported = 0
        errors = []
        for watch_id, item in entries:
            if not watch_id or not isinstance(item, dict):
                continue
            matches = configured.get(Store.canonical_url(str(item.get("url") or "")), [])
            if not matches:
                continue
            try:
                history = json.loads(read(f"{endpoint}/{watch_id}/history"))
                versions = sorted(history.keys() if isinstance(history, dict) else history, key=lambda v: float(v))
                for watch in matches:
                    cursor_key = f"changedetection:{watch_id}:{watch.competitor_id}"
                    cursor = self.store.get_cursor(cursor_key)
                    if cursor is None:
                        local_key = f"changedetection:{Store.canonical_url(watch.url)}"
                        if watch.kind == "pricing":
                            local_key += "#pricing"
                        latest_local = self.store.latest_snapshot(watch.competitor_id, local_key)
                        if latest_local is not None:
                            matched_version = None
                            for version in reversed(versions):
                                content = read(f"{endpoint}/{watch_id}/history/{version}").decode("utf-8", errors="replace")
                                if watch.kind == "pricing":
                                    content = extract_income_pricing_text(content)
                                if content_hash(content) == latest_local.content_hash:
                                    matched_version = str(version)
                                    break
                            if matched_version is None:
                                self.store.set_cursor(cursor_key, str(versions[-1]))
                                continue
                            cursor = matched_version
                    for version in versions:
                        if cursor is not None and float(version) <= float(cursor):
                            continue
                        content = read(f"{endpoint}/{watch_id}/history/{version}").decode("utf-8", errors="replace")
                        result = self.scan(watch.competitor_id, CollectedContent(
                            content, "changedetection", url=watch.url, source_key=watch.url,
                            observed_at=datetime.fromtimestamp(float(version), timezone.utc).isoformat()))
                        if result.status == "error":
                            raise RuntimeError(result.error or "Could not import snapshot")
                        self.store.set_cursor(cursor_key, str(version))
                        imported += 1
            except Exception as exc:
                errors.append(f"{item.get('url', watch_id)}: {exc}")
        return {"imported": imported, "errors": errors, "matched_watches": len(configured)}

    def event_diff(self, event_id: str) -> dict[str, Any] | None:
        pair = self.store.event_evidence_pair(event_id)
        if pair is None:
            return None
        event, before, after = pair
        diff = "\n".join(unified_diff(before.splitlines(), after.splitlines(),
                                       fromfile="before", tofile="after", lineterm=""))
        return {"event_id": event_id, "source_url": event.source_url, "before": before[:12000],
                "after": after[:12000], "diff": diff}

    def analyze_event(self, event_id: str) -> dict[str, str] | None:
        evidence = self.event_diff(event_id)
        if evidence is None:
            return None
        pair = self.store.event_evidence_pair(event_id)
        assert pair is not None
        event = pair[0]
        competitor = self.store.get_competitor(event.competitor_id)
        with self._analysis_lock:
            if event_id in self._analysis_cache:
                return self._analysis_cache[event_id]
            now = time.monotonic()
            self._analysis_calls = [stamp for stamp in self._analysis_calls if now - stamp < 3600]
            if len(self._analysis_calls) >= 30 or event_id in self._analysis_inflight:
                raise PermissionError("AI analysis is busy or has reached its hourly limit")
            self._analysis_calls.append(now)
            self._analysis_inflight.add(event_id)
        try:
            result = analyze_diff(competitor.name if competitor else event.competitor_id,
                                  event.brand_id, event.source_url or "", evidence["diff"])
        except Exception:
            with self._analysis_lock:
                self._analysis_calls.remove(now)
            raise
        else:
            with self._analysis_lock:
                self._analysis_cache[event_id] = result
            return result
        finally:
            with self._analysis_lock:
                self._analysis_inflight.discard(event_id)

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
        self.sync_registry()
        results: list[dict[str, Any]] = []
        for index, feed in enumerate(load_feeds()):
            url = str(feed["url"])
            source = str(feed.get("source", "rss"))
            competitor_id = str(feed.get("competitor_id", ""))
            competitor = self.store.get_competitor(competitor_id) if competitor_id else None
            if competitor is None:
                results.append({"url": url, "status": "error", "error": "Unknown competitor_id"})
                continue
            # Pace LinkedIn/YouTube Chromium routes so RSSHub is less likely to 503.
            if index and (":1200/" in url or "rsshub:" in url):
                time.sleep(2)
            feed_cursor = f"feed-seeded:{Store.canonical_url(url)}:{competitor.id}"
            seeded = bool(self.store.get_cursor(feed_cursor))
            try:
                items = collect_rss(url, source)
                created = 0
                previous_emit = self._emit_new_feed_items
                self._emit_new_feed_items = seeded
                try:
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
                finally:
                    self._emit_new_feed_items = previous_emit
                if not seeded:
                    self.store.set_cursor(feed_cursor, utc_now())
                results.append({"url": url, "status": "ok", "items": len(items), "events": created, "seeded": seeded})
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
            competitor = self.store.get_competitor(event.competitor_id)
            payload["competitor_name"] = competitor_names.get(event.competitor_id, event.competitor_id)
            if competitor:
                payload["organization_id"] = competitor.organization_id
                payload["relationship"] = competitor.relationship
                payload["product_category"] = competitor.product_category
            events.append(payload)
        return events

    def source_health(self) -> list[dict[str, str]]:
        self.sync_registry()
        configured_feeds = len(load_feeds())
        source_counts = self.store.source_competitor_counts()
        website_scans = source_counts.get("website", 0)
        webhook_scans = source_counts.get("changedetection", 0)
        return [
            {
                "source": "website",
                "status": "receiving" if website_scans else "ready",
                "detail": f"{website_scans}/{len(self.active_competitors())} URLs scanned",
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
        self.sync_registry()
        return self.store.monitor_status()

    def summary(self) -> dict[str, int]:
        self.sync_registry()
        return self.store.summary()
