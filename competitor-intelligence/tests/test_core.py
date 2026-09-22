from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
import urllib.error
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from competitor_intelligence.analysis import classify_change, confidence_for_change, content_hash, meaningful_change
from competitor_intelligence.collectors import (CollectedContent, FeedItem, collect_watch,
                                                collect_website, extract_income_pricing_text,
                                                request_bytes)
from competitor_intelligence.config import load_competitors, load_watches
from competitor_intelligence.models import Competitor, WatchSource
from competitor_intelligence.provision import _fetch_backend, _notification_url, provision_changedetection
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

    def test_running_service_refreshes_registry_before_dashboard_reads(self) -> None:
        first = Competitor(
            id="first-competitor",
            brand_id="jade",
            name="First competitor",
            niche="valuable goods",
            countries=["SG"],
            url="https://first.example.test",
        )
        second = Competitor(
            id="second-competitor",
            brand_id="jade",
            name="Second competitor",
            niche="valuable goods",
            countries=["SG"],
            url="https://second.example.test",
        )
        with tempfile.TemporaryDirectory() as directory, patch(
            "competitor_intelligence.service.COMPETITORS_PATH",
            Path(directory) / "competitors.json",
        ):
            registry_path = Path(directory) / "competitors.json"
            registry_path.write_text(json.dumps([first.to_dict()]), encoding="utf-8")
            store = Store(Path(directory) / "test.db")
            service = IntelligenceService(store)
            self.assertEqual([item.id for item in service.competitors()], [first.id])

            registry_path.write_text(
                json.dumps([first.to_dict(), second.to_dict()]), encoding="utf-8"
            )

            self.assertEqual(
                {item.id for item in service.competitors()},
                {first.id, second.id},
            )

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

    def test_confidence_varies_with_evidence_and_source_quality(self) -> None:
        competitor = Competitor(
            id="confidence-1",
            brand_id="doctorshield",
            name="Confidence Test",
            niche="medical indemnity",
            countries=["SG"],
            url="https://example.test/monitor",
        )
        price = classify_change(
            competitor,
            "Annual premium S$500.",
            "Annual premium S$425 with expanded cover.",
            "website",
        )
        product = classify_change(
            competitor,
            "Medical indemnity cover for doctors.",
            "Medical indemnity cover for doctors with a new product and expanded claims support.",
            "website",
        )
        weak = confidence_for_change(
            "Coverage for professionals.",
            "Coverage for professionals in Singapore.",
            "rss",
            "positioning_change",
        )

        self.assertEqual(price["change_type"], "price_change")
        self.assertEqual(product["change_type"], "new_product")
        self.assertGreater(price["confidence"], product["confidence"])
        self.assertGreater(product["confidence"], weak)
        self.assertNotEqual(price["confidence"], 0.82)
        self.assertNotEqual(product["confidence"], 0.82)
        self.assertTrue(0.50 <= weak <= 0.98)

    def test_cookie_banner_container_is_excluded_from_website_content(self) -> None:
        main = "<main><h1>Professional indemnity cover</h1><p>Annual premium S$500.</p></main>"
        first = (
            f"<html><body>{main}<div id='cookie-banner'>"
            "We use cookies. Accept all cookies.</div></body></html>"
        ).encode()
        second = (
            f"<html><body>{main}<div id='cookie-banner'>"
            "We use cookies. Accept all cookies. Manage preferences and reject non-essential cookies."
            "</div></body></html>"
        ).encode()
        with patch("competitor_intelligence.collectors.request_bytes", return_value=(first, "text/html")):
            first_page = collect_website("https://example.test/monitor")
        with patch("competitor_intelligence.collectors.request_bytes", return_value=(second, "text/html")):
            second_page = collect_website("https://example.test/monitor")

        self.assertEqual(first_page.content, second_page.content)
        self.assertNotIn("Manage preferences", second_page.content)

    def test_cookie_filter_preserves_substantive_same_line_price_changes(self) -> None:
        old = "Annual premium SGD 500. We use cookies to improve your experience."
        new = "Annual premium SGD 750. We use cookies to improve your experience."

        self.assertTrue(meaningful_change(old, new))

    def test_cookie_filter_preserves_ambiguous_consent_first_product_changes(self) -> None:
        old = "Accept all cookies New product launch announced for doctors."
        new = "Accept all cookies New product launch postponed until next quarter."

        self.assertTrue(meaningful_change(old, new))

    def test_cookie_labelled_void_element_does_not_hide_following_content(self) -> None:
        html = (
            b"<html><body><input aria-label='Cookie consent'>"
            b"<main><h1>Professional indemnity cover</h1>"
            b"<p>Annual premium S$500.</p></main></body></html>"
        )
        with patch("competitor_intelligence.collectors.request_bytes", return_value=(html, "text/html")):
            page = collect_website("https://example.test/monitor")

        self.assertIn("Professional indemnity cover", page.content)
        self.assertIn("Annual premium S$500.", page.content)

    def test_cookie_only_change_is_unchanged_and_creates_no_event(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "test.db")
            competitor = Competitor(
                id="cookie-1",
                brand_id="jade",
                name="Cookie Test",
                niche="valuable goods",
                countries=["SG"],
                url="https://example.test/monitor",
            )
            store.upsert_competitor(competitor)
            service = IntelligenceService(store)
            url = competitor.url
            first = service.scan(
                competitor.id,
                CollectedContent(
                    "Stable page copy with annual premium S$500.\n"
                    "We use cookies. Accept all cookies.",
                    "website",
                    url=url,
                    source_key=url,
                ),
            )
            second = service.scan(
                competitor.id,
                CollectedContent(
                    "Stable page copy with annual premium S$500.\n"
                    "We use cookies. Accept all cookies. Manage preferences and reject non-essential cookies.",
                    "website",
                    url=url,
                    source_key=url,
                ),
            )

            self.assertEqual(first.status, "baseline")
            self.assertEqual(second.status, "unchanged")
            self.assertFalse(second.changed)
            self.assertIsNone(second.event_id)
            self.assertEqual(len(service.events()), 0)
            snapshot = store.latest_snapshot(competitor.id, f"website:{url}")
            self.assertIsNotNone(snapshot)
            self.assertNotIn("Manage preferences", snapshot.content)

    def test_failed_scan_returns_error_and_preserves_previous_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = Store(Path(directory) / "test.db")
            competitor = Competitor(
                id="blocked-1",
                brand_id="jade",
                name="Blocked Test",
                niche="valuable goods",
                countries=["SG"],
                url="https://example.test/monitor",
            )
            store.upsert_competitor(competitor)
            service = IntelligenceService(store)
            baseline = service.scan(
                competitor.id,
                CollectedContent(
                    "Stable baseline content.",
                    "website",
                    url=competitor.url,
                    source_key=competitor.url,
                ),
            )
            with patch(
                "competitor_intelligence.service.collect_website",
                side_effect=ValueError("HTTP 247 bot-protection challenge"),
            ):
                failed = service.scan(competitor.id)

            self.assertEqual(baseline.status, "baseline")
            self.assertEqual(failed.status, "error")
            self.assertFalse(failed.changed)
            self.assertIn("bot-protection", failed.error or "")
            snapshot = store.latest_snapshot(competitor.id, f"website:{competitor.url}")
            self.assertIsNotNone(snapshot)
            self.assertEqual(snapshot.content, "Stable baseline content.")

    def test_income_pricing_extracts_category_discount_and_effective_date(self) -> None:
        html = b'''<table><tr><th>Risk Category</th><th>Annual Premium (S$)</th></tr>
        <tr><td>Low Risk (see definition)</td><td>$1,773.98</td></tr>
        <tr><td>High Risk</td><td>$8,583.75</td></tr></table>
        <p>10% discount will be applied from 2 September 2025 to 1 September 2026.</p>'''
        with patch("competitor_intelligence.collectors.request_bytes", return_value=(html, "text/html")):
            result = json.loads(collect_watch("https://example.test/prices", "pricing").content)
        self.assertEqual(result["premiums"]["Low Risk (see definition)"], "S$1,773.98")
        self.assertEqual(result["premiums"]["High Risk"], "S$8,583.75")
        self.assertIn("10% discount", result["discount"])
        self.assertEqual(result["effective_date"], "from 2 September 2025 to 1 September 2026")

    def test_news_listing_extracts_next_data_article_links(self) -> None:
        html = b'''<html><head><title>Newsroom</title></head><body>
        <script id="__NEXT_DATA__" type="application/json">
        {"props":{"pageProps":{"page":{"blocks":[{"settings":{"cards":{"articles":[
        {"title":"New specie underwriting capability","buttons":[{"link":"/sg/newsroom/new-specie-capability"}]},
        {"title":"A second article","buttons":[{"link":"/sg/newsroom/second-article"}]}
        ]}}}]}}}}
        </script></body></html>'''
        with patch("competitor_intelligence.collectors.request_bytes", return_value=(html, "text/html")):
            result = collect_watch("https://www.libertyinternational.com/sg/newsroom", "news")
        self.assertIn("https://www.libertyinternational.com/sg/newsroom/new-specie-capability", result.content)
        self.assertIn("New specie underwriting capability", result.content)

    def test_bot_protection_challenge_is_reported_without_creating_content(self) -> None:
        body = b'<script src="/kramericaindustries.ac_v2.lib.js"></script>'
        response = type("Response", (), {
            "status": 247,
            "headers": {},
            "read": lambda self: body,
            "__enter__": lambda self: self,
            "__exit__": lambda self, *args: False,
        })()
        with patch("competitor_intelligence.collectors.urllib.request.urlopen", return_value=response):
            with self.assertRaisesRegex(ValueError, "HTTP 247 bot-protection challenge"):
                collect_watch("https://www.g4s.com/what-we-do/cash-solutions", "logistics")

    def test_transient_http_failure_is_retried(self) -> None:
        response = type("Response", (), {
            "status": 200,
            "headers": {"Content-Type": "text/plain"},
            "read": lambda self: b"ok",
            "__enter__": lambda self: self,
            "__exit__": lambda self, *args: False,
        })()
        failure = urllib.error.HTTPError(
            "https://example.test", 503, "temporary", {}, None
        )
        with patch(
            "competitor_intelligence.collectors.urllib.request.urlopen",
            side_effect=[failure, response],
        ) as opener, patch("competitor_intelligence.collectors.time.sleep") as sleeper:
            self.assertEqual(request_bytes("https://example.test/page"), (b"ok", "text/plain"))
        self.assertEqual(opener.call_count, 2)
        sleeper.assert_called_once_with(1)

    def test_changedetection_pricing_text_extracts_all_risk_categories(self) -> None:
        text = "\n".join(f"{category}\n${1000 + index:,.2f}" for index, category in enumerate((
            "Obstetric Risk", "Gynaecology", "Office Gynaecology", "High Risk",
            "Medium Risk", "Low Risk", "Family Medicine - Procedural",
            "Family Medicine - Non-Procedural",
        )))
        payload = json.loads(extract_income_pricing_text(text))
        self.assertEqual(len(payload["premiums"]), 8)
        self.assertEqual(payload["premiums"]["Low Risk"], "S$1,005.00")

    def test_pricing_change_creates_category_specific_event_and_diff(self) -> None:
        competitor = Competitor("doctorshield-income", "doctorshield", "Income Insurance",
                                "medical indemnity", ["SG"],
                                "https://example.test/prices")
        watch = WatchSource("income-prices", competitor.id, competitor.url, "pricing", "high", 6)
        with tempfile.TemporaryDirectory() as directory, \
             patch("competitor_intelligence.service.load_watches", return_value=[watch]):
            store = Store(Path(directory) / "test.db")
            store.upsert_competitor(competitor)
            service = IntelligenceService(store)
            before = json.dumps({"premiums": {"Low Risk": "S$1,773.98"}, "discount": None, "effective_date": None})
            after = json.dumps({"premiums": {"Low Risk": "S$1,899.00"}, "discount": None, "effective_date": None})
            service.scan(competitor.id, CollectedContent(before, "website", url=watch.url, source_key=watch.url))
            result = service.scan(competitor.id, CollectedContent(after, "website", url=watch.url, source_key=watch.url))
            self.assertTrue(result.changed)
            event = service.events()[0]
            self.assertIn("Low Risk", event["summary"])
            self.assertEqual(event["previous_value"], "Low Risk: S$1,773.98")
            self.assertEqual(event["current_value"], "Low Risk: S$1,899.00")
            self.assertIn("S$1,899.00", service.event_diff(result.event_id)["diff"])

    def test_multiple_premium_changes_are_all_reported(self) -> None:
        before = json.dumps({"premiums": {"Low Risk": "S$100", "High Risk": "S$200"}})
        after = json.dumps({"premiums": {"Low Risk": "S$120", "High Risk": "S$250"}})
        competitor = Competitor("income", "doctorshield", "Income", "medical", ["SG"],
                                "https://example.test/prices")
        result = IntelligenceService._price_change(competitor, before, after)
        self.assertIn("Low Risk", result["summary"])
        self.assertIn("High Risk", result["summary"])
        self.assertIn("S$250", result["current_value"])

    def test_changedetection_price_snapshot_uses_structured_comparison(self) -> None:
        competitor = Competitor("doctorshield-income", "doctorshield", "Income",
                                "medical indemnity", ["SG"], "https://example.test/prices")
        watch = WatchSource("prices", competitor.id, competitor.url, "pricing", "high", 6)
        categories = ("Obstetric Risk", "Gynaecology", "Office Gynaecology", "High Risk",
                      "Medium Risk", "Low Risk", "Family Medicine - Procedural",
                      "Family Medicine - Non-Procedural")
        def page(low_risk):
            return "\n".join(f"{category}\n${low_risk if category == 'Low Risk' else 1000 + index:,.2f}"
                             for index, category in enumerate(categories))
        with tempfile.TemporaryDirectory() as directory, \
             patch("competitor_intelligence.service.load_watches", return_value=[watch]):
            store = Store(Path(directory) / "test.db")
            store.upsert_competitor(competitor)
            service = IntelligenceService(store)
            service.scan(competitor.id, CollectedContent(page(1773.98), "changedetection",
                                                       url=watch.url, source_key=watch.url))
            result = service.scan(competitor.id, CollectedContent(page(1899.00), "changedetection",
                                                                url=watch.url, source_key=watch.url))
            self.assertTrue(result.changed)
            self.assertEqual(service.events()[0]["previous_value"], "Low Risk: S$1,773.98")
            self.assertIn("S$1,899.00", service.event_diff(result.event_id)["diff"])

    def test_news_listing_requires_a_new_relevant_article_link(self) -> None:
        competitor = Competitor("news-1", "jade", "Example", "jewellers block", ["SG"],
                                "https://example.test/news")
        watch = WatchSource("news", competitor.id, competitor.url, "news", "medium", 6)
        with tempfile.TemporaryDirectory() as directory, \
             patch("competitor_intelligence.service.load_watches", return_value=[watch]), \
             patch("competitor_intelligence.service.collect_website", return_value=CollectedContent(
                 "Jewellery cover expansion announced", "website")), \
             patch("competitor_intelligence.service.article_relevant", return_value=True):
            store = Store(Path(directory) / "test.db")
            store.upsert_competitor(competitor)
            service = IntelligenceService(store)
            service.scan(competitor.id, CollectedContent("Page header", "changedetection",
                                                       url=watch.url, source_key=watch.url))
            self.assertFalse(service.scan(competitor.id, CollectedContent(
                "Page header updated", "changedetection", url=watch.url,
                source_key=watch.url)).changed)
            service.scan(competitor.id, CollectedContent(
                "https://example.test/news/old\tOld article", "website",
                url=watch.url, source_key=watch.url))
            result = service.scan(competitor.id, CollectedContent(
                "https://example.test/news/old\tOld article\nhttps://example.test/news/new\tNew jewellery article",
                "website", url=watch.url, source_key=watch.url))
            self.assertTrue(result.changed)
            self.assertEqual(service.events()[0]["change_type"], "article")

    def test_changedetection_history_sync_is_incremental(self) -> None:
        competitor = Competitor("watch-1", "jade", "Test Jeweller", "jewellers block", ["SG"],
                                "https://example.test/product")
        watch = WatchSource("product", competitor.id, competitor.url, "product", "high", 6)

        class FakeResponse:
            def __init__(self, body):
                self.body = body.encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return self.body

        def open_url(request, timeout):
            url = request.full_url
            if url.endswith("/api/v1/watch"):
                return FakeResponse(json.dumps({"uuid-1": {"url": competitor.url}}))
            if url.endswith("/history"):
                return FakeResponse(json.dumps({"100": "old", "200": "new"}))
            return FakeResponse("Cover from SGD 500" if url.endswith("/100") else "Cover from SGD 425")

        with tempfile.TemporaryDirectory() as directory, \
             patch("competitor_intelligence.service.load_watches", return_value=[watch]), \
             patch("competitor_intelligence.service.urllib.request.urlopen", side_effect=open_url):
            store = Store(Path(directory) / "test.db")
            store.upsert_competitor(competitor)
            service = IntelligenceService(store)
            self.assertEqual(service.sync_changedetection()["imported"], 2)
            self.assertEqual(len(service.events()), 1)
            self.assertEqual(service.sync_changedetection()["imported"], 0)
            self.assertEqual(len(service.events()), 1)

    def test_history_sync_does_not_replay_older_versions_after_webhook(self) -> None:
        competitor = Competitor("watch-2", "jade", "Test Jeweller", "jewellers block", ["SG"],
                                "https://example.test/product")
        watch = WatchSource("product", competitor.id, competitor.url, "product", "high", 6)

        class FakeResponse:
            def __init__(self, body):
                self.body = body.encode()

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return self.body

        def open_url(request, timeout):
            url = request.full_url
            if url.endswith("/api/v1/watch"):
                return FakeResponse(json.dumps({"uuid-2": {"url": competitor.url}}))
            if url.endswith("/history"):
                return FakeResponse(json.dumps({"100": "old", "200": "current", "300": "new"}))
            return FakeResponse({"100": "Price SGD 100", "200": "Price SGD 200",
                                 "300": "Price SGD 300"}[url.rsplit("/", 1)[-1]])

        with tempfile.TemporaryDirectory() as directory, \
             patch("competitor_intelligence.service.load_watches", return_value=[watch]), \
             patch("competitor_intelligence.service.urllib.request.urlopen", side_effect=open_url):
            store = Store(Path(directory) / "test.db")
            store.upsert_competitor(competitor)
            service = IntelligenceService(store)
            service.scan(competitor.id, CollectedContent("Price SGD 200", "changedetection",
                                                         url=watch.url, source_key=watch.url,
                                                         observed_at="1970-01-01T00:03:20+00:00"))
            self.assertEqual(service.sync_changedetection()["imported"], 1)
            self.assertEqual(len(service.events()), 1)
            self.assertIn("SGD 300", service.events()[0]["evidence"])

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
                {"url": "https://example.test/feed.xml", "competitor_id": competitor.id, "source": "rsshub"}
            ]), patch("competitor_intelligence.service.collect_rss", return_value=items):
                first = service.poll_feeds()
                second = service.poll_feeds()
            self.assertEqual(first[0]["events"], 0)
            self.assertFalse(first[0]["seeded"])
            self.assertEqual(second[0]["events"], 0)
            self.assertTrue(second[0]["seeded"])
            self.assertEqual(len(service.events()), 0)

            newer = items + [FeedItem("Asia hub", "Opened SG hub", "https://example.test/news/asia-hub")]
            with patch("competitor_intelligence.service.load_feeds", return_value=[
                {"url": "https://example.test/feed.xml", "competitor_id": competitor.id, "source": "rsshub"}
            ]), patch("competitor_intelligence.service.collect_rss", return_value=newer):
                third = service.poll_feeds()
            self.assertEqual(third[0]["events"], 1)
            events = service.events()
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["source"], "rsshub")
            self.assertIn("Asia hub", events[0]["summary"])

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
             patch("competitor_intelligence.provision.load_watches", return_value=[WatchSource("test-watch", competitor.id, competitor.url, "product", "high", 6)]), \
             patch("competitor_intelligence.provision.urllib.request.urlopen", side_effect=responses) as opener:
            result = provision_changedetection()
        request = opener.call_args_list[1].args[0]
        self.assertEqual(result[0]["status"], "updated")
        self.assertEqual(request.get_method(), "PUT")
        self.assertTrue(request.full_url.endswith("/api/v1/watch/watch-id"))
        payload = json.loads(request.data)
        self.assertEqual(payload["fetch_backend"], "html_webdriver")
        self.assertEqual(payload["time_between_check"], {"hours": 6, "minutes": 0, "seconds": 0})

    def test_liberty_watch_uses_http_backend(self) -> None:
        self.assertEqual(
            _fetch_backend("https://www.libertyinternational.com/sg/product/fine-art-and-specie"),
            "html_requests",
        )
        self.assertEqual(
            _fetch_backend("https://www.income.com.sg/commercial-insurance/medical-indemnity-insurance"),
            "html_requests",
        )
        self.assertEqual(
            _fetch_backend("https://www.g4s.com/what-we-do/cash-solutions"),
            "html_webdriver",
        )

    def test_g4s_watch_uses_challenge_wait_options(self) -> None:
        from competitor_intelligence.provision import _watch_fetch_options

        options = _watch_fetch_options("https://www.g4s.com/what-we-do/cash-solutions")
        self.assertTrue(options["ignore_status_codes"])
        self.assertGreaterEqual(options["webdriver_delay"], 20)
        self.assertIn("kramericaindustries", options["text_should_not_be_present"])

    def test_existing_unconfigured_watch_is_preserved(self) -> None:
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
             patch("competitor_intelligence.provision.load_watches", return_value=[]), \
             patch("competitor_intelligence.provision.urllib.request.urlopen", side_effect=responses) as opener:
            result = provision_changedetection()

        self.assertEqual(result, [])
        self.assertEqual(opener.call_count, 1)

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
             patch("competitor_intelligence.provision.load_watches", return_value=[]), \
             patch("competitor_intelligence.provision.urllib.request.urlopen", side_effect=responses) as opener:
            result = provision_changedetection()

        self.assertEqual(result, [])
        self.assertEqual(opener.call_count, 1)


if __name__ == "__main__":
    unittest.main()
