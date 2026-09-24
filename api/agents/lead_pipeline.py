"""Evidence-backed lead discovery and enrichment using Overture Maps Places."""

from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import os
import re
import socket
import time
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parseaddr
from functools import lru_cache
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

try:
    from ..db import get_connection
except ImportError:
    from db import get_connection

logger = logging.getLogger("aura.lead_pipeline")

ROOT = Path(__file__).resolve().parents[2]
ICP_CONFIG_PATH = ROOT / "api" / "config" / "lead_icps.json"
STATE_PATH = ROOT / ".aura" / "lead-refresh.json"
OVERTURE_STAC = "https://stac.overturemaps.org/catalog.json"
OVERTURE_S3 = "s3://overturemaps-us-west-2"
USER_AGENT = "AURA-LeadIntelligence/1.0 (+public business website verification)"
SCORE_VERSION = "2026-09-23.1"
MAX_PAGE_BYTES = 1_500_000
MAX_SITE_PAGES = 6
MAX_JOB_ATTEMPTS = 4
RETRY_DELAYS = (30, 300, 3600)
_RUN_LOCK = __import__("threading").Lock()
_RUNNING = False
_PUBLIC_SUFFIXES = {
    "co.uk", "org.uk", "ac.uk", "com.sg", "com.my", "com.hk", "com.id",
    "co.id", "co.th", "com.th", "com.au", "com.in", "co.in", "com.cn",
    "co.jp", "com.ph", "com.vn", "com.tw", "com.br", "com.mx",
}


class LeadPipelineError(RuntimeError):
    def __init__(self, code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@lru_cache(maxsize=1)
def load_config() -> dict:
    return json.loads(ICP_CONFIG_PATH.read_text(encoding="utf-8"))


def _state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(**values) -> dict:
    state = {**_state(), **values}
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state), encoding="utf-8")
    return state


def get_status() -> dict:
    state = _state()
    return {
        "refreshing": _RUNNING,
        "configured": True,
        "source": "Overture Maps Places",
        "release": state.get("release"),
        "last_scraped_at": state.get("last_scraped_at"),
        "last_error": state.get("last_error"),
        "updated": state.get("updated", 0),
        "watched": len(load_config()["brands"]),
        "pending_jobs": state.get("pending_jobs", 0),
    }


def latest_release() -> str:
    try:
        response = httpx.get(OVERTURE_STAC, timeout=15, follow_redirects=True)
        response.raise_for_status()
        version = str(response.json().get("latest") or "")
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}\.\d+", version):
            raise ValueError("Overture STAC catalog did not return a valid release")
        return version
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise LeadPipelineError("SOURCE_UNAVAILABLE", "Could not read the Overture release catalog.", True) from exc


def overture_candidates(release: str | None = None) -> list[dict]:
    """Query the current Overture Places GeoParquet with DuckDB and schema v2 fields."""
    try:
        import duckdb
    except ImportError as exc:
        raise LeadPipelineError("DUCKDB_MISSING", "Install the API dependency group to enable Overture discovery.") from exc

    config = load_config()
    release = release or latest_release()
    path = f"{OVERTURE_S3}/release/{release}/theme=places/type=place/*"
    rows: list[dict] = []
    con = duckdb.connect(database=":memory:")
    try:
        con.execute("INSTALL httpfs")
        con.execute("LOAD httpfs")
        con.execute("SET s3_region='us-west-2'")
        exact_by_brand = {brand: set(icp["exact_categories"]) for brand, icp in config["brands"].items()}
        hierarchy_by_brand = {brand: set(icp["hierarchy_categories"]) for brand, icp in config["brands"].items()}
        all_exact = sorted(set().union(*exact_by_brand.values()))
        all_hierarchy = sorted(set().union(*hierarchy_by_brand.values()))
        category_expr = [f"p.taxonomy.primary IN ({','.join('?' for _ in all_exact)})"]
        params: list[object] = list(all_exact)
        for category in all_hierarchy:
            category_expr.append("list_contains(p.taxonomy.hierarchy, ?)")
            params.append(category)
        sql = f"""
            SELECT p.id, p.names.primary AS name, p.basic_category,
                   p.taxonomy.primary AS taxonomy_primary,
                   p.taxonomy.hierarchy AS taxonomy_hierarchy,
                   p.operating_status, p.confidence,
                   p.websites, p.emails, p.phones, p.socials,
                   p.addresses, p.sources
            FROM read_parquet(?, hive_partitioning=1) AS p
            WHERE ({' OR '.join(category_expr)})
              AND (p.confidence IS NULL OR p.confidence >= ?)
              AND COALESCE(p.operating_status, '') != 'permanently_closed'
              AND list_contains(list_transform(p.addresses, a -> a.country), ?)
            ORDER BY p.confidence DESC NULLS LAST
            LIMIT ?
        """
        per_brand_limit = max(1, int(config.get("max_candidates_per_brand_run", 300)))
        for country in config["countries"]:
            result = con.execute(
                sql,
                [path, *params, float(config["minimum_overture_confidence"]), country, per_brand_limit * len(config["brands"])],
            )
            columns = [column[0] for column in result.description]
            for record in result.fetchall():
                item = dict(zip(columns, record))
                primary = str(item.get("taxonomy_primary") or "")
                hierarchy = set(item.get("taxonomy_hierarchy") or [])
                for brand_id in config["brands"]:
                    if primary in exact_by_brand[brand_id] or hierarchy.intersection(hierarchy_by_brand[brand_id]):
                        brand_item = {**item, "brand_id": brand_id, "country_filter": country, "source": "overture_maps"}
                        rows.append(_normalize_overture_record(brand_item, release))
    except LeadPipelineError:
        raise
    except Exception as exc:
        logger.exception("Overture discovery failed")
        raise LeadPipelineError("DISCOVERY_FAILED", "DuckDB could not query the current Overture Places release.", True) from exc
    finally:
        con.close()

    unique: dict[tuple[str, str], dict] = {}
    for row in rows:
        key = (row["brand_id"], row.get("external_place_id") or row.get("domain") or row["name"])
        unique[key] = row
    per_brand_limit = max(1, int(config.get("max_candidates_per_brand_run", 300)))
    grouped: dict[str, list[dict]] = {}
    for row in unique.values():
        grouped.setdefault(row["brand_id"], []).append(row)
    return [
        row
        for brand_rows in grouped.values()
        for row in sorted(brand_rows, key=lambda item: item.get("confidence") or 0, reverse=True)[:per_brand_limit]
    ]


def _normalize_overture_record(item: dict, release: str) -> dict:
    addresses = item.get("addresses") or []
    address = next((a for a in addresses if a.get("country")), addresses[0] if addresses else {}) or {}
    websites = item.get("websites") or []
    emails = item.get("emails") or []
    phones = item.get("phones") or []
    socials = item.get("socials") or []
    sources = item.get("sources") or []
    category = item.get("taxonomy_primary") or item.get("basic_category") or ""
    hierarchy = item.get("taxonomy_hierarchy") or []
    name = str(item.get("name") or "").strip()
    raw = {
        "id": str(item.get("id") or ""),
        "name": name,
        "basic_category": item.get("basic_category"),
        "taxonomy": {"primary": category, "hierarchy": list(hierarchy)},
        "operating_status": item.get("operating_status"),
        "confidence": item.get("confidence"),
        "websites": websites,
        "emails": emails,
        "phones": phones,
        "socials": socials,
        "addresses": addresses,
        "sources": sources,
    }
    website = next((str(u) for u in websites if _valid_site_url(str(u))), None)
    return {
        "brand_id": item["brand_id"],
        "source": item.get("source") or "overture_maps",
        "external_place_id": str(item.get("id") or ""),
        "name": name or "Unknown business",
        "category": category,
        "hierarchy": list(hierarchy),
        "location": address.get("freeform") or address.get("locality") or address.get("region") or "",
        "country": address.get("country") or item.get("country_filter") or "",
        "url": website,
        "domain": normalize_domain(website) if website else None,
        "email": _first_business_email(emails),
        "phone": next((str(p) for p in phones if p), None),
        "social_links": [str(value) for value in socials if value],
        "operating_status": item.get("operating_status"),
        "confidence": item.get("confidence"),
        "source_provider": (sources[0].get("dataset") or sources[0].get("provider") or "overture") if sources else "overture",
        "source_release": release,
        "raw_record": raw,
    }


def hunter_discover_candidates() -> tuple[list[dict], list[str]]:
    """Use Hunter's free filter-based Discover API as an optional secondary source."""
    key = (os.getenv("HUNTER_API_KEY") or "").strip()
    if not key or os.getenv("LEAD_HUNTER_DISCOVER_ENABLED", "true").lower() in {"0", "false", "no"}:
        return [], []
    config = load_config()
    release = "hunter-" + datetime.now(timezone.utc).strftime("%Y-%m")
    rows: list[dict] = []
    errors: list[str] = []
    for brand_id, icp in config["brands"].items():
        for country in config["countries"]:
            payload = {
                "headquarters_location": {"include": [{"country": country}]},
                "keywords": {"match": "any", "include": icp["keywords"][:100]},
            }
            try:
                response = httpx.post(
                    "https://api.hunter.io/v2/discover",
                    params={"api_key": key}, json=payload, timeout=20,
                )
                if response.status_code in {401, 403, 429}:
                    errors.append(f"Hunter Discover returned {response.status_code}")
                    continue
                response.raise_for_status()
                for company in (response.json().get("data") or [])[:100]:
                    domain = normalize_domain("https://" + str(company.get("domain") or ""))
                    if not domain:
                        continue
                    name = str(company.get("organization") or domain.split(".")[0].replace("-", " ").title())
                    website = "https://" + str(company.get("domain"))
                    raw = {"organization": company.get("organization"), "domain": company.get("domain"),
                           "emails_count": company.get("emails_count"), "filters": payload}
                    rows.append({
                        "brand_id": brand_id, "source": "hunter_discover", "external_place_id": "hunter:" + domain,
                        "name": name, "category": "hunter_discover_match", "hierarchy": [],
                        "location": country, "country": country, "url": website, "domain": domain,
                        "email": None, "phone": None, "social_links": [], "operating_status": None,
                        "confidence": None, "source_provider": "hunter", "source_release": release,
                        "raw_record": raw,
                    })
            except Exception as exc:
                errors.append(f"Hunter Discover {brand_id}/{country}: {exc.__class__.__name__}")
                # HTTP exception text can contain the API key query string.
                logger.info("Hunter Discover failed for %s %s (%s)", brand_id, country, exc.__class__.__name__)
    unique: dict[tuple[str, str], dict] = {}
    for row in rows:
        unique[(row["brand_id"], row["domain"])] = row
    return list(unique.values()), errors


def _valid_site_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in {"https", "http"} and bool(parsed.hostname) and not parsed.username and not parsed.password
    except ValueError:
        return False


def normalize_domain(url: str | None) -> str | None:
    if not url:
        return None
    try:
        candidate = url if "://" in url else "//" + url
        host = (urlparse(candidate).hostname or "").encode("idna").decode("ascii").lower().rstrip(".")
    except (ValueError, UnicodeError):
        return None
    if host.startswith("www."):
        host = host[4:]
    labels = host.split(".")
    if len(labels) < 2:
        return None
    suffix = ".".join(labels[-2:])
    keep = 3 if suffix in _PUBLIC_SUFFIXES and len(labels) > 2 else 2
    return ".".join(labels[-keep:])


def _first_business_email(values) -> str | None:
    for value in values or []:
        address = parseaddr(str(value))[1].strip().lower()
        if _email_syntax_ok(address) and not _personal_mail_domain(address):
            return address
    return None


def _personal_mail_domain(email: str) -> bool:
    domain = email.rsplit("@", 1)[-1].lower()
    return domain in {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "icloud.com"}


def _email_syntax_ok(email: str) -> bool:
    return bool(re.fullmatch(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,63}", email, re.I))


def _account_id(brand_id: str, domain: str | None, external_place_id: str) -> str:
    identity = f"domain:{domain}" if domain else f"place:{external_place_id}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"aura-lead:{brand_id}:{identity}"))


def _location_id(lead_id: str, external_place_id: str, name: str, location: str) -> str:
    identity = external_place_id or f"{name}:{location}"
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"aura-location:{lead_id}:{identity}"))


def _add_evidence(connection, lead_id: str, evidence_type: str, value: str | None,
                  source: str, source_url: str | None = None, confidence: float | None = None,
                  location_id: str | None = None) -> None:
    value = str(value or "").strip()
    if not value:
        return
    identity = "|".join((lead_id, location_id or "", evidence_type, value, source, source_url or ""))
    evidence_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"aura-evidence:{identity}"))
    exists = connection.execute("SELECT id FROM lead_evidence WHERE id = %s", (evidence_id,)).fetchone()
    if exists:
        connection.execute(
            "UPDATE lead_evidence SET confidence=%s, observed_at=%s WHERE id=%s",
            (confidence, _now(), evidence_id),
        )
        return
    connection.execute(
        "INSERT INTO lead_evidence (id, lead_id, location_id, evidence_type, value, source, source_url, confidence, observed_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (evidence_id, lead_id, location_id, evidence_type, value[:12000], source, source_url, confidence, _now()),
    )


def _add_contact(connection, lead_id: str, location_id: str | None, contact_type: str,
                 value: str | None, source: str, source_url: str | None,
                 confidence: float | None, verification_status: str = "unverified") -> None:
    value = str(value or "").strip()
    if not value:
        return
    contact_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"aura-contact:{lead_id}:{location_id or ''}:{contact_type}:{value.lower()}:{source}"))
    if connection.execute("SELECT id FROM lead_contacts WHERE id=%s", (contact_id,)).fetchone():
        connection.execute("UPDATE lead_contacts SET source_url=%s, verification_status=%s, confidence=%s, observed_at=%s WHERE id=%s",
                           (source_url, verification_status, confidence, _now(), contact_id))
        return
    connection.execute(
        "INSERT INTO lead_contacts (id, lead_id, location_id, contact_type, value, source, source_url, confidence, verification_status, observed_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (contact_id, lead_id, location_id, contact_type, value[:512], source, source_url, confidence, verification_status, _now()),
    )


def _add_source_record(connection, lead_id: str, location_id: str, candidate: dict) -> None:
    source_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"aura-source:{lead_id}:{candidate.get('external_place_id')}:{candidate.get('source_release')}"))
    raw_data = json.dumps(candidate.get("raw_record") or {}, ensure_ascii=False)
    if connection.execute("SELECT id FROM lead_source_records WHERE id=%s", (source_id,)).fetchone():
        connection.execute("UPDATE lead_source_records SET raw_data=%s, observed_at=%s WHERE id=%s", (raw_data, _now(), source_id))
        return
    connection.execute(
        "INSERT INTO lead_source_records (id, lead_id, location_id, source, source_record_id, release, source_url, raw_data, observed_at) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (source_id, lead_id, location_id, candidate.get("source") or "overture_maps", candidate.get("external_place_id") or candidate.get("domain") or candidate["name"],
         candidate.get("source_release"), candidate.get("url"), raw_data, _now()),
    )


def _sync_account(connection, lead_id: str, brand_id: str, name: str, domain: str | None,
                  website: str | None, country: str | None, category: str | None,
                  stage: str, score: int | None = None, score_version: str | None = None) -> None:
    row = connection.execute("SELECT id FROM lead_accounts WHERE id=%s", (lead_id,)).fetchone()
    if row:
        connection.execute(
            "UPDATE lead_accounts SET company_name=%s, domain=%s, website=COALESCE(%s,website), country=%s, category=%s, "
            "stage=CASE WHEN stage='qualified' AND %s='discovered' THEN stage ELSE %s END, "
            "fit_score=COALESCE(%s,fit_score), score_version=COALESCE(%s,score_version), updated_at=%s WHERE id=%s",
            (name, domain, website, country, category, stage, stage, score, score_version, _now(), lead_id),
        )
    else:
        connection.execute(
            "INSERT INTO lead_accounts (id, brand_id, company_name, domain, website, country, category, stage, fit_score, score_version, created_at, updated_at) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
            (lead_id, brand_id, name, domain, website, country, category, stage, score or 0, score_version, _now(), _now()),
        )


def _enqueue_enrichment(connection, lead_id: str, location_id: str, candidate: dict) -> None:
    job_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"aura-enrich:{candidate['source_release']}:{location_id}"))
    if connection.execute("SELECT id FROM lead_jobs WHERE id = %s", (job_id,)).fetchone():
        return
    connection.execute(
        "INSERT INTO lead_jobs (id, lead_id, stage, status, attempts, payload, created_at, updated_at) "
        "VALUES (%s, %s, 'website_verify', 'pending', 0, %s, %s, %s)",
        (job_id, lead_id, json.dumps({"location_id": location_id, "url": candidate.get("url")}), _now(), _now()),
    )


def persist_candidate(candidate: dict) -> str | None:
    brand_id = candidate["brand_id"]
    domain = candidate.get("domain") or normalize_domain(candidate.get("url"))
    account_id = _account_id(brand_id, domain, candidate.get("external_place_id") or candidate["name"])
    with get_connection() as connection:
        suppressed = connection.execute(
            "SELECT id FROM lead_suppressions WHERE brand_id = %s AND ((domain = %s AND domain IS NOT NULL) OR (email = %s AND email IS NOT NULL)) LIMIT 1",
            (brand_id, domain, candidate.get("email")),
        ).fetchone()
        if suppressed:
            return None
        existing = connection.execute("SELECT id FROM leads WHERE id = %s", (account_id,)).fetchone()
        if existing is None:
            # Reuse a known domain account when the stable Overture ID changed.
            if domain:
                existing = connection.execute(
                    "SELECT id FROM leads WHERE brand_id = %s AND domain = %s LIMIT 1", (brand_id, domain)
                ).fetchone()
            if existing:
                account_id = existing["id"]
        now = _now()
        if existing:
            connection.execute(
                "UPDATE leads SET name=%s, category=%s, location=%s, url=COALESCE(url,%s), country=%s, "
                "phone=COALESCE(phone,%s), email=COALESCE(email,%s), public_email=COALESCE(public_email,%s), "
                "social_links=%s, source=%s, source_url=%s, source_release=%s, domain=%s, operating_status=%s, "
                "overture_confidence=%s, external_place_id=COALESCE(external_place_id,%s), "
                "updated_at=%s WHERE id=%s",
                (candidate["name"], candidate.get("category"), candidate.get("location"), candidate.get("url"),
                 candidate.get("country"), candidate.get("phone"), candidate.get("email"), candidate.get("email"),
                 json.dumps(candidate.get("social_links") or []), candidate.get("source") or "overture_maps", candidate.get("url"), candidate.get("source_release"), domain,
                 candidate.get("operating_status"), candidate.get("confidence"), candidate.get("external_place_id"), now, account_id),
            )
        else:
            connection.execute(
                "INSERT INTO leads (id, brand_id, name, category, location, url, country, phone, email, public_email, "
                "social_links, source, source_url, status, fit_score, external_place_id, domain, operating_status, "
                "overture_confidence, source_release, stage, review_status, outreach_status, contact_status, created_at, updated_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'discovered',0,%s,%s,%s,%s,%s,'discovered','pending','not_approved','unknown',%s,%s)",
                (account_id, brand_id, candidate["name"], candidate.get("category"), candidate.get("location"),
                 candidate.get("url"), candidate.get("country"), candidate.get("phone"), candidate.get("email"),
                 candidate.get("email"), json.dumps(candidate.get("social_links") or []), candidate.get("source") or "overture_maps", candidate.get("url"),
                 candidate.get("external_place_id"), domain, candidate.get("operating_status"), candidate.get("confidence"),
                 candidate.get("source_release"), now, now),
            )
        location_id = _location_id(account_id, candidate.get("external_place_id") or "", candidate["name"], candidate.get("location") or "")
        location_exists = connection.execute("SELECT id FROM lead_locations WHERE id = %s", (location_id,)).fetchone()
        source_record = json.dumps(candidate.get("raw_record") or {}, ensure_ascii=False)
        if location_exists:
            connection.execute(
                "UPDATE lead_locations SET name=%s, category=%s, location=%s, country=%s, url=%s, phone=%s, email=%s, "
                "operating_status=%s, confidence=%s, source_release=%s, source_provider=%s, raw_record=%s, "
                "status='active', last_seen_at=%s WHERE id=%s",
                (candidate["name"], candidate.get("category"), candidate.get("location"), candidate.get("country"),
                 candidate.get("url"), candidate.get("phone"), candidate.get("email"), candidate.get("operating_status"),
                 candidate.get("confidence"), candidate.get("source_release"), candidate.get("source_provider"), source_record, now, location_id),
            )
        else:
            connection.execute(
                "INSERT INTO lead_locations (id, lead_id, external_place_id, name, category, location, country, url, phone, email, "
                "operating_status, confidence, source_release, source_provider, raw_record, status, first_seen_at, last_seen_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'active',%s,%s)",
                (location_id, account_id, candidate.get("external_place_id"), candidate["name"], candidate.get("category"),
                 candidate.get("location"), candidate.get("country"), candidate.get("url"), candidate.get("phone"),
                 candidate.get("email"), candidate.get("operating_status"), candidate.get("confidence"),
                 candidate.get("source_release"), candidate.get("source_provider"), source_record, now, now),
            )
        _sync_account(connection, account_id, brand_id, candidate["name"], domain, candidate.get("url"),
                      candidate.get("country"), candidate.get("category"), "discovered")
        _add_source_record(connection, account_id, location_id, candidate)
        source = candidate.get("source") or "overture_maps"
        _add_contact(connection, account_id, location_id, "email", candidate.get("email"), source, candidate.get("url"), candidate.get("confidence"))
        _add_contact(connection, account_id, location_id, "phone", candidate.get("phone"), source, candidate.get("url"), candidate.get("confidence"))
        _add_evidence(connection, account_id, "taxonomy", candidate.get("category"), source, candidate.get("url"), candidate.get("confidence"), location_id)
        _add_evidence(connection, account_id, "country", candidate.get("country"), source, None, candidate.get("confidence"), location_id)
        _add_evidence(connection, account_id, "business_name", candidate.get("name"), source, candidate.get("url"), candidate.get("confidence"), location_id)
        _add_evidence(connection, account_id, "website", candidate.get("url"), source, candidate.get("url"), candidate.get("confidence"), location_id)
        _add_evidence(connection, account_id, "email", candidate.get("email"), source, candidate.get("url"), candidate.get("confidence"), location_id)
        _add_evidence(connection, account_id, "phone", candidate.get("phone"), source, candidate.get("url"), candidate.get("confidence"), location_id)
        _enqueue_enrichment(connection, account_id, location_id, candidate)
    return account_id


def _public_addresses(host: str, port: int) -> bool:
    try:
        resolved = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise LeadPipelineError("DNS_FAILURE", "The website domain did not resolve.") from exc
    if not resolved:
        raise LeadPipelineError("DNS_FAILURE", "The website domain did not resolve.")
    for item in resolved:
        address = ipaddress.ip_address(item[4][0].split("%", 1)[0])
        if not address.is_global:
            raise LeadPipelineError("UNSAFE_URL", "The website resolved to a non-public network address.")
    return True


def _checked_url(url: str) -> tuple[str, str, int]:
    if not _valid_site_url(url):
        raise LeadPipelineError("INVALID_URL", "The source record did not contain an HTTP website.")
    parsed = urlparse(url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port not in {80, 443}:
        raise LeadPipelineError("UNSAFE_URL", "Only standard HTTP and HTTPS ports are allowed.")
    host = parsed.hostname or ""
    _public_addresses(host, port)
    return url, host, port


def _safe_fetch(url: str, *, max_bytes: int = MAX_PAGE_BYTES, redirects: int = 4) -> tuple[str, str, int]:
    current = url
    for _ in range(redirects + 1):
        _checked_url(current)
        try:
            with httpx.Client(timeout=httpx.Timeout(12, connect=5), follow_redirects=False, trust_env=False) as client:
                with client.stream("GET", current, headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.5"}) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        target = response.headers.get("location")
                        if not target:
                            raise LeadPipelineError("PARSE_FAILED", "Website returned an invalid redirect.")
                        current = urljoin(current, target)
                        continue
                    if response.status_code == 403:
                        raise LeadPipelineError("HTTP_403", "Website refused the request.")
                    if response.status_code == 404:
                        raise LeadPipelineError("HTTP_404", "Website page was not found.")
                    if response.status_code == 429:
                        retry_after = response.headers.get("retry-after", "")
                        raise LeadPipelineError("RATE_LIMITED", f"Website rate limited the request ({retry_after}).", True)
                    if response.status_code >= 500:
                        raise LeadPipelineError("HTTP_SERVER_ERROR", "Website returned a server error.", True)
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").lower()
                    if not any(kind in content_type for kind in ("html", "xml", "text/plain")) and content_type:
                        raise LeadPipelineError("UNSUPPORTED_CONTENT", "Website response is not HTML or XML.")
                    chunks: list[bytes] = []
                    size = 0
                    for chunk in response.iter_bytes(16384):
                        size += len(chunk)
                        if size > max_bytes:
                            break
                        chunks.append(chunk)
                    encoding = response.encoding or "utf-8"
                    return b"".join(chunks).decode(encoding, errors="replace"), str(response.url), response.status_code
        except LeadPipelineError:
            raise
        except httpx.TimeoutException as exc:
            raise LeadPipelineError("TIMEOUT", "Website request timed out.", True) from exc
        except httpx.ConnectError as exc:
            raise LeadPipelineError("CONNECTION_ERROR", "Could not connect to the website.", True) from exc
        except httpx.HTTPError as exc:
            raise LeadPipelineError("FETCH_FAILED", "Could not fetch the public website.", True) from exc
    raise LeadPipelineError("TOO_MANY_REDIRECTS", "Website redirected too many times.")


def _robots_parser(home_url: str) -> RobotFileParser:
    parsed = urlparse(home_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        body, _, _ = _safe_fetch(robots_url, max_bytes=128_000, redirects=2)
        parser.parse(body.splitlines())
    except LeadPipelineError as exc:
        if exc.code in {"HTTP_404", "UNSUPPORTED_CONTENT"}:
            parser.parse([])
        else:
            # A robots failure is not proof that crawling is permitted.
            parser.parse(["User-agent: *", "Disallow: /"])
    return parser


def _visible_text(html: str) -> tuple[str, str, str]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    description_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    description = str(description_tag.get("content") or "") if description_tag else ""
    for node in soup(["script", "style", "noscript", "svg"]):
        node.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))
    return title[:180], description[:600], text[:16000]


def _jsonld_objects(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    objects: list[dict] = []
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        try:
            data = json.loads(script.string or script.get_text())
        except (json.JSONDecodeError, TypeError):
            continue
        stack = data if isinstance(data, list) else [data]
        while stack:
            obj = stack.pop()
            if isinstance(obj, list):
                stack.extend(obj)
            elif isinstance(obj, dict):
                graph = obj.get("@graph")
                if graph:
                    stack.append(graph)
                if any(key in obj for key in ("@type", "name", "email", "telephone", "address")):
                    objects.append(obj)
    return objects[:50]


def _jsonld_values(objects: list[dict]) -> dict:
    names, descriptions, emails, phones, services, socials = [], [], [], [], [], []
    for item in objects:
        for key, target in (("name", names), ("description", descriptions), ("email", emails), ("telephone", phones), ("sameAs", socials)):
            value = item.get(key)
            if isinstance(value, list):
                target.extend(str(v) for v in value if v)
            elif value:
                target.append(str(value))
        for key in ("knowsAbout", "medicalSpecialty", "hasOfferCatalog", "makesOffer"):
            value = item.get(key)
            if isinstance(value, list):
                services.extend(json.dumps(v, ensure_ascii=False) if isinstance(v, dict) else str(v) for v in value)
            elif value:
                services.append(json.dumps(value, ensure_ascii=False) if isinstance(value, dict) else str(value))
    return {"names": names, "descriptions": descriptions, "emails": emails, "phones": phones, "services": services, "socials": socials}


def _internal_page_urls(home_url: str, html: str) -> list[str]:
    host = urlparse(home_url).hostname
    links: list[str] = []
    soup = BeautifulSoup(html, "html.parser")
    target_words = ("contact", "about", "team", "service", "location", "clinic", "branch", "practice")
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href") or "").strip()
        if not href or href.lower().startswith(("mailto:", "tel:", "javascript:", "#")):
            continue
        target = urljoin(home_url, href)
        parsed = urlparse(target)
        if parsed.scheme not in {"http", "https"} or parsed.hostname != host:
            continue
        if any(word in (parsed.path + " " + anchor.get_text(" ", strip=True)).lower() for word in target_words):
            links.append(target.split("#", 1)[0])
    return list(dict.fromkeys(links))[:3]


def _sitemap_urls(home_url: str, robots: RobotFileParser) -> list[str]:
    origin = f"{urlparse(home_url).scheme}://{urlparse(home_url).netloc}"
    sitemap_locations = [f"{origin}/sitemap.xml"]
    try:
        robots_body, _, _ = _safe_fetch(f"{origin}/robots.txt", max_bytes=128_000, redirects=2)
        sitemap_locations.extend(re.findall(r"(?im)^\s*Sitemap:\s*(\S+)", robots_body))
    except LeadPipelineError:
        pass
    urls: list[str] = []
    for sitemap in list(dict.fromkeys(sitemap_locations))[:3]:
        try:
            xml, _, _ = _safe_fetch(sitemap, max_bytes=500_000, redirects=2)
            root = ET.fromstring(xml)
        except (LeadPipelineError, ET.ParseError):
            continue
        for node in root.iter():
            if node.tag.lower().endswith("loc") and node.text:
                target = node.text.strip()
                path = urlparse(target).path.lower()
                if any(word in path for word in ("contact", "about", "team", "service", "location", "clinic", "branch")):
                    if urlparse(target).hostname == urlparse(home_url).hostname:
                        urls.append(target)
        if len(urls) >= MAX_SITE_PAGES:
            break
    return list(dict.fromkeys(urls))[:MAX_SITE_PAGES]


def _crawl4ai_text(url: str) -> str | None:
    if os.getenv("LEAD_CRAWL4AI_ENABLED", "false").lower() not in {"1", "true", "yes"}:
        return None
    try:
        from crawl4ai import AsyncWebCrawler
    except ImportError:
        return None
    async def run() -> str:
        async with AsyncWebCrawler(verbose=False) as crawler:
            result = await crawler.arun(url=url)
            if not result.success:
                return ""
            return str(result.markdown or result.cleaned_html or "")
    try:
        return asyncio.run(run()) or None
    except Exception:
        logger.info("Crawl4AI could not render %s", url)
        return None


def verify_website(url: str) -> dict:
    if not url:
        return {"ok": False, "error": "NO_WEBSITE", "pages": [], "text": "", "title": "", "description": "", "emails": [], "phones": [], "services": [], "socials": []}
    _checked_url(url)
    robots = _robots_parser(url)
    if not robots.can_fetch(USER_AGENT, url):
        raise LeadPipelineError("ROBOTS_BLOCKED", "The site robots.txt disallows crawling this page.")
    try:
        homepage_html, home_url, _ = _safe_fetch(url)
    except LeadPipelineError:
        raise
    title, description, homepage_text = _visible_text(homepage_html)
    jsonld = _jsonld_values(_jsonld_objects(homepage_html))
    selected_urls = _internal_page_urls(home_url, homepage_html)
    selected_urls.extend(url for url in _sitemap_urls(home_url, robots) if url not in selected_urls)
    origin = f"{urlparse(home_url).scheme}://{urlparse(home_url).netloc}"
    selected_urls.extend(
        f"{origin}/{path}"
        for path in ("contact", "contact-us", "about", "about-us", "team", "services", "locations")
        if f"{origin}/{path}" not in selected_urls
    )
    texts = [homepage_text]
    all_html = [homepage_html]
    verified_urls = [home_url]
    for page_url in selected_urls[:MAX_SITE_PAGES - 1]:
        if not robots.can_fetch(USER_AGENT, page_url):
            continue
        try:
            body, final_url, _ = _safe_fetch(page_url)
        except LeadPipelineError:
            continue
        _, page_description, page_text = _visible_text(body)
        texts.append(page_text)
        all_html.append(body)
        verified_urls.append(final_url)
        if not description and page_description:
            description = page_description
        for prop in _jsonld_values(_jsonld_objects(body)).items():
            key, values = prop
            jsonld[key].extend(values)
    rendered_text = ""
    if not any(texts) or len(" ".join(texts)) < 100:
        rendered_text = _crawl4ai_text(home_url) or ""
        if rendered_text:
            texts.append(rendered_text)
    html = "\n".join(all_html)
    emails = [str(v).strip().lower() for v in jsonld["emails"] if _email_syntax_ok(str(v).strip())]
    emails.extend(re.findall(r"(?i)mailto:([^?\"'\s>]+)", html))
    emails.extend(re.findall(r"(?i)[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,63}", html + " " + rendered_text))
    emails = [email for email in dict.fromkeys(unescape_html(value).strip().lower() for value in emails) if _usable_contact_email(email)]
    phones = [str(v) for v in jsonld["phones"] if v]
    phones.extend(re.findall(r"(?i)tel:([+\d][^\"'\s>]{6,})", html))
    services = list(dict.fromkeys([*jsonld["services"], *jsonld["descriptions"]]))
    return {
        "ok": True,
        "title": title,
        "name": (jsonld["names"] or [""])[0],
        "description": (jsonld["descriptions"] or [description])[0] if (jsonld["descriptions"] or [description]) else "",
        "text": " ".join(texts)[:30000],
        "emails": emails[:20],
        "phones": list(dict.fromkeys(phones))[:20],
        "services": services[:30],
        "socials": list(dict.fromkeys(jsonld["socials"]))[:20],
        "pages": verified_urls,
        "status": "verified",
    }


def unescape_html(value: str) -> str:
    from html import unescape
    return unescape(value)


def _usable_contact_email(email: str) -> bool:
    if not _email_syntax_ok(email):
        return False
    domain = email.rsplit("@", 1)[-1]
    if domain.endswith((".png", ".jpg", ".svg", ".webp")):
        return False
    return not any(part in email for part in ("example.", "sentry", "wixpress", "schema.org", "noreply", "no-reply"))


def email_mx_status(email: str) -> str:
    if not _email_syntax_ok(email):
        return "invalid_syntax"
    domain = email.rsplit("@", 1)[1]
    try:
        import dns.resolver
        dns.resolver.resolve(domain, "MX", lifetime=3)
        return "mx_valid"
    except ImportError:
        return "not_checked"
    except Exception:
        return "mx_missing"


def _fit_score(brand_id: str, candidate: dict, site: dict) -> tuple[int, str, dict, bool]:
    config = load_config()["brands"][brand_id]
    category = str(candidate.get("category") or "")
    hierarchy = set(candidate.get("hierarchy") or [])
    exact = category in config["exact_categories"]
    secondary_source = candidate.get("source") == "hunter_discover"
    broad = not exact and (category in config["hierarchy_categories"] or bool(hierarchy.intersection(config["hierarchy_categories"])) or secondary_source)
    text = " ".join((site.get("title") or "", site.get("description") or "", site.get("text") or "", " ".join(site.get("services") or []))).lower()
    matches = [term for term in config["keywords"] if term.lower() in text]
    breakdown = {
        "taxonomy_match": 35 if exact else 30 if secondary_source else 20 if broad else 0,
        "website_fit_signals": min(30, len(matches) * 6),
        "target_country": 10 if candidate.get("country") in load_config()["countries"] else 0,
        "working_website": 10 if site.get("ok") else 0,
        "overture_confidence": round(max(0, min(5, (candidate.get("confidence") or 0) * 5))),
        "matches": matches[:8],
        "version": SCORE_VERSION,
    }
    score = min(100, sum(value for key, value in breakdown.items() if isinstance(value, int)))
    sources = set()
    if category:
        sources.add(candidate.get("source") or "overture_maps")
    if site.get("ok") and matches:
        sources.add("company_website")
    has_independent_evidence = len(sources) >= 2
    qualified = score >= int(load_config().get("qualification_score", 75)) and has_independent_evidence and bool(exact or broad) and bool(matches)
    reasons = []
    if exact:
        reasons.append(f"Overture taxonomy matches {category}.")
    elif broad:
        reasons.append(f"Discovery source matches the {category} business group.")
    if matches:
        reasons.append("Company website confirms: " + ", ".join(matches[:4]) + ".")
    if not site.get("ok"):
        reasons.append("Website could not be independently verified yet.")
    elif not matches:
        reasons.append("Website was reachable but did not confirm a target service or business type.")
    return score, " ".join(reasons), breakdown, qualified


def _maybe_gemini(brand_id: str, candidate: dict, site: dict, score: int) -> dict | None:
    enabled = os.getenv("LEAD_GEMINI_ENABLED", "false").lower() in {"1", "true", "yes"}
    api_key = (os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or "").strip()
    model = (os.getenv("LEAD_GEMINI_MODEL") or "").strip()
    if not enabled or not api_key or not model or not 55 <= score < 85:
        return None
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        schema = {"type": "OBJECT", "properties": {
            "fit": {"type": "BOOLEAN"}, "confidence": {"type": "NUMBER"},
            "evidence": {"type": "STRING"}, "reason": {"type": "STRING"}},
            "required": ["fit", "confidence", "evidence", "reason"]}
        response = client.models.generate_content(
            model=model,
            contents=("Classify fit using only this public business evidence. Do not infer private facts. "
                      "Return JSON conforming to the requested schema.\nTarget: " + brand_id +
                      "\nOverture category: " + str(candidate.get("category")) +
                      "\nPublic website text: " + str(site.get("text") or "")[:8000]),
            config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema),
        )
        data = json.loads(response.text or "{}")
        if 0 <= float(data.get("confidence", 0)) <= 1 and len(str(data.get("evidence") or "")) < 300:
            return data
    except Exception:
        logger.info("Gemini lead classification unavailable", exc_info=True)
    return None


def _hunter_contact(domain: str, score: int) -> dict | None:
    key = (os.getenv("HUNTER_API_KEY") or "").strip()
    if not key or score < 75:
        return None
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    limit = max(0, int(os.getenv("LEAD_HUNTER_MONTHLY_CREDIT_LIMIT", "45")))
    if not _reserve_hunter_credit(period, limit):
        return None
    try:
        response = httpx.get("https://api.hunter.io/v2/domain-search", params={"domain": domain, "api_key": key, "type": "generic"}, timeout=15)
        if response.status_code in {401, 403, 429}:
            _release_hunter_credit(period)
            return None
        response.raise_for_status()
        data = response.json().get("data") or {}
        emails = data.get("emails") or []
        generic = sorted((item for item in emails if item.get("type") == "generic" and _email_syntax_ok(str(item.get("value") or ""))), key=lambda item: int(item.get("confidence") or 0), reverse=True)
        if not generic:
            _release_hunter_credit(period)
            return None
        found = generic[0]
        return {"email": str(found["value"]).lower(), "source_url": (found.get("sources") or [{}])[0].get("uri"), "confidence": float(found.get("confidence") or 0) / 100}
    except Exception:
        # Keep the reservation when the request outcome is unknown, avoiding accidental overuse.
        # HTTP exception text can contain the API key query string.
        logger.info("Hunter enrichment unavailable for %s (%s)", domain, exc.__class__.__name__)
        return None


def _reserve_hunter_credit(period: str, limit: int) -> bool:
    if limit <= 0:
        return False
    with get_connection() as connection:
        row = connection.execute("SELECT used FROM lead_provider_usage WHERE provider='hunter' AND period=%s", (period,)).fetchone()
        if not row:
            try:
                connection.execute("INSERT INTO lead_provider_usage (provider, period, used, updated_at) VALUES ('hunter', %s, 1, %s)", (period, _now()))
                return True
            except Exception:
                # A concurrent process may have inserted this period's row.
                row = connection.execute("SELECT used FROM lead_provider_usage WHERE provider='hunter' AND period=%s", (period,)).fetchone()
                if not row:
                    return False
        updated = connection.execute(
            "UPDATE lead_provider_usage SET used=used+1, updated_at=%s WHERE provider='hunter' AND period=%s AND used < %s",
            (_now(), period, limit),
        )
        return updated.rowcount == 1


def _release_hunter_credit(period: str) -> None:
    with get_connection() as connection:
        connection.execute("UPDATE lead_provider_usage SET used=used-1, updated_at=%s WHERE provider='hunter' AND period=%s AND used > 0", (_now(), period))


def _record_score(connection, lead_id: str, score: int, breakdown: dict, qualified: bool) -> None:
    connection.execute(
        "INSERT INTO lead_scores (id, lead_id, score, score_version, breakdown, qualification, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (str(uuid.uuid4()), lead_id, score, SCORE_VERSION, json.dumps(breakdown), "qualified" if qualified else "possible", _now()),
    )


def enrich_location_job(job: dict) -> None:
    payload = json.loads(job.get("payload") or "{}")
    location_id = payload.get("location_id")
    with get_connection() as connection:
        location = connection.execute("SELECT * FROM lead_locations WHERE id=%s", (location_id,)).fetchone()
        lead = connection.execute("SELECT * FROM leads WHERE id=%s", (job["lead_id"],)).fetchone()
        if not location or not lead:
            raise LeadPipelineError("SOURCE_RECORD_MISSING", "The lead location disappeared before enrichment.")
    candidate = {
        "brand_id": lead["brand_id"], "external_place_id": location.get("external_place_id"),
        "source": lead.get("source") or "overture_maps",
        "name": location["name"], "category": location.get("category"), "country": location.get("country"),
        "hierarchy": (json.loads(location.get("raw_record") or "{}").get("taxonomy") or {}).get("hierarchy", []),
        "confidence": location.get("confidence"), "url": location.get("url"),
    }
    try:
        site = verify_website(str(location.get("url") or ""))
    except LeadPipelineError as exc:
        site = {"ok": False, "error": exc.code, "text": "", "title": "", "description": "", "emails": [], "phones": [], "services": [], "socials": [], "pages": []}
        if exc.retryable:
            raise
    score, why, breakdown, qualified = _fit_score(lead["brand_id"], candidate, site)
    classifier = _maybe_gemini(lead["brand_id"], candidate, site, score)
    website_url = (site.get("pages") or [None])[0]
    email = site["emails"][0] if site.get("emails") else lead.get("email") or lead.get("public_email")
    phone = site["phones"][0] if site.get("phones") else lead.get("phone")
    if email and email_mx_status(email) != "mx_valid" and not site.get("emails"):
        email = None
    hunter_evidence = None
    if not email and qualified and lead.get("domain"):
        hunter_evidence = _hunter_contact(lead["domain"], score)
        email = hunter_evidence.get("email") if hunter_evidence else None
    if classifier:
        breakdown["ambiguous_classifier"] = {"fit": bool(classifier.get("fit")), "confidence": classifier.get("confidence"), "reason": classifier.get("reason"), "evidence": classifier.get("evidence")}
        if classifier.get("fit") is False and float(classifier.get("confidence") or 0) >= 0.85:
            qualified = False
            why += " Gemini found conflicting fit evidence: " + str(classifier.get("reason") or "")
    final_status = "qualified" if qualified else "possible" if score >= 40 else "low"
    contact_status = "verified" if site.get("emails") and email and email_mx_status(email) == "mx_valid" else "unverified" if email else "phone_only" if phone else "unavailable"
    with get_connection() as connection:
        for page_url in site.get("pages") or []:
            _add_evidence(connection, lead["id"], "website_page", page_url, "company_website", page_url, 1.0, location_id)
        if site.get("title"):
            _add_evidence(connection, lead["id"], "website_title", site["title"], "company_website", website_url, 0.95, location_id)
        if site.get("description"):
            _add_evidence(connection, lead["id"], "website_description", site["description"], "company_website", website_url, 0.9, location_id)
        text = str(site.get("text") or "")
        brand_config = load_config()["brands"][lead["brand_id"]]
        for term in brand_config["keywords"]:
            match = re.search(r"[^.!?]*\b" + re.escape(term) + r"\b[^.!?]*[.!?]?", text, re.I)
            if match:
                _add_evidence(connection, lead["id"], "fit_signal", match.group(0)[:500], "company_website", website_url, 0.9, location_id)
        for value in site.get("emails") or []:
            _add_evidence(connection, lead["id"], "email", value, "company_website", website_url, 1.0, location_id)
        for value in site.get("phones") or []:
            _add_evidence(connection, lead["id"], "phone", value, "company_website", website_url, 1.0, location_id)
            _add_contact(connection, lead["id"], location_id, "phone", value, "company_website", website_url, 1.0, "published")
        for value in site.get("emails") or []:
            verification = email_mx_status(value)
            _add_contact(connection, lead["id"], location_id, "email", value, "company_website", website_url, 1.0,
                         "mx_valid" if verification == "mx_valid" else verification)
        if hunter_evidence:
            _add_evidence(connection, lead["id"], "email", email, "hunter", hunter_evidence.get("source_url") or "https://hunter.io", hunter_evidence.get("confidence"), location_id)
            _add_contact(connection, lead["id"], location_id, "email", email, "hunter", hunter_evidence.get("source_url") or "https://hunter.io", hunter_evidence.get("confidence"), "hunter_verified")
        requirements = " ".join([str(site.get("description") or ""), *[str(x) for x in site.get("services") or []]])[:1000]
        connection.execute(
            "UPDATE leads SET url=COALESCE(%s,url), name=COALESCE(NULLIF(%s,''),name), fit_score=%s, why=%s, requirements=%s, "
            "description=%s, services=%s, email=%s, public_email=%s, phone=%s, stage=%s, status=%s, score_version=%s, "
            "score_breakdown=%s, contact_status=%s, last_verified_at=%s, source_title=%s, updated_at=%s WHERE id=%s",
            (website_url or location.get("url"), str(site.get("name") or ""), score, why[:1200], requirements,
             (site.get("description") or "")[:1200], json.dumps(site.get("services") or []), email, email, phone,
             "qualified" if qualified else "verified", final_status, SCORE_VERSION, json.dumps(breakdown), contact_status,
             _now() if site.get("ok") else None, site.get("title"), _now(), lead["id"]),
        )
        connection.execute(
            "UPDATE lead_locations SET last_verified_at=%s, status=%s WHERE id=%s",
            (_now() if site.get("ok") else None, "verified" if site.get("ok") else str(site.get("error") or "unverified").lower(), location_id),
        )
        _record_score(connection, lead["id"], score, breakdown, qualified)
        _sync_account(connection, lead["id"], lead["brand_id"], str(site.get("name") or lead["name"]), lead.get("domain"),
                      website_url or location.get("url"), lead.get("country"), lead.get("category"),
                      "qualified" if qualified else "verified", score, SCORE_VERSION)


def _claim_job() -> dict | None:
    now = _now()
    expired = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
    with get_connection() as connection:
        row = connection.execute(
            "SELECT id, lead_id, stage, status, attempts, payload FROM lead_jobs "
            "WHERE (status='pending' AND (next_attempt_at IS NULL OR next_attempt_at <= %s)) "
            "OR (status='running' AND locked_at < %s) ORDER BY created_at LIMIT 1",
            (now, expired),
        ).fetchone()
        if not row:
            return None
        result = connection.execute(
            "UPDATE lead_jobs SET status='running', locked_at=%s, attempts=attempts+1, updated_at=%s WHERE id=%s AND (status='pending' OR locked_at < %s)",
            (now, now, row["id"], expired),
        )
        if result.rowcount != 1:
            return None
        row["attempts"] = int(row.get("attempts") or 0) + 1
        return row


def process_pending_jobs(max_jobs: int = 300) -> tuple[int, list[str]]:
    completed = 0
    errors: list[str] = []
    for _ in range(max_jobs):
        job = _claim_job()
        if not job:
            break
        try:
            if job["stage"] == "website_verify":
                enrich_location_job(job)
            with get_connection() as connection:
                connection.execute("UPDATE lead_jobs SET status='done', locked_at=NULL, last_error=NULL, updated_at=%s WHERE id=%s", (_now(), job["id"]))
            completed += 1
            time.sleep(float(os.getenv("LEAD_CRAWL_DELAY_SECONDS", "0.35")))
        except LeadPipelineError as exc:
            errors.append(f"{exc.code}: {exc}")
            attempts = int(job.get("attempts") or 1)
            should_retry = exc.retryable and attempts < MAX_JOB_ATTEMPTS
            delay = RETRY_DELAYS[min(attempts - 1, len(RETRY_DELAYS) - 1)] if should_retry else 0
            with get_connection() as connection:
                connection.execute(
                    "UPDATE lead_jobs SET status=%s, locked_at=NULL, next_attempt_at=%s, last_error=%s, updated_at=%s WHERE id=%s",
                    ("pending" if should_retry else "failed", (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat() if should_retry else None,
                     f"{exc.code}: {exc}"[:500], _now(), job["id"]),
                )
                if job.get("lead_id"):
                    connection.execute("UPDATE leads SET stage='enrichment_failed', updated_at=%s WHERE id=%s AND stage!='qualified'", (_now(), job["lead_id"]))
        except Exception as exc:
            errors.append(f"{exc.__class__.__name__}")
            attempts = int(job.get("attempts") or 1)
            should_retry = attempts < MAX_JOB_ATTEMPTS
            delay = RETRY_DELAYS[min(attempts - 1, len(RETRY_DELAYS) - 1)] if should_retry else 0
            with get_connection() as connection:
                connection.execute(
                    "UPDATE lead_jobs SET status=%s, locked_at=NULL, next_attempt_at=%s, last_error=%s, updated_at=%s WHERE id=%s",
                    ("pending" if should_retry else "failed", (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat() if should_retry else None,
                     exc.__class__.__name__, _now(), job["id"]),
                )
    return completed, errors


def _apply_changelog(release: str) -> dict:
    """Mark removed Overture matches stale and changed records for re-verification."""
    try:
        import duckdb
    except ImportError:
        return {"removed": 0, "changed": 0}
    with get_connection() as connection:
        records = connection.execute("SELECT DISTINCT external_place_id FROM lead_locations WHERE external_place_id IS NOT NULL").fetchall()
    ids = [str(row["external_place_id"]) for row in records]
    if not ids:
        return {"removed": 0, "changed": 0}
    con = duckdb.connect(database=":memory:")
    changed: list[tuple[str, str, list[str]]] = []
    try:
        con.execute("INSTALL httpfs")
        con.execute("LOAD httpfs")
        con.execute("SET s3_region='us-west-2'")
        con.execute("CREATE TEMP TABLE tracked_ids(id VARCHAR)")
        con.executemany("INSERT INTO tracked_ids VALUES (?)", [(value,) for value in ids])
        table = f"{OVERTURE_S3}/changelog/{release}/theme=places/type=place/change_type=*/*"
        rows = con.execute(
            "SELECT c.id, c.change_type, c.columns_changed FROM read_parquet(?, hive_partitioning=1) c "
            "INNER JOIN tracked_ids t ON c.id=t.id WHERE c.change_type IN ('removed','data_changed')",
            [table],
        ).fetchall()
        changed = [(str(row[0]), str(row[1]), row[2] or []) for row in rows]
    except Exception:
        logger.info("Overture changelog check unavailable", exc_info=True)
    finally:
        con.close()
    removed = 0
    changed_count = 0
    with get_connection() as connection:
        for place_id, change_type, columns in changed:
            locations = connection.execute("SELECT id, lead_id FROM lead_locations WHERE external_place_id=%s", (place_id,)).fetchall()
            if change_type == "removed":
                connection.execute("UPDATE lead_locations SET status='source_removed_pending_review' WHERE external_place_id=%s", (place_id,))
                removed += 1
            elif set(columns).intersection({"taxonomy", "basic_category", "operating_status", "addresses", "websites", "emails", "phones"}):
                connection.execute("UPDATE lead_locations SET status='needs_reverify' WHERE external_place_id=%s", (place_id,))
                changed_count += 1
            else:
                continue
            new_stage = "source_removed_pending_review" if change_type == "removed" else "needs_reverification"
            for location in locations:
                connection.execute(
                    "UPDATE leads SET stage=%s, review_status='pending', reviewed_by=NULL, reviewed_at=NULL, "
                    "outreach_status='not_approved', outreach_approved_by=NULL, outreach_approved_at=NULL, updated_at=%s WHERE id=%s",
                    (new_stage, _now(), location["lead_id"]),
                )
                connection.execute(
                    "UPDATE lead_accounts SET stage=%s, review_status='pending', reviewed_by=NULL, reviewed_at=NULL, "
                    "outreach_status='not_approved', outreach_approved_by=NULL, outreach_approved_at=NULL, updated_at=%s WHERE id=%s",
                    (new_stage, _now(), location["lead_id"]),
                )
    return {"removed": removed, "changed": changed_count}


def discover_and_enrich() -> dict:
    release = latest_release()
    old_release = _state().get("release")
    if old_release == release:
        resumed = resume_pending_jobs()
        return {
            "release": release,
            "discovered": 0,
            "accounts": 0,
            "enriched": resumed["enriched"],
            "pending_jobs": resumed["pending_jobs"],
            "changelog": {"removed": 0, "changed": 0},
            "errors": resumed["errors"],
        }
    change_counts = _apply_changelog(release) if old_release and old_release != release else {"removed": 0, "changed": 0}
    candidates = overture_candidates(release)
    hunter_candidates, hunter_errors = hunter_discover_candidates()
    candidates.extend(hunter_candidates)
    accounts: set[str] = set()
    errors: list[str] = hunter_errors[:]
    for candidate in candidates:
        try:
            account = persist_candidate(candidate)
            if account:
                accounts.add(account)
        except Exception as exc:
            errors.append(f"{exc.__class__.__name__}")
            logger.info("Could not persist Overture place %s", candidate.get("external_place_id"), exc_info=True)
    completed, job_errors = process_pending_jobs(max_jobs=int(os.getenv("LEAD_MAX_JOBS_PER_RUN", "300")))
    errors.extend(job_errors)
    with get_connection() as connection:
        pending = connection.execute("SELECT COUNT(*) AS total FROM lead_jobs WHERE status='pending'").fetchone()
    return {
        "release": release,
        "discovered": len(candidates),
        "accounts": len(accounts),
        "enriched": completed,
        "pending_jobs": int((pending or {}).get("total") or 0),
        "changelog": change_counts,
        "errors": errors[:10],
    }


def resume_pending_jobs() -> dict:
    completed, errors = process_pending_jobs(max_jobs=int(os.getenv("LEAD_MAX_JOBS_PER_RUN", "300")))
    with get_connection() as connection:
        pending = connection.execute("SELECT COUNT(*) AS total FROM lead_jobs WHERE status='pending'").fetchone()
    return {"enriched": completed, "pending_jobs": int((pending or {}).get("total") or 0), "errors": errors[:10]}


def refresh(*, force: bool = False) -> dict:
    global _RUNNING
    with _RUN_LOCK:
        if _RUNNING:
            return get_status()
        _RUNNING = True
    started = _now()
    _save_state(last_error=None, refreshing=True)
    try:
        result = discover_and_enrich()
        state = _save_state(
            last_scraped_at=_now(), release=result["release"], updated=result["accounts"],
            pending_jobs=result["pending_jobs"], last_error="; ".join(result["errors"]) or None,
            last_run=started, changelog=result["changelog"],
        )
        return {**get_status(), **result, **{"last_error": state.get("last_error")}}
    except LeadPipelineError as exc:
        _save_state(last_error=f"{exc.code}: {exc}", pending_jobs=0)
        return get_status()
    finally:
        _save_state(refreshing=False)
        with _RUN_LOCK:
            _RUNNING = False


def _is_stale() -> bool:
    state = _state()
    last = state.get("last_scraped_at")
    if not last:
        return True
    try:
        return datetime.now(timezone.utc) - datetime.fromisoformat(last) > timedelta(hours=int(os.getenv("LEAD_REFRESH_HOURS", "720")))
    except ValueError:
        return True


def start_scheduler() -> None:
    if os.getenv("AURA_LEAD_REFRESH", "true").lower() in {"0", "false", "no"} or os.getenv("PYTEST_CURRENT_TEST"):
        return
    import threading
    def loop() -> None:
        while True:
            try:
                resume_pending_jobs()
                if _is_stale():
                    refresh()
            except Exception:
                logger.exception("Lead discovery scheduler failed")
            time.sleep(60 * 60)
    threading.Thread(target=loop, name="aura-lead-refresh", daemon=True).start()


def list_leads(brand_id: str | None = None, *, review_status: str | None = None) -> list[dict]:
    with get_connection() as connection:
        query = "SELECT leads.*, (SELECT COUNT(*) FROM lead_locations WHERE lead_locations.lead_id=leads.id) AS location_count FROM leads"
        clauses, params = [], []
        if brand_id:
            clauses.append("brand_id=%s")
            params.append(brand_id)
        if review_status:
            clauses.append("review_status=%s")
            params.append(review_status)
        if clauses:
            query += " WHERE " + " AND ".join(clauses)
        query += " ORDER BY fit_score DESC, name"
        rows = connection.execute(query, tuple(params)).fetchall()
        output = []
        for row in rows:
            def decoded(value, default):
                if isinstance(value, (dict, list)):
                    return value
                try:
                    return json.loads(value or "")
                except (json.JSONDecodeError, TypeError):
                    return default
            row["score_breakdown"] = decoded(row.get("score_breakdown"), {})
            for field in ("social_links", "services", "products", "specialties", "fit_reasons"):
                row[field] = decoded(row.get(field), [])
            output.append(row)
        return output


def lead_details(lead_id: str) -> dict | None:
    with get_connection() as connection:
        lead = connection.execute("SELECT * FROM leads WHERE id=%s", (lead_id,)).fetchone()
        if not lead:
            return None
        locations = connection.execute("SELECT * FROM lead_locations WHERE lead_id=%s ORDER BY country, location", (lead_id,)).fetchall()
        contacts = connection.execute("SELECT * FROM lead_contacts WHERE lead_id=%s ORDER BY contact_type, observed_at DESC", (lead_id,)).fetchall()
        evidence = connection.execute("SELECT * FROM lead_evidence WHERE lead_id=%s ORDER BY observed_at DESC", (lead_id,)).fetchall()
        scores = connection.execute("SELECT * FROM lead_scores WHERE lead_id=%s ORDER BY created_at DESC LIMIT 10", (lead_id,)).fetchall()
    lead["locations"] = locations
    lead["contacts"] = contacts
    lead["evidence"] = evidence
    def decoded(value, default):
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value or "")
        except (json.JSONDecodeError, TypeError):
            return default
    lead["score_history"] = [{**score, "breakdown": decoded(score.get("breakdown"), {})} for score in scores]
    lead["score_breakdown"] = decoded(lead.get("score_breakdown"), {})
    for field in ("social_links", "services", "products", "specialties", "fit_reasons"):
        lead[field] = decoded(lead.get(field), [])
    return lead


def review_lead(lead_id: str, decision: str, reviewer: str, note: str | None = None) -> dict | None:
    if decision not in {"approved", "rejected"}:
        raise ValueError("Review decision must be approved or rejected")
    with get_connection() as connection:
        lead = connection.execute("SELECT id, brand_id, domain, email, public_email, fit_score, status, stage FROM leads WHERE id=%s", (lead_id,)).fetchone()
        if not lead:
            return None
        if decision == "approved" and (
            lead.get("status") != "qualified"
            or lead.get("stage") != "qualified"
            or int(lead.get("fit_score") or 0) < int(load_config().get("qualification_score", 75))
        ):
            raise ValueError("Only qualified leads can be approved for outreach")
        result = connection.execute(
            "UPDATE leads SET review_status=%s, reviewed_by=%s, reviewed_at=%s, review_note=%s, "
            "outreach_status=%s, outreach_approved_by=%s, outreach_approved_at=%s, updated_at=%s WHERE id=%s "
            "AND (%s!='approved' OR NOT EXISTS (SELECT 1 FROM lead_suppressions s WHERE s.brand_id=leads.brand_id "
            "AND ((s.domain=leads.domain AND s.domain IS NOT NULL) OR "
            "(s.email=LOWER(COALESCE(leads.email,leads.public_email,'')) AND s.email IS NOT NULL))))",
            (decision, reviewer[:255], _now(), (note or "")[:2000], "approved" if decision == "approved" else "not_approved",
             reviewer[:255] if decision == "approved" else None, _now() if decision == "approved" else None, _now(), lead_id, decision),
        )
        if result.rowcount != 1:
            raise ValueError("This lead is on the outreach suppression list")
        connection.execute(
            "UPDATE lead_accounts SET review_status=%s, reviewed_by=%s, reviewed_at=%s, review_note=%s, outreach_status=%s, "
            "outreach_approved_by=%s, outreach_approved_at=%s, updated_at=%s WHERE id=%s",
            (decision, reviewer[:255], _now(), (note or "")[:2000], "approved" if decision == "approved" else "not_approved",
             reviewer[:255] if decision == "approved" else None, _now() if decision == "approved" else None, _now(), lead_id),
        )
    return lead_details(lead_id)


def add_suppression(brand_id: str, domain: str | None, email: str | None, reason: str | None, actor: str) -> str:
    if not domain and not email:
        raise ValueError("A suppression requires a domain or email")
    normalized_domain = normalize_domain(domain) if domain else None
    if domain and not normalized_domain:
        raise ValueError("Suppression domain is invalid")
    suppression_id = str(uuid.uuid4())
    with get_connection() as connection:
        connection.execute("INSERT INTO lead_suppressions (id, brand_id, domain, email, reason, created_by, created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                           (suppression_id, brand_id, normalized_domain, email.lower() if email else None, reason, actor[:255], _now()))
        if normalized_domain:
            connection.execute("UPDATE leads SET review_status='rejected', outreach_status='not_approved', outreach_approved_by=NULL, outreach_approved_at=NULL, reviewed_by=%s, reviewed_at=%s, review_note=%s WHERE brand_id=%s AND domain=%s", (actor[:255], _now(), reason or "Suppressed", brand_id, normalized_domain))
            connection.execute("UPDATE lead_accounts SET review_status='rejected', reviewed_by=%s, reviewed_at=%s, review_note=%s, outreach_status='not_approved', outreach_approved_by=NULL, outreach_approved_at=NULL WHERE brand_id=%s AND domain=%s", (actor[:255], _now(), reason or "Suppressed", brand_id, normalized_domain))
        if email:
            normalized_email = email.strip().lower()
            connection.execute("UPDATE leads SET review_status='rejected', outreach_status='not_approved', outreach_approved_by=NULL, outreach_approved_at=NULL, reviewed_by=%s, reviewed_at=%s, review_note=%s WHERE brand_id=%s AND lower(COALESCE(email, public_email,''))=%s", (actor[:255], _now(), reason or "Suppressed", brand_id, normalized_email))
            connection.execute("UPDATE lead_accounts SET review_status='rejected', reviewed_by=%s, reviewed_at=%s, review_note=%s, outreach_status='not_approved', outreach_approved_by=NULL, outreach_approved_at=NULL WHERE brand_id=%s AND id IN (SELECT id FROM leads WHERE brand_id=%s AND lower(COALESCE(email, public_email,''))=%s)", (actor[:255], _now(), reason or "Suppressed", brand_id, brand_id, normalized_email))
    return suppression_id


def approve_outreach(lead_id: str, actor: str) -> dict | None:
    return review_lead(lead_id, "approved", actor, "Outreach explicitly approved")


def mark_outreach_sent(lead_id: str) -> None:
    with get_connection() as connection:
        connection.execute("UPDATE leads SET outreach_status='sent', outreach_sent_at=%s, status='contacted', updated_at=%s WHERE id=%s AND outreach_status='sending'", (_now(), _now(), lead_id))
        connection.execute("UPDATE lead_accounts SET outreach_status='sent', updated_at=%s WHERE id=%s", (_now(), lead_id))


def claim_outreach_send(lead_id: str) -> bool:
    with get_connection() as connection:
        result = connection.execute(
            "UPDATE leads SET outreach_status='sending', updated_at=%s WHERE id=%s AND review_status='approved' AND outreach_status='approved' "
            "AND NOT EXISTS (SELECT 1 FROM lead_suppressions s WHERE s.brand_id=leads.brand_id "
            "AND ((s.domain=leads.domain AND s.domain IS NOT NULL) OR "
            "(s.email=LOWER(COALESCE(leads.email,leads.public_email,'')) AND s.email IS NOT NULL)))",
            (_now(), lead_id),
        )
        claimed = result.rowcount == 1
        if claimed:
            connection.execute("UPDATE lead_accounts SET outreach_status='sending', updated_at=%s WHERE id=%s AND outreach_status='approved'", (_now(), lead_id))
        return claimed


def mark_outreach_failed(lead_id: str) -> None:
    with get_connection() as connection:
        connection.execute("UPDATE leads SET outreach_status='send_failed', updated_at=%s WHERE id=%s AND outreach_status='sending'", (_now(), lead_id))
        connection.execute("UPDATE lead_accounts SET outreach_status='send_failed', updated_at=%s WHERE id=%s AND outreach_status='sending'", (_now(), lead_id))


def hunter_remaining() -> int:
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    limit = max(0, int(os.getenv("LEAD_HUNTER_MONTHLY_CREDIT_LIMIT", "45")))
    with get_connection() as connection:
        row = connection.execute("SELECT used FROM lead_provider_usage WHERE provider='hunter' AND period=%s", (period,)).fetchone()
    return max(0, limit - int((row or {}).get("used") or 0))
