from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from competitor_intelligence.analysis import content_hash, meaningful_change
from competitor_intelligence.collectors import CollectedContent
from competitor_intelligence.models import Competitor
from competitor_intelligence.service import IntelligenceService
from competitor_intelligence.store import Store


class IntelligenceCoreTests(unittest.TestCase):
    def test_normalized_hash_ignores_whitespace_noise(self) -> None:
        self.assertEqual(content_hash("A  page\nwith text"), content_hash("A page with   text"))
        self.assertFalse(meaningful_change("Trusted by 8,000 businesses", "Trusted by 8,001 businesses"))
        self.assertTrue(meaningful_change("Starting from SGD 500", "Starting from SGD 425 with expanded cover"))

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
            self.assertEqual(len(service.events()), 1)


if __name__ == "__main__":
    unittest.main()
