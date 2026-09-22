from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from competitor_intelligence.analysis import content_hash, meaningful_change
from competitor_intelligence.collectors import CollectedContent, FeedItem
from competitor_intelligence.config import load_competitors
from competitor_intelligence.models import Competitor
from competitor_intelligence.provision import _notification_url, provision_changedetection
from competitor_intelligence.service import IntelligenceService
from competitor_intelligence.store import Store


class IntelligenceCoreTests(unittest.TestCase):
    def test_registry_models_companies_as_brand_relationships(self) -> None:
        registry = load_competitors()
        self.assertEqual(len(registry), 13)
        self.assertEqual(sum(item.monitor for item in registry), 12)
        self.assertEqual(len({item.organization_id for item in registry}), 11)

        howden = [item for item in registry if item.organization_id == "howden"]
        self.assertEqual({item.brand_id for item in howden}, {"jade", "doctorshield"})
        self.assertTrue(all(item.relationship == "DIRECT_COMPETITOR" for item in howden))

        chubb = next(item for item in registry if item.organization_id == "chubb" and item.brand_id == "jade")
        self.assertEqual(chubb.relationship, "DIRECT_COMPETITOR")
        marsh = next(item for item in registry if item.organization_id == "marsh")
        self.assertEqual(marsh.name, "Marsh / MEDEFEND")
        liberty_context = next(item for item in registry if item.id == "jaguar-liberty-context")
        self.assertEqual(liberty_context.relationship, "PARTNER")
        self.assertFalse(liberty_context.monitor)

    def test_store_persists_relationships_and_active_watchlist_count(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "test.db")
            for competitor in load_competitors():
                store.upsert_competitor(competitor)

            summary = store.summary()
            self.assertEqual(summary["competitors"], 12)
            self.assertEqual(summary["relationships"], 13)
            self.assertEqual(summary["organizations"], 11)
            liberty = store.get_competitor("jaguar-liberty-context")
            self.assertIsNotNone(liberty)
            self.assertEqual(liberty.relationship, "PARTNER")
            self.assertFalse(liberty.monitor)
            self.assertEqual(len(store.list_competitors(active_only=True)), 12)

    def test_registry_sync_retires_removed_rows_without_deleting_history(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "test.db")
            store.upsert_competitor(
                Competitor(
                    id="jade-competitor-1",
                    brand_id="jade",
                    name="Legacy watch",
                    niche="legacy",
                    countries=["SG"],
                    url="https://legacy.example.test/watch",
                ),
                registry_managed=True,
            )

            IntelligenceService(store)

            retired = store.get_competitor("jade-competitor-1")
            self.assertIsNotNone(retired)
            self.assertTrue(retired.retired)
            self.assertFalse(retired.monitor)
            self.assertNotIn("jade-competitor-1", {item.id for item in store.list_competitors()})

    def test_empty_registry_retires_managed_rows_when_file_exists(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            registry_path = Path(directory) / "competitors.json"
            registry_path.write_text("[]", encoding="utf-8")
            store = Store(Path(directory) / "test.db")
            store.upsert_competitor(
                Competitor(
                    id="managed-old",
                    brand_id="jade",
                    name="Managed old",
                    niche="legacy",
                    countries=["SG"],
                    url="https://legacy.example.test/watch",
                ),
                registry_managed=True,
            )

            with patch("competitor_intelligence.service.load_competitors", return_value=[]), \
                 patch("competitor_intelligence.service.COMPETITORS_PATH", registry_path):
                IntelligenceService(store)

            retired = store.get_competitor("managed-old")
            self.assertIsNotNone(retired)
            self.assertTrue(retired.retired)

    def test_url_only_lookup_rejects_ambiguous_active_relationships(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "test.db")
            for competitor_id in ("active-one", "active-two"):
                store.upsert_competitor(
                    Competitor(
                        id=competitor_id,
                        brand_id="jade",
                        name=competitor_id,
                        niche="valuable goods",
                        countries=["SG"],
                        url="https://example.test/shared",
                    )
                )

            with self.assertRaisesRegex(ValueError, "multiple active relationships"):
                store.find_competitor_by_url("https://EXAMPLE.TEST/shared/")

    def test_normalized_hash_ignores_whitespace_noise(self) -> None:
        self.assertEqual(content_hash("A  page\nwith text"), content_hash("A page with   text"))
        self.assertFalse(meaningful_change("Trusted by 8,000 businesses", "Trusted by 8,001 businesses"))
        self.assertTrue(meaningful_change("Starting from SGD 500", "Starting from SGD 425 with expanded cover"))
        self.assertTrue(meaningful_change("Premium USD 800", "Premium USD 801"))
        old = "alpha beta gamma " * 100
        self.assertTrue(meaningful_change(old, old.replace(" gamma", "")))

    def test_changedetection_content_creates_one_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "test.db")
            competitor = Competitor(
                id="doctor-1",
                brand_id="doctorshield",
                name="Test Medical Mutual",
                niche="medical indemnity",
                countries=["SG"],
                url="https://example.test/medical",
                priority="high",
            )
            store.upsert_competitor(competitor)
            service = IntelligenceService(store)
            service.scan(competitor.id, CollectedContent("Medical cover from SGD 500", "changedetection"))
            result = service.scan(
                competitor.id,
                CollectedContent("Medical cover from SGD 425 with a new plan", "changedetection"),
            )
            self.assertEqual(result.status, "changed")
            self.assertTrue(result.event_id)
            self.assertEqual(len(service.events()), 1)
            repeat = service.scan(
                competitor.id,
                CollectedContent("Medical cover from SGD 425 with a new plan", "changedetection"),
            )
            self.assertFalse(repeat.changed)
            self.assertEqual(repeat.status, "unchanged")
            self.assertEqual(len(service.events()), 1)

    def test_sources_are_compared_in_separate_streams(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "test.db")
            competitor = Competitor(
                id="stream-1",
                brand_id="jade",
                name="Stream Test",
                niche="valuable goods",
                countries=["SG"],
                url="https://example.test/product",
            )
            store.upsert_competitor(competitor)
            service = IntelligenceService(store)
            website = service.scan(
                competitor.id,
                CollectedContent("Website baseline", "website", url=competitor.url, source_key=competitor.url),
            )
            webhook = service.scan(
                competitor.id,
                CollectedContent("Webhook baseline", "changedetection", url=competitor.url, source_key=competitor.url),
            )
            self.assertEqual(website.status, "baseline")
            self.assertEqual(webhook.status, "baseline")
            self.assertEqual(len(service.events()), 0)

    def test_monitor_status_exposes_real_snapshot_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "test.db")
            competitor = Competitor(
                id="status-1",
                brand_id="jaguar",
                name="Status Test",
                niche="cargo",
                countries=["SG"],
                url="https://example.test/cargo",
            )
            store.upsert_competitor(competitor)
            service = IntelligenceService(store)
            service.scan(competitor.id, CollectedContent("Cargo baseline", "website", url=competitor.url, source_key=competitor.url))
            row = next(item for item in service.monitor_status() if item["competitor_id"] == competitor.id)
            self.assertEqual(row["status"], "active")
            self.assertEqual(row["source"], "website")
            self.assertEqual(row["snapshots"], 1)
            self.assertEqual(row["versions"], 1)

    def test_equivalent_sources_create_one_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "test.db")
            competitor = Competitor(
                id="dedupe-1",
                brand_id="jade",
                name="Dedupe Test",
                niche="valuable goods",
                countries=["SG"],
                url="https://example.test/product",
            )
            store.upsert_competitor(competitor)
            service = IntelligenceService(store)
            service.scan(
                competitor.id,
                CollectedContent(
                    "Starting from SGD 500",
                    "website",
                    url="https://EXAMPLE.TEST/product/",
                    source_key="https://EXAMPLE.TEST/product/",
                ),
            )
            service.scan(
                competitor.id,
                CollectedContent(
                    "Starting from SGD 500",
                    "changedetection",
                    url="https://example.test/product/",
                    source_key="https://example.test/product/",
                ),
            )
            website_change = service.scan(
                competitor.id,
                CollectedContent(
                    "Starting from SGD 425",
                    "website",
                    url="https://example.test/product",
                    source_key="https://example.test/product",
                ),
            )
            webhook_change = service.scan(
                competitor.id,
                CollectedContent(
                    "Starting from SGD 425",
                    "changedetection",
                    url="https://example.test/product/",
                    source_key="https://example.test/product/",
                ),
            )
            self.assertTrue(website_change.changed)
            self.assertTrue(webhook_change.changed)
            self.assertEqual(website_change.event_id, webhook_change.event_id)
            self.assertEqual(len(service.events()), 1)

    def test_feed_items_are_stable_across_polls(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "test.db")
            competitor = Competitor(
                id="feed-1",
                brand_id="jaguar",
                name="Feed Test",
                niche="cargo",
                countries=["SG"],
                url="https://example.test/cargo",
            )
            store.upsert_competitor(competitor)
            service = IntelligenceService(store)
            items = [
                FeedItem("Launch", "New cargo cover", "https://example.test/news/launch"),
                FeedItem("Rates", "Updated rates", "https://example.test/news/rates"),
            ]
            with patch("competitor_intelligence.service.load_feeds", return_value=[
                {"url": "https://example.test/feed.xml", "competitor_id": competitor.id}
            ]), patch("competitor_intelligence.service.collect_rss", return_value=items):
                first = service.poll_feeds()
                second = service.poll_feeds()
            self.assertEqual(first[0]["events"], 0)
            self.assertEqual(second[0]["events"], 0)
            self.assertEqual(len(service.events()), 0)

    def test_legacy_snapshot_streams_are_migrated(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "legacy.db"
            with closing(sqlite3.connect(path)) as connection, connection:
                connection.executescript(
                    """
                    CREATE TABLE competitors (
                        id TEXT PRIMARY KEY, brand_id TEXT NOT NULL, name TEXT NOT NULL,
                        niche TEXT NOT NULL, countries TEXT NOT NULL, url TEXT NOT NULL,
                        priority TEXT NOT NULL
                    );
                    CREATE TABLE snapshots (
                        id TEXT PRIMARY KEY, competitor_id TEXT NOT NULL,
                        content_hash TEXT NOT NULL, content TEXT NOT NULL,
                        source TEXT NOT NULL, change_summary TEXT, scraped_at TEXT NOT NULL
                    );
                    """
                )
                connection.execute(
                    "INSERT INTO competitors VALUES (?, ?, ?, ?, ?, ?, ?)",
                    ("legacy-1", "jade", "Legacy", "cargo", '["SG"]', "https://EXAMPLE.test/page/", "high"),
                )
                connection.execute(
                    "INSERT INTO snapshots VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        "snapshot-1",
                        "legacy-1",
                        content_hash("Legacy baseline"),
                        "Legacy baseline",
                        "changedetection",
                        None,
                        "2026-09-21T00:00:00+00:00",
                    ),
                )
            store = Store(path)
            snapshot = store.latest_snapshot("legacy-1")
            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot.source_key, "changedetection:https://example.test/page")

    def test_recurring_transition_is_not_suppressed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "test.db")
            competitor = Competitor(
                id="recurring-1",
                brand_id="jade",
                name="Recurring Test",
                niche="valuable goods",
                countries=["SG"],
                url="https://example.test/product",
            )
            store.upsert_competitor(competitor)
            service = IntelligenceService(store)
            values = (
                "Starting from SGD 500",
                "Starting from SGD 425",
                "Starting from SGD 500",
                "Starting from SGD 425",
            )
            results = [
                service.scan(
                    competitor.id,
                    CollectedContent(value, "website", url=competitor.url, source_key=competitor.url),
                )
                for value in values
            ]
            self.assertEqual([result.changed for result in results], [False, True, True, True])
            self.assertEqual(len(service.events()), 3)
            self.assertEqual(len({result.event_id for result in results[1:]}), 3)

    def test_notification_url_carries_webhook_token(self) -> None:
        with patch("competitor_intelligence.provision.WEBHOOK_TOKEN", "token/with+symbols"):
            self.assertEqual(
                _notification_url(),
                "post://intelligence:8787/api/webhooks/changedetection?+X-Webhook-Token=token%2Fwith%2Bsymbols",
            )

    def test_existing_changedetection_watch_is_reconciled(self) -> None:
        competitor = Competitor(
            id="provision-1",
            brand_id="jade",
            name="Provision Test",
            niche="valuable goods",
            countries=["SG"],
            url="https://example.test/product",
        )

        class FakeResponse:
            def __init__(self, body: str, status: int = 200):
                self.body = body.encode("utf-8")
                self.status = status

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return self.body

        responses = [
            FakeResponse(json.dumps({"watch-id": {"url": "https://EXAMPLE.test/product/"}})),
            FakeResponse("{}", 200),
        ]
        with patch("competitor_intelligence.provision.CHANGEDETECTION_API_KEY", "api-key"), \
             patch("competitor_intelligence.provision.load_competitors", return_value=[competitor]), \
             patch("competitor_intelligence.provision.urllib.request.urlopen", side_effect=responses) as opener:
            result = provision_changedetection()
        request = opener.call_args_list[1].args[0]
        self.assertEqual(result[0]["status"], "updated")
        self.assertEqual(request.get_method(), "PUT")
        self.assertTrue(request.full_url.endswith("/api/v1/watch/watch-id"))

    def test_legacy_changedetection_watch_is_paused(self) -> None:
        class FakeResponse:
            def __init__(self, body: str, status: int = 200):
                self.body = body.encode("utf-8")
                self.status = status

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return self.body

        responses = [
            FakeResponse(
                json.dumps(
                    {
                        "legacy-watch": {
                            "url": "https://www.msig.com.sg/commercial/professional-indemnity"
                        }
                    }
                )
            ),
            FakeResponse(
                json.dumps(
                    {
                        "notification_urls": [
                            "post://intelligence:8787/api/webhooks/changedetection"
                        ]
                    }
                )
            ),
            FakeResponse("{}", 200),
        ]
        with patch("competitor_intelligence.provision.CHANGEDETECTION_API_KEY", "api-key"), \
             patch("competitor_intelligence.provision.load_competitors", return_value=[]), \
             patch("competitor_intelligence.provision.urllib.request.urlopen", side_effect=responses) as opener:
            result = provision_changedetection()

        request = opener.call_args_list[2].args[0]
        self.assertEqual(result[0]["status"], "paused")
        self.assertEqual(request.get_method(), "PUT")
        self.assertTrue(request.full_url.endswith("/api/v1/watch/legacy-watch"))
        self.assertEqual(json.loads(request.data), {"paused": True})

    def test_manual_legacy_changedetection_watch_is_not_paused(self) -> None:
        class FakeResponse:
            def __init__(self, body: str):
                self.body = body.encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return self.body

        responses = [
            FakeResponse(
                json.dumps(
                    {
                        "manual-watch": {
                            "url": "https://www.msig.com.sg/commercial/professional-indemnity"
                        }
                    }
                )
            ),
            FakeResponse(json.dumps({"notification_urls": []})),
        ]

        with patch("competitor_intelligence.provision.CHANGEDETECTION_API_KEY", "api-key"), \
             patch("competitor_intelligence.provision.load_competitors", return_value=[]), \
             patch("competitor_intelligence.provision.urllib.request.urlopen", side_effect=responses) as opener:
            result = provision_changedetection()

        self.assertEqual(result, [])
        self.assertEqual(opener.call_count, 2)


if __name__ == "__main__":
    unittest.main()
