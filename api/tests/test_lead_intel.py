"""Lead discovery uses offline Overture configuration and safe account domains."""

import http.server
import json
import sqlite3
import socket
import sys
import threading
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from agents import lead_intel
from agents import lead_pipeline
from agents.lead_pipeline import (
    LeadPipelineError,
    _checked_url,
    _enrichment_requires_review,
    _safe_fetch,
    load_config,
    normalize_domain,
)


def test_overture_discovery_needs_no_provider_key():
    assert lead_intel.key_configured() is True


def test_fastapi_startup_uses_the_retry_aware_pipeline_scheduler(monkeypatch):
    calls = []
    monkeypatch.setattr(lead_pipeline, "start_scheduler", lambda: calls.append("started"))
    lead_intel.start_daily_refresh()
    assert calls == ["started"]


def test_pipeline_scheduler_starts_each_worker_once(monkeypatch):
    import threading

    started = []

    class FakeThread:
        def __init__(self, *, target, name, daemon):
            self.name = name
            self.target = target
            self.daemon = daemon

        def start(self):
            started.append(self.name)

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setenv("AURA_LEAD_REFRESH", "true")
    monkeypatch.setattr(threading, "Thread", FakeThread)
    monkeypatch.setattr(lead_pipeline, "_SCHEDULER_STARTED", False)
    lead_pipeline.start_scheduler()
    lead_pipeline.start_scheduler()
    assert started == ["aura-lead-refresh", "aura-lead-jobs"]


def test_manual_refresh_drains_enrichment_jobs_when_automatic_workers_are_disabled(monkeypatch):
    calls = []

    class FakeThread:
        def __init__(self, *, target, name, daemon):
            self.target = target
            self.name = name
            self.daemon = daemon

        def start(self):
            calls.append(self.name)
            self.target()

    monkeypatch.setenv("AURA_LEAD_REFRESH", "false")
    monkeypatch.setattr(lead_pipeline, "_SCHEDULER_STARTED", False)
    monkeypatch.setattr(lead_pipeline, "_MANUAL_JOB_WORKER_STARTED", False)
    monkeypatch.setattr(lead_pipeline, "refresh", lambda: calls.append("refresh"))
    monkeypatch.setattr(
        lead_pipeline,
        "resume_pending_jobs",
        lambda: calls.append("jobs") or {"pending_jobs": 0, "enriched": 0, "errors": []},
    )
    monkeypatch.setattr(lead_pipeline.threading, "Thread", FakeThread)

    lead_pipeline._manual_refresh_task()

    assert calls == ["refresh", "aura-lead-manual-jobs", "jobs"]


def test_record_job_progress_publishes_each_job_update_for_the_frontend(monkeypatch, tmp_path):
    state_path = tmp_path / "lead-refresh.json"
    state_path.write_text(json.dumps({"jobs_progress_total": 4}))
    monkeypatch.setattr(lead_pipeline, "STATE_PATH", state_path)

    lead_pipeline._record_job_progress()

    state = json.loads(state_path.read_text())
    assert state["jobs_progress_total"] == 5
    assert state["jobs_last_progress_at"]


def test_config_contains_supported_brands_and_current_categories():
    config = load_config()
    assert {"jade", "doctorshield", "jaguar"} <= set(config["brands"])
    assert config["qualification_score"] >= 75
    assert all(item["exact_categories"] for item in config["brands"].values())


def test_overture_discovery_scans_once_and_keeps_country_caps_separate(monkeypatch):
    class FakeDuckDBConnection:
        def __init__(self):
            self.queries = []
            self.description = []

        def execute(self, query, params=None):
            self.queries.append((query, params))
            return self

        def fetchall(self):
            return []

        def close(self):
            pass

    fake_connection = FakeDuckDBConnection()
    monkeypatch.setattr(lead_pipeline, "_duckdb_connection", lambda _duckdb: fake_connection)
    assert lead_pipeline.overture_candidates("2026-09-23.0") == []
    scans = [(query, params) for query, params in fake_connection.queries if "read_parquet" in query]
    assert len(scans) == 1
    query, params = scans[0]
    assert "PARTITION BY country_filter" in query
    assert "taxonomy.primary" in query and "basic_category" in query
    assert "permanently_closed" in query
    assert params[:6] == ["SG", 103.5, 104.1, 1.1, 1.5, "SG"]
    assert params[-1] == 300


def test_overture_discovery_query_reads_schema_v2_parquet(tmp_path, monkeypatch):
    import duckdb

    data_dir = tmp_path / "release" / "test-release" / "theme=places" / "type=place"
    data_dir.mkdir(parents=True)
    raw_connection = duckdb.connect(database=":memory:")
    raw_connection.execute(
        """CREATE TABLE places AS SELECT
            'place-1'::VARCHAR AS id,
            {'primary': 'Northwind Jewellers'} AS names,
            'jewelry_store'::VARCHAR AS basic_category,
            {'primary': 'jewelry_store', 'hierarchy': ['shopping', 'jewelry_store'], 'alternates': ['jewelry_store']} AS taxonomy,
            'open'::VARCHAR AS operating_status,
            0.95::DOUBLE AS confidence,
            ['https://northwind.test']::VARCHAR[] AS websites,
            ['info@northwind.test']::VARCHAR[] AS emails,
            ['+6561234567']::VARCHAR[] AS phones,
            []::VARCHAR[] AS socials,
            [{'freeform': 'Singapore', 'locality': 'Singapore', 'region': '', 'country': 'SG'}] AS addresses,
            [{'dataset': 'overture', 'provider': 'test'}] AS sources,
            {'xmin': 103.7, 'xmax': 103.9, 'ymin': 1.2, 'ymax': 1.4} AS bbox"""
    )
    raw_connection.execute(f"COPY places TO '{data_dir / 'part-0.parquet'}' (FORMAT PARQUET)")

    class LocalDuckDBConnection:
        def execute(self, query, params=None):
            if query.startswith(("INSTALL ", "LOAD ", "SET s3_region")):
                return self
            raw_connection.execute(query, params or [])
            return self

        @property
        def description(self):
            return raw_connection.description

        def fetchall(self):
            return raw_connection.fetchall()

        def close(self):
            raw_connection.close()

    monkeypatch.setattr(lead_pipeline, "OVERTURE_S3", str(tmp_path))
    monkeypatch.setattr(lead_pipeline, "_duckdb_connection", lambda _duckdb: LocalDuckDBConnection())
    rows = lead_pipeline.overture_candidates("test-release", country="SG")
    assert len(rows) == 1
    assert rows[0]["brand_id"] == "jade"
    assert rows[0]["country"] == "SG"
    assert rows[0]["category"] == "jewelry_store"
    assert rows[0]["email"] == "info@northwind.test"
    snapshot_connection = duckdb.connect(database=":memory:")
    snapshot = lead_pipeline._snapshot_tracked_places(snapshot_connection, "test-release", ["place-1"])
    snapshot_connection.close()
    assert snapshot["place-1"]["name"] == "Northwind Jewellers"
    assert float(snapshot["place-1"]["bbox"]["xmin"]) == pytest.approx(103.7)


def test_domain_resolution_groups_custom_subdomains_but_not_shared_hosting_tenants():
    assert normalize_domain("https://shop.brand.co.uk/contact") == "brand.co.uk"
    assert normalize_domain("https://first.wixsite.com") == "first.wixsite.com"
    assert normalize_domain("https://second.wixsite.com") == "second.wixsite.com"


def test_qualification_or_evidence_changes_require_a_fresh_review():
    assert not _enrichment_requires_review(qualified=True, evidence_changed=False)
    assert _enrichment_requires_review(qualified=True, evidence_changed=True)
    assert _enrichment_requires_review(qualified=False, evidence_changed=False)


@pytest.fixture
def lead_database(monkeypatch):
    from db import SQLiteConnectionWrapper, init_sqlite_db

    raw = sqlite3.connect(":memory:")
    init_sqlite_db(raw)
    wrapper = SQLiteConnectionWrapper(raw)

    @contextmanager
    def connection():
        try:
            yield wrapper
            wrapper.commit()
        except Exception:
            wrapper.rollback()
            raise

    monkeypatch.setattr(lead_pipeline, "get_connection", connection)
    yield wrapper
    raw.close()


def _seed_approved_lead(connection, outreach_status="approved"):
    connection.execute(
        "INSERT INTO leads (id,brand_id,name,category,location,url,country,status,fit_score,source,external_place_id,domain,"
        "overture_confidence,stage,review_status,reviewed_by,reviewed_at,outreach_status,outreach_approved_by,outreach_approved_at,"
        "score_breakdown,created_at,updated_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        ("lead-1", "jade", "Northwind Jewellers", "jewelry_store", "Singapore", "https://northwind.example", "SG",
         "qualified", 90, "overture_maps", "place-1", "northwind.example", 0.9, "qualified", "approved", "Reviewer",
         "today", outreach_status, "Reviewer", "today", "{}", "today", "today"),
    )
    connection.execute(
        "INSERT INTO lead_accounts (id,brand_id,company_name,domain,website,country,category,stage,fit_score,review_status,reviewed_by,"
        "reviewed_at,outreach_status,outreach_approved_by,outreach_approved_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        ("lead-1", "jade", "Northwind Jewellers", "northwind.example", "https://northwind.example", "SG", "jewelry_store",
         "qualified", 90, "approved", "Reviewer", "today", outreach_status, "Reviewer", "today"),
    )
    connection.execute(
        "INSERT INTO lead_locations (id,lead_id,external_place_id,name,category,location,country,url,confidence,raw_record) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        ("location-1", "lead-1", "place-1", "Northwind Jewellers", "jewelry_store", "Singapore", "SG",
         "https://northwind.example", 0.9, json.dumps({"taxonomy": {"hierarchy": ["shopping", "jewelry_store"]}})),
    )


def _low_fit_site():
    return {"ok": False, "error": "HTTP_404", "text": "", "title": "", "description": "", "emails": [],
            "phones": [], "services": [], "socials": [], "pages": []}


def _enrich_lead():
    lead_pipeline.enrich_location_job({"lead_id": "lead-1", "payload": json.dumps({"location_id": "location-1"})})


def test_enrichment_revokes_approval_when_fit_evidence_is_lost(lead_database):
    _seed_approved_lead(lead_database)
    with patch.object(lead_pipeline, "verify_website", return_value=_low_fit_site()):
        _enrich_lead()
    lead = lead_database.execute("SELECT status,review_status,outreach_status FROM leads WHERE id=%s", ("lead-1",)).fetchone()
    assert lead == {"status": "possible", "review_status": "pending", "outreach_status": "not_approved"}


def test_enrichment_preserves_a_concurrent_rejection(lead_database):
    _seed_approved_lead(lead_database)

    def reject_during_fetch(_url):
        lead_database.execute(
            "UPDATE leads SET review_status='rejected', reviewed_by='Human', outreach_status='not_approved', "
            "outreach_approved_by=NULL,outreach_approved_at=NULL WHERE id=%s", ("lead-1",),
        )
        lead_database.execute(
            "UPDATE lead_accounts SET review_status='rejected', reviewed_by='Human', outreach_status='not_approved', "
            "outreach_approved_by=NULL,outreach_approved_at=NULL WHERE id=%s", ("lead-1",),
        )
        return _low_fit_site()

    with patch.object(lead_pipeline, "verify_website", side_effect=reject_during_fetch):
        _enrich_lead()
    lead = lead_database.execute("SELECT review_status,reviewed_by,outreach_status FROM leads WHERE id=%s", ("lead-1",)).fetchone()
    assert lead == {"review_status": "rejected", "reviewed_by": "Human", "outreach_status": "not_approved"}


def test_enrichment_preserves_sent_and_uncertain_outreach(lead_database):
    for status in ("sent", "sending", "delivery_uncertain"):
        lead_database.execute("DELETE FROM leads")
        lead_database.execute("DELETE FROM lead_accounts")
        lead_database.execute("DELETE FROM lead_locations")
        _seed_approved_lead(lead_database, status)
        with patch.object(lead_pipeline, "verify_website", return_value=_low_fit_site()):
            _enrich_lead()
        row = lead_database.execute("SELECT outreach_status FROM leads WHERE id=%s", ("lead-1",)).fetchone()
        assert row["outreach_status"] == status


def test_enrichment_expires_contacts_missing_from_current_evidence(lead_database):
    _seed_approved_lead(lead_database)
    old_email = "old@northwind.example"
    lead_database.execute(
        "UPDATE leads SET email=%s,public_email=%s WHERE id=%s", (old_email, old_email, "lead-1"),
    )
    lead_pipeline._add_contact(
        lead_database, "lead-1", "location-1", "email", old_email,
        "company_website", "https://northwind.example/contact", 1.0, "published",
    )
    with patch.object(lead_pipeline, "verify_website", return_value=_low_fit_site()):
        _enrich_lead()

    lead = lead_database.execute("SELECT email,public_email FROM leads WHERE id=%s", ("lead-1",)).fetchone()
    contact = lead_database.execute(
        "SELECT verification_status FROM lead_contacts WHERE lead_id=%s AND value=%s",
        ("lead-1", old_email),
    ).fetchone()
    assert lead == {"email": None, "public_email": None}
    assert contact["verification_status"] == "stale"


def _candidate(category="jewelry_store", email=None):
    return {
        "brand_id": "jade", "source": "overture_maps", "external_place_id": "place-1",
        "name": "Northwind Jewellers", "category": category, "location": "Singapore", "country": "SG",
        "url": "https://northwind.example", "domain": "northwind.example", "email": email,
        "phone": None, "operating_status": None, "confidence": 0.9,
        "source_provider": "overture", "source_release": "2026-09-23.0",
        "raw_record": {"taxonomy": {"hierarchy": ["shopping", category]}},
    }


def test_discovery_provenance_does_not_link_dataset_fields_to_business_website(lead_database):
    candidate = {**_candidate(email="info@northwind.example"), "phone": "+65 6123 4567",
                 "social_links": ["https://instagram.com/northwind"]}
    lead_id = lead_pipeline.persist_candidate(candidate)
    location_id = lead_database.execute(
        "SELECT id FROM lead_locations WHERE lead_id=%s", (lead_id,),
    ).fetchone()["id"]
    lead_pipeline._add_evidence(
        lead_database, lead_id, "business_name", candidate["name"], "overture_maps",
        candidate["url"], candidate["confidence"], location_id,
    )
    lead_database.execute(
        "UPDATE lead_source_records SET source_url=%s WHERE lead_id=%s", (candidate["url"], lead_id),
    )
    lead_database.execute(
        "UPDATE lead_contacts SET source_url=%s WHERE lead_id=%s", (candidate["url"], lead_id),
    )
    lead_pipeline.persist_candidate(candidate)
    rows = lead_database.execute(
        "SELECT evidence_type,value,source_url FROM lead_evidence WHERE lead_id=%s", (lead_id,),
    ).fetchall()
    evidence = {(row["evidence_type"], row["value"]): row["source_url"] for row in rows}
    assert evidence[("business_name", "Northwind Jewellers")] is None
    assert evidence[("website", "https://northwind.example")] is None
    assert evidence[("email", "info@northwind.example")] is None
    assert evidence[("phone", "+65 6123 4567")] is None
    assert evidence[("social_url", "https://instagram.com/northwind")] is None
    source = lead_database.execute(
        "SELECT source,release,source_url FROM lead_source_records WHERE lead_id=%s", (lead_id,),
    ).fetchone()
    assert source == {"source": "overture_maps", "release": "2026-09-23.0", "source_url": None}
    contact = lead_database.execute(
        "SELECT source_url FROM lead_contacts WHERE lead_id=%s AND contact_type='email'", (lead_id,),
    ).fetchone()
    assert contact["source_url"] is None


def test_source_import_revokes_approval_before_enrichment_is_queued(lead_database):
    _seed_approved_lead(lead_database)
    assert lead_pipeline.persist_candidate(_candidate(category="medical_clinic", email="info@northwind.example")) == "lead-1"

    lead = lead_database.execute(
        "SELECT review_status,reviewed_by,outreach_status,outreach_approved_by,review_note FROM leads WHERE id=%s",
        ("lead-1",),
    ).fetchone()
    account = lead_database.execute(
        "SELECT review_status,outreach_status,outreach_approved_by FROM lead_accounts WHERE id=%s", ("lead-1",),
    ).fetchone()
    job = lead_database.execute("SELECT status FROM lead_jobs WHERE lead_id=%s", ("lead-1",)).fetchone()
    assert lead == {
        "review_status": "pending", "reviewed_by": None, "outreach_status": "not_approved",
        "outreach_approved_by": None, "review_note": "Source data changed; human review is required again.",
    }
    assert account == {"review_status": "pending", "outreach_status": "not_approved", "outreach_approved_by": None}
    assert job == {"status": "pending"}


def test_unchanged_source_import_preserves_approval(lead_database):
    _seed_approved_lead(lead_database)
    generated_location_id = lead_pipeline._location_id("lead-1", "place-1", "Northwind Jewellers", "Singapore")
    lead_database.execute("UPDATE lead_locations SET id=%s WHERE id=%s", (generated_location_id, "location-1"))
    lead_pipeline.persist_candidate(_candidate())
    lead = lead_database.execute(
        "SELECT review_status,reviewed_by,outreach_status,outreach_approved_by FROM leads WHERE id=%s", ("lead-1",),
    ).fetchone()
    assert lead == {
        "review_status": "approved", "reviewed_by": "Reviewer", "outreach_status": "approved",
        "outreach_approved_by": "Reviewer",
    }


def test_source_refresh_clears_a_removed_website(lead_database):
    candidate = _candidate(email="info@northwind.example")
    lead_id = lead_pipeline.persist_candidate(candidate)
    lead_pipeline.persist_candidate({**candidate, "url": None, "domain": None, "email": None})
    lead = lead_database.execute("SELECT url,domain FROM leads WHERE id=%s", (lead_id,)).fetchone()
    location = lead_database.execute("SELECT url,email FROM lead_locations WHERE lead_id=%s", (lead_id,)).fetchone()
    account = lead_database.execute("SELECT website,domain FROM lead_accounts WHERE id=%s", (lead_id,)).fetchone()
    assert lead == {"url": None, "domain": None}
    assert location == {"url": None, "email": None}
    assert account == {"website": None, "domain": None}


@pytest.mark.parametrize("phone", [None, "+65 6123 4567"])
def test_outlets_without_a_website_resolve_to_one_company_account(lead_database, phone):
    first = _candidate()
    first.update({
        "external_place_id": "place-orchard", "name": "Northwind Jewellers - Orchard", "location": "Orchard",
        "url": None, "domain": None, "phone": phone,
    })
    second = {**first}
    second.update({
        "external_place_id": "place-marina", "name": "Northwind Jewellers - Marina Bay", "location": "Marina Bay",
        "country": "SG", "source_release": "2026-09-23.0",
    })
    first_account = lead_pipeline.persist_candidate(first)
    second_account = lead_pipeline.persist_candidate(second)

    assert first_account == second_account
    assert lead_database.execute("SELECT COUNT(*) AS total FROM leads").fetchone()["total"] == 1
    assert lead_database.execute("SELECT COUNT(*) AS total FROM lead_locations").fetchone()["total"] == 2
    account = lead_database.execute("SELECT name,location,domain FROM leads").fetchone()
    assert account == {"name": "Northwind Jewellers - Orchard", "location": "Orchard", "domain": None}


def test_initial_discovery_runs_when_release_marker_exists_without_scrape_checkpoint(lead_database, monkeypatch, tmp_path):
    state_path = tmp_path / "lead-refresh.json"
    state_path.write_text(json.dumps({
        "release": "2026-09-23.0",
        "changelog_release": "2026-09-23.0",
        "last_release_checked_at": "2026-09-24T05:22:24+00:00",
    }))
    monkeypatch.setattr(lead_pipeline, "STATE_PATH", state_path)
    monkeypatch.setattr(lead_pipeline, "latest_release", lambda: "2026-09-23.0")
    monkeypatch.setattr(lead_pipeline, "_hunter_discovery_due", lambda: False)
    queried_releases = []
    queried_countries = []

    def query_country(release, *, country):
        queried_releases.append(release)
        queried_countries.append(country)
        return []

    monkeypatch.setattr(
        lead_pipeline, "overture_candidates", query_country,
    )

    result = lead_pipeline.refresh()

    state = json.loads(state_path.read_text())
    assert queried_releases == ["2026-09-23.0"] * len(load_config()["countries"])
    assert queried_countries == load_config()["countries"]
    assert result["overture_attempted"] is True
    assert state["release"] == "2026-09-23.0"
    assert state["last_scraped_at"]


def test_discovery_persists_each_country_batch_before_querying_next(lead_database, monkeypatch, tmp_path):
    state_path = tmp_path / "lead-refresh.json"
    state_path.write_text(json.dumps({
        "release": "2026-09-23.0",
        "changelog_release": "2026-09-23.0",
    }))
    monkeypatch.setattr(lead_pipeline, "STATE_PATH", state_path)
    monkeypatch.setattr(lead_pipeline, "latest_release", lambda: "2026-09-23.0")
    monkeypatch.setattr(lead_pipeline, "_hunter_discovery_due", lambda: False)
    queried_countries = []

    def query_country(_release, *, country):
        queried_countries.append(country)
        if country == "SG":
            return [_candidate()]
        if country == "MY":
            count = lead_database.execute("SELECT COUNT(*) AS total FROM leads").fetchone()["total"]
            assert count == 1
        return []

    monkeypatch.setattr(lead_pipeline, "overture_candidates", query_country)

    result = lead_pipeline.discover_and_enrich()

    assert queried_countries == load_config()["countries"]
    assert result["discovered"] == 1
    assert result["accounts"] == 1
    assert json.loads(state_path.read_text())["updated"] == 1


def test_scheduler_treats_missing_scrape_checkpoint_as_stale(monkeypatch):
    monkeypatch.setattr(lead_pipeline, "_state", lambda: {
        "release": "2026-09-23.0",
        "last_release_checked_at": "2026-09-24T05:22:24+00:00",
    })

    assert lead_pipeline._is_stale() is True


def test_scheduler_honors_initial_discovery_retry_backoff(monkeypatch):
    now = lead_pipeline.datetime.now(lead_pipeline.timezone.utc)
    state = {
        "release": "2026-09-23.0",
        "discovery_retry_pending": True,
        "discovery_retry_at": (now + lead_pipeline.timedelta(hours=1)).isoformat(),
    }
    monkeypatch.setattr(lead_pipeline, "_state", lambda: state)

    assert lead_pipeline._is_stale() is False

    state["discovery_retry_at"] = (now - lead_pipeline.timedelta(seconds=1)).isoformat()
    assert lead_pipeline._is_stale() is True


def test_hunter_retry_is_independent_of_overture_release(lead_database, monkeypatch, tmp_path):
    now = lead_pipeline.datetime(2026, 9, 24, 12, 0, tzinfo=lead_pipeline.timezone.utc)
    monkeypatch.setenv("HUNTER_API_KEY", "configured")
    monkeypatch.setattr(lead_pipeline, "_state", lambda: {
        "release": "2026-09-23.0", "hunter_period": "2026-09", "hunter_retry_pending": True,
        "hunter_last_attempt_at": "2026-09-24T03:00:00+00:00",
        "last_scraped_at": "2026-09-23T00:00:00+00:00",
    })
    monkeypatch.setattr(lead_pipeline, "STATE_PATH", tmp_path / "lead-refresh.json")
    assert lead_pipeline._hunter_discovery_due(now) is True
    assert lead_pipeline._hunter_discovery_due(now.replace(hour=8)) is False

    hunter_calls = []
    monkeypatch.setattr(lead_pipeline, "latest_release", lambda: "2026-09-23.0")
    monkeypatch.setattr(lead_pipeline, "_hunter_discovery_due", lambda: True)
    monkeypatch.setattr(lead_pipeline, "overture_candidates", lambda *_: (_ for _ in ()).throw(AssertionError("Overture should not be queried")))
    monkeypatch.setattr(lead_pipeline, "hunter_discover_candidates", lambda: (hunter_calls.append(True) or [], ["Hunter Discover unavailable"]))
    monkeypatch.setattr(lead_pipeline, "process_pending_jobs", lambda **_kwargs: (0, []))

    result = lead_pipeline.discover_and_enrich()
    assert hunter_calls == [True]
    assert result["overture_attempted"] is False
    assert result["hunter_attempted"] is True
    assert result["checkpoint_complete"] is True
    assert result["hunter_checkpoint_complete"] is False


def test_changelog_invalidates_approvals_but_preserves_rejection_and_sent_state(lead_database, monkeypatch):
    class FakeDuckDBConnection:
        def execute(self, query, _params=None):
            self.query = query
            return self

        def executemany(self, _query, _params):
            pass

        def fetchall(self):
            if "SELECT c.id" in self.query:
                return [("place-1", "data_changed", ["emails"])]
            return []

        def close(self):
            pass

    monkeypatch.setitem(sys.modules, "duckdb", SimpleNamespace(connect=lambda **_kwargs: FakeDuckDBConnection()))
    previous_release = "2026-08-19.0"
    monkeypatch.setattr(lead_pipeline, "_release_parent", lambda _release: previous_release)
    _seed_approved_lead(lead_database)
    result = lead_pipeline._apply_changelog("2026-09-23.0", previous_release)
    approved = lead_database.execute(
        "SELECT review_status,outreach_status,reviewed_by FROM leads WHERE id=%s", ("lead-1",),
    ).fetchone()
    assert result == {"removed": 0, "changed": 1, "complete": True}
    assert approved == {"review_status": "pending", "outreach_status": "not_approved", "reviewed_by": None}

    lead_database.execute("DELETE FROM leads")
    lead_database.execute("DELETE FROM lead_accounts")
    lead_database.execute("DELETE FROM lead_locations")
    _seed_approved_lead(lead_database)
    lead_database.execute(
        "UPDATE leads SET review_status='rejected',reviewed_by='Human',review_note='Do not contact',outreach_status='not_approved' WHERE id=%s",
        ("lead-1",),
    )
    lead_database.execute(
        "UPDATE lead_accounts SET review_status='rejected',reviewed_by='Human',review_note='Do not contact',outreach_status='not_approved' WHERE id=%s",
        ("lead-1",),
    )
    lead_pipeline._apply_changelog("2026-09-23.0", previous_release)
    rejected = lead_database.execute(
        "SELECT review_status,outreach_status,reviewed_by,review_note FROM leads WHERE id=%s", ("lead-1",),
    ).fetchone()
    assert rejected == {
        "review_status": "rejected", "outreach_status": "not_approved", "reviewed_by": "Human", "review_note": "Do not contact",
    }

    lead_database.execute("DELETE FROM leads")
    lead_database.execute("DELETE FROM lead_accounts")
    lead_database.execute("DELETE FROM lead_locations")
    _seed_approved_lead(lead_database, "sent")
    lead_pipeline._apply_changelog("2026-09-23.0", previous_release)
    sent = lead_database.execute(
        "SELECT review_status,outreach_status,reviewed_by FROM leads WHERE id=%s", ("lead-1",),
    ).fetchone()
    assert sent == {"review_status": "approved", "outreach_status": "sent", "reviewed_by": "Reviewer"}


def test_changelog_read_failure_remains_retryable(lead_database, monkeypatch):
    class BrokenDuckDBConnection:
        def execute(self, query, _params=None):
            if "SELECT c.id" in query:
                raise OSError("storage unavailable")
            return self

        def executemany(self, _query, _params):
            pass

        def close(self):
            pass

    monkeypatch.setitem(sys.modules, "duckdb", SimpleNamespace(connect=lambda **_kwargs: BrokenDuckDBConnection()))
    previous_release = "2026-08-19.0"
    monkeypatch.setattr(lead_pipeline, "_release_parent", lambda _release: previous_release)
    _seed_approved_lead(lead_database)
    result = lead_pipeline._apply_changelog("2026-09-23.0", previous_release)
    assert result == {"removed": 0, "changed": 0, "complete": False}


def test_missed_release_reconciles_tracked_places_against_latest_snapshot(lead_database, monkeypatch):
    columns = [
        "id", "name", "basic_category", "taxonomy_primary", "taxonomy_hierarchy", "taxonomy_alternates",
        "operating_status", "confidence", "websites", "emails", "phones", "socials", "addresses", "sources", "bbox",
    ]
    current = (
        "place-1", "Northwind Jewellers", "jewelry_store", "jewelry_store", ["shopping", "jewelry_store"], [],
        "open", 0.95, ["https://northwind.example"], ["info@northwind.example"], ["+6561234567"], [],
        [{"freeform": "Singapore", "locality": "Singapore", "region": "", "country": "SG"}],
        [{"dataset": "overture", "provider": "test"}], {"xmin": 103.7, "xmax": 103.9, "ymin": 1.2, "ymax": 1.4},
    )

    class SnapshotDuckDBConnection:
        def execute(self, query, _params=None):
            self.query = query
            self.description = [(name,) for name in columns] if "FROM read_parquet" in query else []
            self.rows = [current] if "FROM read_parquet" in query else []
            return self

        def executemany(self, _query, _params):
            pass

        def fetchall(self):
            return self.rows

        def close(self):
            pass

    monkeypatch.setitem(sys.modules, "duckdb", SimpleNamespace(connect=lambda **_kwargs: SnapshotDuckDBConnection()))
    monkeypatch.setattr(lead_pipeline, "_duckdb_connection", lambda _duckdb: SnapshotDuckDBConnection())
    monkeypatch.setattr(lead_pipeline, "_release_parent", lambda _release: "2026-08-19.0")
    _seed_approved_lead(lead_database)

    result = lead_pipeline._apply_changelog("2026-09-23.0", "2026-07-22.0")
    location = lead_database.execute(
        "SELECT status FROM lead_locations WHERE id=%s", ("location-1",),
    ).fetchone()
    lead = lead_database.execute(
        "SELECT review_status,outreach_status,stage FROM leads WHERE id=%s", ("lead-1",),
    ).fetchone()
    assert result == {"removed": 0, "changed": 1, "complete": True}
    assert location["status"] == "needs_reverify"
    assert lead == {"review_status": "pending", "outreach_status": "not_approved", "stage": "needs_reverification"}


def test_refresh_catalog_failure_persists_a_short_retry(monkeypatch, tmp_path):
    state_path = tmp_path / "lead-refresh.json"
    monkeypatch.setattr(lead_pipeline, "STATE_PATH", state_path)
    monkeypatch.setattr(
        lead_pipeline, "latest_release",
        lambda: (_ for _ in ()).throw(LeadPipelineError("SOURCE_UNAVAILABLE", "catalog unavailable", True)),
    )
    result = lead_pipeline.refresh()
    state = json.loads(state_path.read_text())
    assert result["last_error"].startswith("SOURCE_UNAVAILABLE")
    assert lead_pipeline.get_status()["refreshing"] is False
    assert state["discovery_retry_pending"] is True
    assert lead_pipeline.datetime.fromisoformat(state["discovery_retry_at"]) > lead_pipeline.datetime.now(lead_pipeline.timezone.utc)


def test_refresh_failure_preserves_pending_website_jobs(lead_database, monkeypatch, tmp_path):
    state_path = tmp_path / "lead-refresh.json"
    monkeypatch.setattr(lead_pipeline, "STATE_PATH", state_path)
    lead_database.execute(
        "INSERT INTO lead_jobs (id, stage, status) VALUES (%s, %s, %s)",
        ("still-pending", "website_verify", "pending"),
    )
    monkeypatch.setattr(
        lead_pipeline, "latest_release",
        lambda: (_ for _ in ()).throw(LeadPipelineError("SOURCE_UNAVAILABLE", "catalog unavailable", True)),
    )

    result = lead_pipeline.refresh()

    assert result["pending_jobs"] == 1
    assert json.loads(state_path.read_text())["pending_jobs"] == 1


def test_sqlite_schema_initialization_runs_once_per_database(monkeypatch, tmp_path):
    import db as database

    monkeypatch.setenv("DB_ENGINE", "sqlite")
    monkeypatch.delenv("MYSQL_HOST", raising=False)
    monkeypatch.setattr(database, "SQLITE_DB_PATH", tmp_path / "aura.db")
    monkeypatch.setattr(database, "_SQLITE_INITIALIZED_PATHS", set())
    original_init = database.init_sqlite_db
    calls = []

    def tracked_init(connection):
        calls.append(True)
        original_init(connection)

    monkeypatch.setattr(database, "init_sqlite_db", tracked_init)
    with database.get_db():
        pass
    with database.get_db():
        pass

    assert calls == [True]


def test_changelog_failure_does_not_block_overture_checkpoint(lead_database, monkeypatch, tmp_path):
    state_path = tmp_path / "lead-refresh.json"
    state_path.write_text(json.dumps({
        "release": "2026-08-19.0", "changelog_release": "2026-08-19.0",
        "last_scraped_at": "2026-08-20T00:00:00+00:00",
    }))
    monkeypatch.setattr(lead_pipeline, "STATE_PATH", state_path)
    monkeypatch.setattr(lead_pipeline, "latest_release", lambda: "2026-09-23.0")
    monkeypatch.setattr(lead_pipeline, "_apply_changelog", lambda _release, _previous=None: {"removed": 0, "changed": 0, "complete": False})
    monkeypatch.setattr(lead_pipeline, "overture_candidates", lambda _release, **_kwargs: [])
    monkeypatch.setattr(lead_pipeline, "_hunter_discovery_due", lambda: False)
    monkeypatch.setattr(
        lead_pipeline, "process_pending_jobs",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("website verification must run in its own worker")),
    )
    pending_before = lead_database.execute("SELECT COUNT(*) AS total FROM lead_jobs WHERE status='pending'").fetchone()["total"]

    result = lead_pipeline.refresh()
    state = json.loads(state_path.read_text())
    assert result["release"] == "2026-09-23.0"
    assert result["checkpoint_complete"] is True
    assert result["enriched"] == 0
    assert result["pending_jobs"] == pending_before
    assert result["changelog_complete"] is False
    assert state["release"] == "2026-09-23.0"
    assert state["changelog_release"] == "2026-08-19.0"
    assert state["changelog_retry_release"] == "2026-09-23.0"
    assert state["changelog_retry_pending"] is True

    retry_at = lead_pipeline.datetime.fromisoformat(state["changelog_retry_at"])
    assert lead_pipeline._changelog_retry_due(retry_at + lead_pipeline.timedelta(seconds=1)) is True


def test_checked_url_rejects_private_dns_answers(monkeypatch):
    monkeypatch.setattr(
        "agents.lead_pipeline.socket.getaddrinfo",
        lambda *_args, **_kwargs: [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, "", ("127.0.0.1", 80))],
    )
    try:
        _checked_url("http://business.example")
    except LeadPipelineError as exc:
        assert exc.code == "UNSAFE_URL"
    else:
        raise AssertionError("private DNS results must be rejected")


def test_safe_fetch_uses_the_checked_ip_and_original_host_header(monkeypatch):
    seen_hosts = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            seen_hosts.append(self.headers.get("Host"))
            body = b"<html><body>verified</body></html>"
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *_args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_port
    address = (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, ("127.0.0.1", port), "93.184.216.34")
    monkeypatch.setattr(
        "agents.lead_pipeline._checked_url",
        lambda url: (f"http://business.example:{port}/", "business.example", port, [address]),
    )
    monkeypatch.setattr("agents.lead_pipeline._respect_host_delay", lambda _host: None)
    monkeypatch.setattr("agents.lead_pipeline.socket.getaddrinfo", lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("unexpected DNS lookup")))
    try:
        body, final_url, status = _safe_fetch(f"http://business.example:{port}/")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert status == 200
    assert final_url == f"http://business.example:{port}/"
    assert "verified" in body
    assert seen_hosts == [f"business.example:{port}"]


def test_safe_fetch_checks_destination_robots_before_following_redirect(monkeypatch):
    destination_requests = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            destination_requests.append(self.path)
            self.send_response(302)
            self.send_header("Location", "https://blocked.example/contact")
            self.end_headers()

        def log_message(self, *_args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    port = server.server_port
    address = (socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP, ("127.0.0.1", port), "93.184.216.34")

    def checked(url):
        if "blocked.example" in url:
            raise AssertionError("blocked redirect target must not be fetched")
        return f"http://business.example:{port}/", "business.example", port, [address]

    monkeypatch.setattr("agents.lead_pipeline._checked_url", checked)
    monkeypatch.setattr("agents.lead_pipeline._respect_host_delay", lambda _host: None)
    try:
        with pytest.raises(LeadPipelineError, match="robots.txt") as caught:
            _safe_fetch(
                f"http://business.example:{port}/",
                robots_check=lambda target: "blocked.example" not in target,
            )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

    assert caught.value.code == "ROBOTS_BLOCKED"
    assert destination_requests == ["/"]


def test_website_extractor_keeps_contact_page_provenance(monkeypatch):
    homepage = """<html><head><title>Northwind</title></head><body>
      <a href="/contact">Contact</a><p>Independent jeweller in Singapore.</p>
    </body></html>"""
    contact = """<html><head><title>Contact</title></head><body>
      <script type="application/ld+json">{
        "@type":"JewelryStore","name":"Northwind Jewellers",
        "description":"Diamond and gold jewellery services",
        "email":"sales@northwind.example","telephone":"+65 6123 4567",
        "sameAs":["https://instagram.com/northwind"],"knowsAbout":["Diamond resizing"]
      }</script>
    </body></html>"""

    class AllowAllRobots:
        def can_fetch(self, _agent, _url):
            return True

    def fetch(url, **_kwargs):
        robots_check = _kwargs.get("robots_check")
        if robots_check:
            assert robots_check(url)
        if url.rstrip("/").endswith("/contact"):
            final_url = "https://northwind.example/contact"
            assert not robots_check or robots_check(final_url)
            return contact, final_url, 200
        if url.rstrip("/") == "https://northwind.example":
            final_url = "https://northwind.example/"
            assert not robots_check or robots_check(final_url)
            return homepage, final_url, 200
        raise LeadPipelineError("HTTP_404", "not found")

    monkeypatch.setattr(lead_pipeline, "_checked_url", lambda url: (url, "northwind.example", 443, []))
    monkeypatch.setattr(lead_pipeline, "_robots_parser", lambda _url: AllowAllRobots())
    monkeypatch.setattr(lead_pipeline, "_sitemap_urls", lambda *_args: [])
    monkeypatch.setattr(lead_pipeline, "_safe_fetch", fetch)

    site = lead_pipeline.verify_website("https://northwind.example")
    contact_url = "https://northwind.example/contact"
    assert site["email_sources"]["sales@northwind.example"] == contact_url
    assert site["phone_sources"]["+65 6123 4567"] == contact_url
    assert site["service_sources"]["Diamond resizing"] == contact_url
    assert site["social_sources"]["https://instagram.com/northwind"] == contact_url
    assert site["description_source"] == contact_url
    assert site["name_source"] == contact_url


def test_enrichment_persists_contact_and_service_source_pages(lead_database):
    _seed_approved_lead(lead_database)
    contact_url = "https://northwind.example/contact"
    lead_pipeline._add_evidence(
        lead_database, "lead-1", "email", "sales@northwind.example", "company_website",
        "https://northwind.example/", 1.0, "location-1",
    )
    site = {
        "ok": True, "title": "Northwind Jewellers", "name": "Northwind Jewellers",
        "description": "Diamond and gold jewellery services", "description_source": contact_url,
        "name_source": contact_url, "text": "Diamond jewellery and gold services.",
        "page_texts": [{"url": contact_url, "text": "Diamond jewellery and gold services."}],
        "pages": ["https://northwind.example/", contact_url],
        "emails": ["sales@northwind.example"], "email_sources": {"sales@northwind.example": contact_url},
        "phones": ["+65 6123 4567"], "phone_sources": {"+65 6123 4567": contact_url},
        "services": ["Diamond resizing"], "service_sources": {"Diamond resizing": contact_url},
        "socials": ["https://instagram.com/northwind"],
        "social_sources": {"https://instagram.com/northwind": contact_url},
    }
    with patch.object(lead_pipeline, "verify_website", return_value=site), \
            patch.object(lead_pipeline, "email_mx_status", return_value="mx_valid"):
        _enrich_lead()

    evidence = lead_database.execute(
        "SELECT evidence_type,value,source_url FROM lead_evidence WHERE lead_id=%s", ("lead-1",),
    ).fetchall()
    by_type_and_value = {(item["evidence_type"], item["value"]): item["source_url"] for item in evidence}
    assert by_type_and_value[("email", "sales@northwind.example")] == contact_url
    assert [item["source_url"] for item in evidence
            if item["evidence_type"] == "email" and item["value"] == "sales@northwind.example"] == [contact_url]
    assert by_type_and_value[("phone", "+65 6123 4567")] == contact_url
    assert by_type_and_value[("service", "Diamond resizing")] == contact_url
    assert by_type_and_value[("social_url", "https://instagram.com/northwind")] == contact_url
    contact = lead_database.execute(
        "SELECT source_url FROM lead_contacts WHERE lead_id=%s AND contact_type='email' AND value=%s",
        ("lead-1", "sales@northwind.example"),
    ).fetchone()
    assert contact["source_url"] == contact_url


def test_lead_page_uses_keyset_cursor_without_duplicate_or_missing_rows(lead_database):
    rows = [
        ("lead-a", "jade", "Amber Jewellers", 94, "SG", "amber.example", "", ""),
        ("lead-b", "jade", "Blue Clinic", 91, "SG", "blue.example", "care@blue.example", ""),
        ("lead-c", "jaguar", "Cedar Freight", 91, "MY", "cedar.example", "", "+60 123"),
        ("lead-d", "jade", "Delta Clinic", 82, "TH", "delta.example", "", ""),
        ("lead-e", "jade", "Echo Medical", 79, "SG", "echo.example", "", ""),
    ]
    for lead_id, brand_id, name, score, country, domain, email, phone in rows:
        lead_database.execute(
            "INSERT INTO leads (id,brand_id,name,fit_score,country,domain,email,phone) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
            (lead_id, brand_id, name, score, country, domain, email, phone),
        )

    first = lead_pipeline.list_lead_page(limit=2)
    second = lead_pipeline.list_lead_page(limit=2, cursor=first["next_cursor"])
    third = lead_pipeline.list_lead_page(limit=2, cursor=second["next_cursor"])

    assert [row["id"] for row in first["items"]] == ["lead-a", "lead-b"]
    assert [row["id"] for row in second["items"]] == ["lead-c", "lead-d"]
    assert [row["id"] for row in third["items"]] == ["lead-e"]
    assert first["has_more"] is True
    assert third["has_more"] is False
    assert third["next_cursor"] is None


def test_lead_page_filters_on_database_and_rejects_cursor_for_other_filters(lead_database):
    rows = [
        ("lead-a", "jade", "Amber Jewellers", 94, "amber.example", "", ""),
        ("lead-b", "jade", "Blue Clinic", 91, "blue.example", "care@blue.example", ""),
        ("lead-c", "jaguar", "Cedar Freight", 91, "cedar.example", "", "+60 123"),
    ]
    for lead_id, brand_id, name, score, domain, email, phone in rows:
        lead_database.execute(
            "INSERT INTO leads (id,brand_id,name,fit_score,domain,email,phone) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (lead_id, brand_id, name, score, domain, email, phone),
        )

    page = lead_pipeline.list_lead_page(brand_id="jade", search="blu", contact="email", limit=1)
    assert [row["id"] for row in page["items"]] == ["lead-b"]
    assert page["has_more"] is False
    cursor = lead_pipeline.list_lead_page(limit=1)["next_cursor"]
    with pytest.raises(ValueError, match="different filters"):
        lead_pipeline.list_lead_page(brand_id="jade", limit=1, cursor=cursor)


def test_lead_page_rejects_invalid_cursor_and_limits(lead_database):
    with pytest.raises(ValueError, match="cursor is invalid"):
        lead_pipeline.list_lead_page(cursor="not-a-cursor")
    with pytest.raises(ValueError, match="page size"):
        lead_pipeline.list_lead_page(limit=101)


def test_lead_page_orderings_have_matching_database_indexes(lead_database):
    fit_plan = lead_database.execute(
        "EXPLAIN QUERY PLAN SELECT id FROM leads ORDER BY fit_score DESC, name ASC, id ASC LIMIT %s", (41,),
    ).fetchall()
    brand_fit_plan = lead_database.execute(
        "EXPLAIN QUERY PLAN SELECT id FROM leads WHERE brand_id=%s ORDER BY fit_score DESC, name ASC, id ASC LIMIT %s",
        ("jade", 41),
    ).fetchall()
    name_plan = lead_database.execute(
        "EXPLAIN QUERY PLAN SELECT id FROM leads ORDER BY name ASC, id ASC LIMIT %s", (41,),
    ).fetchall()
    brand_name_plan = lead_database.execute(
        "EXPLAIN QUERY PLAN SELECT id FROM leads WHERE brand_id=%s ORDER BY name ASC, id ASC LIMIT %s",
        ("jade", 41),
    ).fetchall()
    assert any("idx_leads_page_fit" in row["detail"] for row in fit_plan)
    assert any("idx_leads_page_brand_fit" in row["detail"] for row in brand_fit_plan)
    assert any("idx_leads_page_name" in row["detail"] for row in name_plan)
    assert any("idx_leads_page_brand_name" in row["detail"] for row in brand_name_plan)


def test_lead_page_adapter_uses_bounded_pipeline_page():
    expected = {"items": [{"id": "lead-1", "brand_id": "jade"}], "has_more": False, "next_cursor": None, "limit": 25}
    with patch.object(lead_intel.lead_pipeline, "list_lead_page", return_value=expected):
        assert lead_intel.load_lead_page(brand_id="jade", limit=25) == expected


def test_lead_route_returns_cursor_page_and_forwards_filters(monkeypatch):
    from routes import leads as lead_routes

    captured = {}
    expected = {"items": [], "has_more": True, "next_cursor": "next-page", "limit": 25}
    monkeypatch.setattr(lead_routes, "key_configured", lambda: True)

    def load_page(**filters):
        captured.update(filters)
        return expected

    monkeypatch.setattr(lead_routes, "load_lead_page", load_page)
    page = lead_routes.list_leads("jade", "north", "email", "name", 25, "current-page")

    assert page.items == []
    assert page.has_more is True
    assert page.next_cursor == "next-page"
    assert captured == {
        "brand_id": "jade", "search": "north", "contact": "email", "sort": "name",
        "limit": 25, "cursor": "current-page",
    }
