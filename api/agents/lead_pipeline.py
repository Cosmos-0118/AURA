"""Evidence-backed lead discovery and enrichment using Overture Maps Places."""

from __future__ import annotations

import asyncio
import base64
import binascii
import hashlib
import http.client
import ipaddress
import json
import logging
import os
import re
import socket
import ssl
import threading
import time
import unicodedata
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
import tldextract

try:
    from ..db import get_connection
except ImportError:
    from db import get_connection

logger = logging.getLogger("aura.lead_pipeline")

MODULE_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = MODULE_ROOT if (MODULE_ROOT / "api").is_dir() else Path.cwd()
ICP_CONFIG_PATH = Path(__file__).resolve().parents[1] / "config" / "lead_icps.json"
STATE_PATH = PROJECT_ROOT / ".aura" / "lead-refresh.json"
OVERTURE_STAC = "https://stac.overturemaps.org/catalog.json"
OVERTURE_S3 = "s3://overturemaps-us-west-2"
USER_AGENT = "AURA-LeadIntelligence/1.0 (+public business website verification)"
SCORE_VERSION = "2026-09-23.1"
MAX_PAGE_BYTES = 1_500_000
MAX_SITE_PAGES = 6
MAX_JOB_ATTEMPTS = 4
RETRY_DELAYS = (30, 300, 3600)
_RUN_LOCK = threading.Lock()
_JOB_RUN_LOCK = threading.Lock()
_MANUAL_JOB_WORKER_LOCK = threading.Lock()
_STATE_LOCK = threading.Lock()
_SCHEDULER_LOCK = threading.Lock()
_HOST_LOCKS_LOCK = threading.Lock()
_HOST_LOCKS: dict[str, threading.Lock] = {}
_HOST_LAST_FETCH: dict[str, float] = {}
_RUNNING = False
_SCHEDULER_STARTED = False
_MANUAL_JOB_WORKER_STARTED = False
_DOMAIN_EXTRACTOR = tldextract.TLDExtract(
    suffix_list_urls=(), cache_dir=None, fallback_to_snapshot=True,
    include_psl_private_domains=True,
)


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
    with _STATE_LOCK:
        state = {**_state(), **values}
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        temporary = STATE_PATH.with_name(STATE_PATH.name + "." + uuid.uuid4().hex + ".tmp")
        try:
            temporary.write_text(json.dumps(state), encoding="utf-8")
            temporary.replace(STATE_PATH)
        finally:
            temporary.unlink(missing_ok=True)
        return state


def get_status() -> dict:
    state = _state()
    refreshing = _RUNNING
    return {
        "refreshing": refreshing,
        "configured": True,
        "source": "Overture Maps Places",
        "phase": state.get("refresh_phase") if refreshing else None,
        "refresh_started_at": state.get("refresh_started_at") if refreshing else None,
        "release": state.get("release"),
        "last_scraped_at": state.get("last_scraped_at"),
        "last_error": state.get("last_error"),
        "updated": state.get("updated", 0),
        "watched": len(load_config()["brands"]),
        "pending_jobs": state.get("pending_jobs", 0),
        "jobs_progress_total": state.get("jobs_progress_total", 0),
        "jobs_last_progress_at": state.get("jobs_last_progress_at"),
    }


def _set_refresh_phase(phase: str) -> None:
    _save_state(refresh_phase=phase)


def _pending_job_count() -> int:
    try:
        with get_connection() as connection:
            pending = connection.execute(
                "SELECT COUNT(*) AS total FROM lead_jobs WHERE status='pending'"
            ).fetchone()
        return int((pending or {}).get("total") or 0)
    except Exception:
        return int(_state().get("pending_jobs") or 0)


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


def _release_parent(release: str) -> str | None:
    try:
        response = httpx.get(f"https://stac.overturemaps.org/{release}/catalog.json", timeout=15, follow_redirects=True)
        response.raise_for_status()
        catalog = response.json()
        previous = next((link for link in catalog.get("links", []) if link.get("rel") == "prev"), None)
        if previous is None:
            return None
        parent = str(previous.get("title") or "").split()[0]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}\.\d+", parent):
            path = urlparse(str(previous.get("href") or "")).path.rstrip("/").split("/")
            parent = path[-1] if path else ""
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}\.\d+", parent):
            raise ValueError("Overture release catalog did not identify its previous release")
        return parent
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        raise LeadPipelineError("SOURCE_UNAVAILABLE", "Could not read the Overture release chain.", True) from exc


def _duckdb_connection(duckdb):
    extension_directory = os.getenv("DUCKDB_EXTENSION_DIRECTORY") or str(STATE_PATH.parent / "duckdb_extensions")
    return duckdb.connect(database=":memory:", config={"extension_directory": extension_directory})


def overture_candidates(release: str | None = None, *, country: str | None = None) -> list[dict]:
    """Query the current Overture Places GeoParquet with DuckDB and schema v2 fields."""
    try:
        import duckdb
    except ImportError as exc:
        raise LeadPipelineError("DUCKDB_MISSING", "Install the API dependency group to enable Overture discovery.") from exc

    config = load_config()
    release = release or latest_release()
    countries = [country] if country else config["countries"]
    if any(item not in config["countries"] for item in countries):
        raise ValueError("Country is not configured for Overture discovery")
    path = f"{OVERTURE_S3}/release/{release}/theme=places/type=place/*"
    rows: list[dict] = []
    con = None
    try:
        con = _duckdb_connection(duckdb)
        con.execute("INSTALL httpfs")
        con.execute("LOAD httpfs")
        con.execute("SET s3_region='us-west-2'")
        exact_by_brand = {brand: set(icp["exact_categories"]) for brand, icp in config["brands"].items()}
        hierarchy_by_brand = {brand: set(icp["hierarchy_categories"]) for brand, icp in config["brands"].items()}
        all_exact = sorted(set().union(*exact_by_brand.values()))
        all_targets = sorted(set().union(*exact_by_brand.values(), *hierarchy_by_brand.values()))
        category_expr = [f"COALESCE(p.taxonomy.primary, p.basic_category) IN ({','.join('?' for _ in all_exact)})"]
        category_params: list[object] = list(all_exact)
        for category in all_targets:
            category_expr.append("list_contains(p.taxonomy.hierarchy, ?)")
            category_params.append(category)
        for category in all_targets:
            category_expr.append("list_contains(p.taxonomy.alternates, ?)")
            category_params.append(category)
        country_cases = []
        country_case_params: list[object] = []
        country_predicates = []
        country_where_params: list[object] = []
        for country_code in countries:
            west, south, east, north = config["country_bounds"][country_code]
            predicate = (
                "(list_contains(list_transform(p.addresses, a -> a.country), ?) AND "
                "p.bbox.xmin BETWEEN ? AND ? AND p.bbox.ymin BETWEEN ? AND ?)"
            )
            predicate_params = (country_code, west, east, south, north)
            country_cases.append(f"WHEN {predicate} THEN ?")
            country_case_params.extend((*predicate_params, country_code))
            country_predicates.append(predicate)
            country_where_params.extend(predicate_params)
        sql = f"""
            WITH classified AS (
                SELECT p.id, p.names.primary AS name, p.basic_category,
                       COALESCE(p.taxonomy.primary, p.basic_category) AS taxonomy_primary,
                       p.taxonomy.hierarchy AS taxonomy_hierarchy,
                       p.taxonomy.alternates AS taxonomy_alternates,
                       p.operating_status, p.confidence,
                       p.websites, p.emails, p.phones, p.socials,
                       p.addresses, p.sources, p.bbox,
                       CASE {' '.join(country_cases)} ELSE NULL END AS country_filter
                FROM read_parquet(?, hive_partitioning=1) AS p
                WHERE ({' OR '.join(category_expr)})
                  AND p.confidence >= ?
                  AND COALESCE(p.operating_status, '') != 'permanently_closed'
                  AND ({' OR '.join(country_predicates)})
            ), country_matches AS (
                SELECT * FROM classified WHERE country_filter IS NOT NULL
            )
            SELECT * EXCLUDE (candidate_rank) FROM (
                SELECT *, ROW_NUMBER() OVER (
                    PARTITION BY country_filter, COALESCE(taxonomy_primary, basic_category)
                    ORDER BY confidence DESC NULLS LAST
                ) AS candidate_rank
                FROM country_matches
            ) AS ranked
            WHERE candidate_rank <= ?
            ORDER BY confidence DESC NULLS LAST
        """
        per_brand_limit = max(1, int(config.get("max_candidates_per_brand_run", 300)))
        result = con.execute(
            sql,
            [*country_case_params, path, *category_params, float(config["minimum_overture_confidence"]),
             *country_where_params, per_brand_limit],
        )
        columns = [column[0] for column in result.description]
        for record in result.fetchall():
            item = dict(zip(columns, record))
            primary = str(item.get("taxonomy_primary") or "")
            hierarchy = set(item.get("taxonomy_hierarchy") or [])
            alternates = set(item.get("taxonomy_alternates") or [])
            for brand_id in config["brands"]:
                exact = exact_by_brand[brand_id]
                broad = hierarchy_by_brand[brand_id]
                if primary in exact or hierarchy.intersection(exact | broad) or alternates.intersection(exact | broad):
                    exact_match = primary if primary in exact else next(iter(sorted(alternates.intersection(exact))), None)
                    hierarchy_match = next(iter(sorted(hierarchy.intersection(exact | broad))), None)
                    brand_item = {
                        **item, "brand_id": brand_id, "source": "overture_maps",
                        "matched_category": exact_match or hierarchy_match,
                        "matched_is_exact": bool(exact_match),
                    }
                    rows.append(_normalize_overture_record(brand_item, release))
    except LeadPipelineError:
        raise
    except Exception as exc:
        logger.exception("Overture discovery failed")
        raise LeadPipelineError("DISCOVERY_FAILED", "DuckDB could not query the current Overture Places release.", True) from exc
    finally:
        if con is not None:
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
    bbox = item.get("bbox")
    if isinstance(bbox, dict):
        bbox = {key: float(value) for key, value in bbox.items() if value is not None}
    category = item.get("taxonomy_primary") or item.get("basic_category") or ""
    hierarchy = item.get("taxonomy_hierarchy") or []
    name = str(item.get("name") or "").strip()
    raw = {
        "id": str(item.get("id") or ""),
        "name": name,
        "basic_category": item.get("basic_category"),
        "taxonomy": {"primary": category, "hierarchy": list(hierarchy), "alternates": list(item.get("taxonomy_alternates") or [])},
        "operating_status": item.get("operating_status"),
        "confidence": item.get("confidence"),
        "websites": websites,
        "emails": emails,
        "phones": phones,
        "socials": socials,
        "addresses": addresses,
        "sources": sources,
        "bbox": bbox,
    }
    website = next((str(u) for u in websites if _valid_site_url(str(u))), None)
    return {
        "brand_id": item["brand_id"],
        "source": item.get("source") or "overture_maps",
        "external_place_id": str(item.get("id") or ""),
        "name": name or "Unknown business",
        "category": category,
        "alternates": list(item.get("taxonomy_alternates") or []),
        "matched_category": item.get("matched_category"),
        "matched_is_exact": bool(item.get("matched_is_exact")),
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
                time.sleep(0.22)  # Hunter Discover is limited to five requests per second.
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
    per_brand_limit = max(1, int(config.get("max_candidates_per_brand_run", 300)))
    grouped: dict[str, list[dict]] = {}
    for row in unique.values():
        grouped.setdefault(row["brand_id"], []).append(row)
    return [row for brand_rows in grouped.values() for row in brand_rows[:per_brand_limit]], errors


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
    if host.startswith("[") and host.endswith("]"):
        host = host[1:-1]
    try:
        return str(ipaddress.ip_address(host))
    except ValueError:
        pass
    extracted = _DOMAIN_EXTRACTOR(host)
    if extracted.domain and extracted.suffix:
        return f"{extracted.domain}.{extracted.suffix}"
    # Unknown suffixes are retained as full hosts to avoid merging unrelated tenants.
    return host if "." in host else None


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


def _normalized_phone(value: str | None) -> str | None:
    digits = re.sub(r"\D", "", str(value or ""))
    return digits if len(digits) >= 7 else None


def _normalized_company_name(name: str | None, location: str | None = None) -> str:
    def tokens(value: str | None) -> list[str]:
        normalized = unicodedata.normalize("NFKD", str(value or ""))
        ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
        return re.findall(r"[a-z0-9]+", ascii_value)

    name_tokens = tokens(name)
    location_tokens = set(tokens(location))
    while name_tokens and name_tokens[-1] in location_tokens:
        name_tokens.pop()
    legal_suffixes = (
        ("private", "limited"), ("pte", "ltd"), ("sdn", "bhd"), ("limited",), ("ltd",),
        ("llc",), ("inc",), ("incorporated",), ("corp",), ("corporation",), ("plc",),
    )
    for suffix in legal_suffixes:
        if len(name_tokens) > len(suffix) and tuple(name_tokens[-len(suffix):]) == suffix:
            name_tokens = name_tokens[:-len(suffix)]
            break
    return " ".join(name_tokens)


def _account_id(brand_id: str, domain: str | None, external_place_id: str,
                name: str | None = None, country: str | None = None,
                phone: str | None = None, location: str | None = None) -> str:
    phone_key = _normalized_phone(phone)
    name_key = _normalized_company_name(name, location)
    if domain:
        identity = f"domain:{domain}"
    elif phone_key:
        identity = f"phone:{phone_key}"
    elif name_key and country:
        identity = f"name:{country.upper()}:{name_key}"
    else:
        identity = f"place:{external_place_id}"
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


def _expire_stale_contacts(connection, lead_id: str, location_id: str,
                           current_email: str | None, current_phone: str | None) -> None:
    rows = connection.execute(
        "SELECT id,contact_type,value FROM lead_contacts WHERE lead_id=%s AND location_id=%s",
        (lead_id, location_id),
    ).fetchall()
    for row in rows:
        current = current_email if row["contact_type"] == "email" else current_phone
        if row["contact_type"] == "email":
            matches = bool(current) and str(row["value"]).strip().lower() == str(current).strip().lower()
        elif row["contact_type"] == "phone":
            matches = bool(current) and _normalized_phone(row["value"]) == _normalized_phone(current)
        else:
            matches = True
        if not matches:
            connection.execute(
                "UPDATE lead_contacts SET verification_status='stale' WHERE id=%s",
                (row["id"],),
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
         candidate.get("source_release"), None, raw_data, _now()),
    )


def _sync_account(connection, lead_id: str, brand_id: str, name: str, domain: str | None,
                  website: str | None, country: str | None, category: str | None,
                  stage: str, score: int | None = None, score_version: str | None = None) -> None:
    row = connection.execute("SELECT id FROM lead_accounts WHERE id=%s", (lead_id,)).fetchone()
    if row:
        connection.execute(
            "UPDATE lead_accounts SET company_name=%s, domain=%s, website=%s, country=%s, category=%s, "
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
    # Enrich one company website once per source release even when several
    # Overture locations resolve to the same company account.
    job_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"aura-enrich:{candidate['source_release']}:{lead_id}"))
    if connection.execute("SELECT id FROM lead_jobs WHERE id = %s", (job_id,)).fetchone():
        return
    connection.execute(
        "INSERT INTO lead_jobs (id, lead_id, stage, status, attempts, payload, created_at, updated_at) "
        "VALUES (%s, %s, 'website_verify', 'pending', 0, %s, %s, %s)",
        (job_id, lead_id, json.dumps({"location_id": location_id, "url": candidate.get("url")}), _now(), _now()),
    )


def _revoke_approval_for_source_change(connection, lead_id: str, changed: bool) -> None:
    """Invalidate review before changed discovery evidence can be used for outreach."""
    if not changed:
        return
    reason = "Source data changed; human review is required again."
    connection.execute(
        "UPDATE leads SET reviewed_by=NULL, reviewed_at=NULL, review_note=%s, review_status='pending' "
        "WHERE id=%s AND review_status='approved' AND outreach_status NOT IN ('sent','sending','delivery_uncertain') "
        "AND outreach_sent_at IS NULL",
        (reason, lead_id),
    )
    connection.execute(
        "UPDATE leads SET outreach_status='not_approved', outreach_approved_by=NULL, outreach_approved_at=NULL "
        "WHERE id=%s AND outreach_status='approved' AND outreach_sent_at IS NULL",
        (lead_id,),
    )
    connection.execute(
        "UPDATE lead_accounts SET reviewed_by=NULL, reviewed_at=NULL, review_note=%s, review_status='pending', "
        "stage='needs_reverification', updated_at=%s WHERE id=%s AND review_status='approved' "
        "AND outreach_status NOT IN ('sent','sending','delivery_uncertain')",
        (reason, _now(), lead_id),
    )
    connection.execute(
        "UPDATE lead_accounts SET outreach_status='not_approved', outreach_approved_by=NULL, outreach_approved_at=NULL, "
        "stage='needs_reverification', updated_at=%s WHERE id=%s AND outreach_status='approved'",
        (_now(), lead_id),
    )


def _source_location_changed(old_location: dict | None, candidate: dict, old_domain: str | None,
                             domain: str | None, old_source: str | None) -> bool:
    if old_location is None:
        return True
    for field in ("name", "category", "location", "country", "url", "phone", "email", "operating_status"):
        old_value = old_location.get(field)
        new_value = candidate.get(field)
        if field in {"phone", "email"}:
            old_value = str(old_value or "").strip().lower()
            new_value = str(new_value or "").strip().lower()
        else:
            old_value = str(old_value or "").strip()
            new_value = str(new_value or "").strip()
        if old_value != new_value:
            return True
    if old_location.get("confidence") != candidate.get("confidence"):
        return True
    old_raw = old_location.get("raw_record") or {}
    new_raw = candidate.get("raw_record") or {}
    try:
        old_raw = json.loads(old_raw) if isinstance(old_raw, str) else old_raw
    except (json.JSONDecodeError, TypeError):
        old_raw = {}
    for field in ("taxonomy", "addresses", "websites", "emails", "phones", "socials", "operating_status", "confidence", "bbox"):
        if old_raw.get(field) != new_raw.get(field):
            return True
    if old_domain != domain:
        return True
    return old_source != (candidate.get("source") or "overture_maps")


def persist_candidate(candidate: dict) -> str | None:
    brand_id = candidate["brand_id"]
    source = candidate.get("source") or "overture_maps"
    domain = candidate.get("domain") or normalize_domain(candidate.get("url"))
    external_place_id = candidate.get("external_place_id") or candidate["name"]
    account_id = _account_id(
        brand_id, domain, external_place_id, candidate.get("name"), candidate.get("country"),
        candidate.get("phone"), candidate.get("location"),
    )
    with get_connection() as connection:
        suppressed = connection.execute(
            "SELECT id FROM lead_suppressions WHERE brand_id = %s AND ((domain = %s AND domain IS NOT NULL) OR (email = %s AND email IS NOT NULL)) LIMIT 1",
            (brand_id, domain, candidate.get("email")),
        ).fetchone()
        if suppressed:
            return None
        lead_columns = "id, source, domain, name, location, country, category, phone"
        # A stable Overture place ID remains the same business when its website changes.
        existing = None
        if source == "overture_maps" and candidate.get("external_place_id"):
            existing = connection.execute(
                "SELECT leads.id, leads.source, leads.domain, leads.name, leads.location, leads.country, leads.category, leads.phone FROM leads JOIN lead_locations "
                "ON lead_locations.lead_id=leads.id WHERE leads.brand_id=%s AND lead_locations.external_place_id=%s LIMIT 1",
                (brand_id, candidate.get("external_place_id")),
            ).fetchone()
            if existing:
                account_id = existing["id"]
        if existing is None:
            existing = connection.execute(f"SELECT {lead_columns} FROM leads WHERE id = %s", (account_id,)).fetchone()
        if existing is None:
            # Reuse a known domain account when the stable Overture ID changed.
            if domain:
                existing = connection.execute(
                    f"SELECT {lead_columns} FROM leads WHERE brand_id = %s AND domain = %s LIMIT 1", (brand_id, domain)
                ).fetchone()
            if existing:
                account_id = existing["id"]
        if existing is None and not domain:
            similar_accounts = connection.execute(
                f"SELECT {lead_columns} FROM leads WHERE brand_id=%s AND domain IS NULL",
                (brand_id,),
            ).fetchall()
            candidate_phone = _normalized_phone(candidate.get("phone"))
            if candidate_phone:
                existing = next(
                    (row for row in similar_accounts if _normalized_phone(row.get("phone")) == candidate_phone),
                    None,
                )
            if existing is None:
                candidate_name = _normalized_company_name(candidate.get("name"), candidate.get("location"))
                candidate_country = str(candidate.get("country") or "").upper()
                if candidate_name and candidate_country:
                    existing = next((
                        row for row in similar_accounts
                        if str(row.get("country") or "").upper() == candidate_country
                        and _normalized_company_name(row.get("name"), row.get("location")) == candidate_name
                    ), None)
            if existing:
                account_id = existing["id"]
        # Hunter is a secondary discovery source. Record its observation without
        # replacing a better Overture record or queuing a duplicate website crawl.
        if existing and source == "hunter_discover" and existing.get("source") == "overture_maps":
            _add_source_record(connection, account_id, None, candidate)
            _add_evidence(connection, account_id, "discovery_source", "Hunter Discover matched the configured country and keywords",
                          source, None, candidate.get("confidence"))
            return account_id
        now = _now()
        location_id = _location_id(account_id, candidate.get("external_place_id") or "", candidate["name"], candidate.get("location") or "")
        old_location = connection.execute("SELECT * FROM lead_locations WHERE id = %s", (location_id,)).fetchone()
        account_name = existing.get("name") if existing and not old_location else None
        account_location = existing.get("location") if existing and not old_location else None
        account_country = existing.get("country") if existing and not old_location else None
        account_category = existing.get("category") if existing and not old_location else None
        account_name = account_name or candidate["name"]
        account_location = account_location or candidate.get("location")
        account_country = account_country or candidate.get("country")
        account_category = account_category or candidate.get("category")
        source_changed = bool(existing) and _source_location_changed(
            old_location, candidate, existing.get("domain"), domain, existing.get("source"),
        )
        _revoke_approval_for_source_change(connection, account_id, source_changed)
        if existing:
            connection.execute(
                "UPDATE leads SET name=%s, category=%s, location=%s, url=%s, country=%s, "
                "phone=COALESCE(phone,%s), email=COALESCE(email,%s), public_email=COALESCE(public_email,%s), "
                "social_links=%s, source=%s, source_url=%s, source_release=%s, domain=%s, operating_status=%s, "
                "overture_confidence=%s, external_place_id=COALESCE(external_place_id,%s), "
                "updated_at=%s WHERE id=%s",
                (account_name, account_category, account_location, candidate.get("url"),
                 account_country, candidate.get("phone"), candidate.get("email"), candidate.get("email"),
                 json.dumps(candidate.get("social_links") or []), candidate.get("source") or "overture_maps", candidate.get("url"), candidate.get("source_release"), domain,
                 candidate.get("operating_status"), candidate.get("confidence"), candidate.get("external_place_id"), now, account_id),
            )
        else:
            connection.execute(
                "INSERT INTO leads (id, brand_id, name, category, location, url, country, phone, email, public_email, "
                "social_links, source, source_url, status, fit_score, external_place_id, domain, operating_status, "
                "overture_confidence, source_release, stage, review_status, outreach_status, contact_status, created_at, updated_at) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'discovered',0,%s,%s,%s,%s,%s,'discovered','pending','not_approved','unknown',%s,%s)",
                (account_id, brand_id, account_name, account_category, account_location,
                 candidate.get("url"), account_country, candidate.get("phone"), candidate.get("email"),
                 candidate.get("email"), json.dumps(candidate.get("social_links") or []), candidate.get("source") or "overture_maps", candidate.get("url"),
                 candidate.get("external_place_id"), domain, candidate.get("operating_status"), candidate.get("confidence"),
                 candidate.get("source_release"), now, now),
            )
        location_exists = old_location
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
        _sync_account(connection, account_id, brand_id, account_name, domain, candidate.get("url"),
                      account_country, account_category, "discovered")
        _add_source_record(connection, account_id, location_id, candidate)
        _add_contact(connection, account_id, location_id, "email", candidate.get("email"), source, None, candidate.get("confidence"))
        _add_contact(connection, account_id, location_id, "phone", candidate.get("phone"), source, None, candidate.get("confidence"))
        # Older rows from an earlier build incorrectly used the business URL as
        # the discovery source URL. Keep dataset evidence visibly source-backed.
        connection.execute(
            "UPDATE lead_source_records SET source_url=NULL WHERE lead_id=%s AND location_id=%s AND source=%s",
            (account_id, location_id, source),
        )
        connection.execute(
            "DELETE FROM lead_evidence WHERE lead_id=%s AND location_id=%s AND source=%s AND source_url IS NOT NULL",
            (account_id, location_id, source),
        )
        discovery_type = "taxonomy" if source == "overture_maps" else "discovery_source"
        discovery_value = candidate.get("category") if source == "overture_maps" else "Hunter Discover matched the configured country and keywords"
        _add_evidence(connection, account_id, discovery_type, discovery_value, source, None, candidate.get("confidence"), location_id)
        _add_evidence(connection, account_id, "country", candidate.get("country"), source, None, candidate.get("confidence"), location_id)
        _add_evidence(connection, account_id, "business_name", candidate.get("name"), source, None, candidate.get("confidence"), location_id)
        _add_evidence(connection, account_id, "business_location", candidate.get("location"), source, None, candidate.get("confidence"), location_id)
        _add_evidence(connection, account_id, "website", candidate.get("url"), source, None, candidate.get("confidence"), location_id)
        _add_evidence(connection, account_id, "email", candidate.get("email"), source, None, candidate.get("confidence"), location_id)
        _add_evidence(connection, account_id, "phone", candidate.get("phone"), source, None, candidate.get("confidence"), location_id)
        _add_evidence(connection, account_id, "operating_status", candidate.get("operating_status"), source, None, candidate.get("confidence"), location_id)
        _add_evidence(connection, account_id, "source_confidence", candidate.get("confidence"), source, None, candidate.get("confidence"), location_id)
        for social_url in candidate.get("social_links") or []:
            _add_evidence(connection, account_id, "social_url", social_url, source, None, candidate.get("confidence"), location_id)
        _enqueue_enrichment(connection, account_id, location_id, candidate)
    return account_id


def _public_addresses(host: str, port: int) -> list[tuple[int, int, int, tuple, str]]:
    try:
        resolved = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise LeadPipelineError("DNS_FAILURE", "The website domain did not resolve.") from exc
    if not resolved:
        raise LeadPipelineError("DNS_FAILURE", "The website domain did not resolve.")
    public = []
    seen = set()
    for item in resolved:
        address = ipaddress.ip_address(item[4][0].split("%", 1)[0])
        if not address.is_global:
            raise LeadPipelineError("UNSAFE_URL", "The website resolved to a non-public network address.")
        key = (item[0], item[1], item[2], item[4])
        if key not in seen:
            public.append((item[0], item[1], item[2], item[4], str(address)))
            seen.add(key)
    return public


def _checked_url(url: str) -> tuple[str, str, int, list[tuple[int, int, int, tuple, str]]]:
    if not _valid_site_url(url):
        raise LeadPipelineError("INVALID_URL", "The source record did not contain an HTTP website.")
    parsed = urlparse(url)
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise LeadPipelineError("INVALID_URL", "The website URL contains an invalid port.") from exc
    if port not in {80, 443}:
        raise LeadPipelineError("UNSAFE_URL", "Only standard HTTP and HTTPS ports are allowed.")
    host = parsed.hostname or ""
    try:
        host = host.encode("idna").decode("ascii").lower().rstrip(".")
    except UnicodeError as exc:
        raise LeadPipelineError("INVALID_URL", "The website hostname is invalid.") from exc
    try:
        ip = ipaddress.ip_address(host)
        authority_host = f"[{host}]" if ip.version == 6 else host
    except ValueError:
        authority_host = host
    default_port = 443 if parsed.scheme == "https" else 80
    authority = authority_host if port == default_port else f"{authority_host}:{port}"
    normalized = parsed._replace(netloc=authority, fragment="").geturl()
    return normalized, host, port, _public_addresses(host, port)


def _url_origin(url: str) -> tuple[str, str, int]:
    parsed = urlparse(url)
    if not parsed.hostname:
        raise ValueError("URL has no hostname")
    return parsed.scheme.lower(), parsed.hostname.encode("idna").decode("ascii").lower().rstrip("."), parsed.port or (443 if parsed.scheme.lower() == "https" else 80)


class _PinnedHTTPConnection(http.client.HTTPConnection):
    def __init__(self, host: str, port: int, address: tuple[int, int, int, tuple, str], timeout: float):
        super().__init__(host, port, timeout=timeout)
        self.pinned_address = address

    def connect(self) -> None:
        family, socktype, proto, sockaddr, _ = self.pinned_address
        sock = socket.socket(family, socktype, proto)
        sock.settimeout(self.timeout)
        try:
            sock.connect(sockaddr)
        except Exception:
            sock.close()
            raise
        self.sock = sock


class _PinnedHTTPSConnection(_PinnedHTTPConnection):
    def connect(self) -> None:
        family, socktype, proto, sockaddr, _ = self.pinned_address
        sock = socket.socket(family, socktype, proto)
        sock.settimeout(self.timeout)
        try:
            sock.connect(sockaddr)
            self.sock = ssl.create_default_context().wrap_socket(sock, server_hostname=self.host)
        except Exception:
            sock.close()
            raise


def _respect_host_delay(host: str) -> None:
    with _HOST_LOCKS_LOCK:
        host_lock = _HOST_LOCKS.setdefault(host, threading.Lock())
    with host_lock:
        delay = max(0.0, float(os.getenv("LEAD_CRAWL_DELAY_SECONDS", "0.35")))
        remaining = delay - (time.monotonic() - _HOST_LAST_FETCH.get(host, 0.0))
        if remaining > 0:
            time.sleep(remaining)
        _HOST_LAST_FETCH[host] = time.monotonic()


def _safe_fetch(url: str, *, max_bytes: int = MAX_PAGE_BYTES, redirects: int = 4,
                robots_check=None) -> tuple[str, str, int]:
    current = url
    for _ in range(redirects + 1):
        if robots_check and not robots_check(current):
            raise LeadPipelineError("ROBOTS_BLOCKED", "The destination site's robots.txt disallows this page.")
        current, host, port, addresses = _checked_url(current)
        _respect_host_delay(host)
        parsed = urlparse(current)
        path = parsed.path or "/"
        if parsed.query:
            path += "?" + parsed.query
        authority = parsed.netloc
        last_error: Exception | None = None
        for address in addresses:
            connection = _PinnedHTTPSConnection(host, port, address, timeout=12) if parsed.scheme == "https" else _PinnedHTTPConnection(host, port, address, timeout=12)
            try:
                connection.request("GET", path, headers={
                    "Host": authority,
                    "User-Agent": USER_AGENT,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.5",
                    "Connection": "close",
                })
                response = connection.getresponse()
                if response.status in {301, 302, 303, 307, 308}:
                    target = response.getheader("location")
                    if not target:
                        raise LeadPipelineError("PARSE_FAILED", "Website returned an invalid redirect.")
                    current = urljoin(current, target)
                    break
                if response.status == 403:
                    raise LeadPipelineError("HTTP_403", "Website refused the request.")
                if response.status == 404:
                    raise LeadPipelineError("HTTP_404", "Website page was not found.")
                if response.status == 429:
                    retry_after = response.getheader("retry-after", "")
                    raise LeadPipelineError("RATE_LIMITED", f"Website rate limited the request ({retry_after}).", True)
                if response.status >= 500:
                    raise LeadPipelineError("HTTP_SERVER_ERROR", "Website returned a server error.", True)
                if response.status >= 400:
                    raise LeadPipelineError("HTTP_STATUS", f"Website returned HTTP {response.status}.")
                content_type = (response.getheader("content-type") or "").lower()
                if not any(kind in content_type for kind in ("html", "xml", "text/plain")) and content_type:
                    raise LeadPipelineError("UNSUPPORTED_CONTENT", "Website response is not HTML or XML.")
                body = response.read(max_bytes)
                return body.decode("utf-8", errors="replace"), current, response.status
            except LeadPipelineError:
                raise
            except (OSError, http.client.HTTPException, ssl.SSLError) as exc:
                last_error = exc
            finally:
                connection.close()
        else:
            if isinstance(last_error, (socket.timeout, TimeoutError)):
                raise LeadPipelineError("TIMEOUT", "Website request timed out.", True) from last_error
            if last_error:
                raise LeadPipelineError("CONNECTION_ERROR", "Could not connect to the website.", True) from last_error
            raise LeadPipelineError("CONNECTION_ERROR", "Could not connect to the website.", True)
        # A redirect starts a fresh DNS check and pinned connection on the next iteration.
    raise LeadPipelineError("TOO_MANY_REDIRECTS", "Website redirected too many times.")


def _robots_parser(home_url: str) -> RobotFileParser:
    parsed = urlparse(home_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    parser = RobotFileParser()
    parser.set_url(robots_url)
    try:
        body, final_url, _ = _safe_fetch(robots_url, max_bytes=128_000, redirects=2)
        if _url_origin(final_url) != _url_origin(robots_url):
            parser.parse(["User-agent: *", "Disallow: /"])
        else:
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


def _sitemap_urls(home_url: str, robots: RobotFileParser, robots_check=None) -> list[str]:
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
            xml, _, _ = _safe_fetch(sitemap, max_bytes=500_000, redirects=2, robots_check=robots_check)
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


def _playwright_text(url: str, robots_check=None) -> str | None:
    if os.getenv("LEAD_PLAYWRIGHT_ENABLED", "false").lower() not in {"1", "true", "yes"}:
        return None
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return None

    try:
        url, host, _, addresses = _checked_url(url)
    except LeadPipelineError:
        return None
    pinned_ipv4 = next((address[4] for address in addresses if ipaddress.ip_address(address[4]).version == 4), None)
    if not pinned_ipv4:
        return None

    async def run() -> str:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    f"--host-resolver-rules=MAP {host} {pinned_ipv4},MAP * ~NOTFOUND",
                    "--no-proxy-server",
                    "--disable-background-networking",
                ],
            )
            try:
                context = await browser.new_context(service_workers="block")

                async def check_request(route):
                    try:
                        request_url = urlparse(route.request.url)
                        port = request_url.port or (443 if request_url.scheme == "https" else 80)
                        permitted = (
                            request_url.scheme in {"http", "https"}
                            and (request_url.hostname or "").encode("idna").decode("ascii").lower() == host
                            and port in {80, 443}
                            and route.request.method in {"GET", "HEAD"}
                        )
                    except (UnicodeError, ValueError):
                        permitted = False
                    if permitted and robots_check and not robots_check(route.request.url):
                        permitted = False
                    if not permitted:
                        await route.abort()
                    else:
                        await route.continue_()

                async def block_websocket(websocket):
                    await websocket.close(code=1008, reason="WebSockets are blocked during lead verification")

                await context.route("**/*", check_request)
                await context.route_web_socket("**/*", block_websocket)
                page = await context.new_page()
                await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
                return await page.locator("body").inner_text(timeout=5_000)
            finally:
                await browser.close()

    try:
        return asyncio.run(run()) or None
    except Exception:
        logger.info("Playwright could not render %s", url)
        return None


def verify_website(url: str) -> dict:
    if not url:
        return {"ok": False, "error": "NO_WEBSITE", "pages": [], "text": "", "title": "", "description": "", "emails": [], "phones": [], "services": [], "socials": []}
    _checked_url(url)
    robots = _robots_parser(url)
    robots_cache = {_url_origin(url): robots}

    def robots_allows(page_url: str) -> bool:
        try:
            origin = _url_origin(page_url)
        except (UnicodeError, ValueError):
            return False
        parser = robots_cache.get(origin)
        if parser is None:
            parser = _robots_parser(page_url)
            robots_cache[origin] = parser
        return parser.can_fetch(USER_AGENT, page_url)

    def fetch_page(page_url: str, **kwargs):
        if not robots_allows(page_url):
            raise LeadPipelineError("ROBOTS_BLOCKED", "The site's robots.txt disallows this page.")
        return _safe_fetch(page_url, robots_check=robots_allows, **kwargs)

    try:
        homepage_html, home_url, _ = fetch_page(url)
    except LeadPipelineError:
        raise
    title, description, homepage_text = _visible_text(homepage_html)
    description_source = home_url if description else None
    jsonld = _jsonld_values(_jsonld_objects(homepage_html))
    selected_urls = _internal_page_urls(home_url, homepage_html)
    selected_urls.extend(url for url in _sitemap_urls(home_url, robots, robots_allows) if url not in selected_urls)
    origin = f"{urlparse(home_url).scheme}://{urlparse(home_url).netloc}"
    selected_urls.extend(
        f"{origin}/{path}"
        for path in ("contact", "contact-us", "about", "about-us", "team", "services", "locations")
        if f"{origin}/{path}" not in selected_urls
    )
    texts = [homepage_text]
    page_texts = [{"url": home_url, "text": homepage_text}]
    all_html = [homepage_html]
    verified_urls = [home_url]
    for page_url in selected_urls[:MAX_SITE_PAGES - 1]:
        if not robots_allows(page_url):
            continue
        try:
            body, final_url, _ = fetch_page(page_url)
        except LeadPipelineError:
            continue
        _, page_description, page_text = _visible_text(body)
        texts.append(page_text)
        page_texts.append({"url": final_url, "text": page_text})
        all_html.append(body)
        verified_urls.append(final_url)
        if not description and page_description:
            description = page_description
            description_source = final_url
        for prop in _jsonld_values(_jsonld_objects(body)).items():
            key, values = prop
            jsonld[key].extend(values)
    rendered_text = ""
    if not any(texts) or len(" ".join(texts)) < 100:
        rendered_text = _playwright_text(home_url, robots_allows) or ""
        if rendered_text:
            texts.append(rendered_text)
            page_texts.append({"url": home_url, "text": rendered_text})
    html = "\n".join(all_html)
    emails = [str(v).strip().lower() for v in jsonld["emails"] if _email_syntax_ok(str(v).strip())]
    emails.extend(re.findall(r"(?i)mailto:([^?\"'\s>]+)", html))
    emails.extend(re.findall(r"(?i)[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,63}", html + " " + rendered_text))
    emails = [email for email in dict.fromkeys(unescape_html(value).strip().lower() for value in emails) if _usable_contact_email(email)]
    phones = [str(v) for v in jsonld["phones"] if v]
    phones.extend(re.findall(r"(?i)tel:([+\d][^\"'\s>]{6,})", html))
    services = list(dict.fromkeys([*jsonld["services"], *jsonld["descriptions"]]))
    email_sources: dict[str, str] = {}
    phone_sources: dict[str, str] = {}
    social_sources: dict[str, str] = {}
    service_sources: dict[str, str] = {}
    description_sources: dict[str, str] = {}
    name_sources: dict[str, str] = {}
    for page_url, page_html in zip(verified_urls, all_html):
        page_jsonld = _jsonld_values(_jsonld_objects(page_html))
        page_emails = [*page_jsonld["emails"], *re.findall(r"(?i)mailto:([^?\"'\s>]+)", page_html)]
        page_emails.extend(re.findall(r"(?i)[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,63}", page_html))
        for value in page_emails:
            normalized = unescape_html(str(value)).strip().lower()
            if _usable_contact_email(normalized):
                email_sources.setdefault(normalized, page_url)
        page_phones = [*page_jsonld["phones"], *re.findall(r"(?i)tel:([+\d][^\"'\s>]{6,})", page_html)]
        for value in page_phones:
            normalized = str(value).strip()
            if normalized:
                phone_sources.setdefault(normalized, page_url)
        for value in page_jsonld["socials"]:
            social_sources.setdefault(str(value), page_url)
        for value in page_jsonld["services"]:
            service_sources.setdefault(str(value), page_url)
        for value in page_jsonld["descriptions"]:
            description_sources.setdefault(str(value), page_url)
        for value in page_jsonld["names"]:
            name_sources.setdefault(str(value), page_url)
    for value in re.findall(r"(?i)[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,63}", rendered_text):
        normalized = unescape_html(value).strip().lower()
        if _usable_contact_email(normalized):
            email_sources.setdefault(normalized, home_url)
    return {
        "ok": True,
        "title": title,
        "name": (jsonld["names"] or [""])[0],
        "description": (jsonld["descriptions"] or [description])[0] if (jsonld["descriptions"] or [description]) else "",
        "text": " ".join(texts)[:30000],
        "page_texts": page_texts,
        "emails": emails[:20],
        "email_sources": {value: email_sources.get(value, home_url) for value in emails[:20]},
        "phones": list(dict.fromkeys(phones))[:20],
        "phone_sources": {value: phone_sources.get(value, home_url) for value in list(dict.fromkeys(phones))[:20]},
        "services": services[:30],
        "service_sources": {value: service_sources.get(value, home_url) for value in services[:30]},
        "socials": list(dict.fromkeys(jsonld["socials"]))[:20],
        "social_sources": {value: social_sources.get(value, home_url) for value in list(dict.fromkeys(jsonld["socials"]))[:20]},
        "description_source": description_sources.get((jsonld["descriptions"] or [None])[0]) or description_source or home_url,
        "name_source": name_sources.get((jsonld["names"] or [None])[0]) or home_url,
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
    exact_categories = set(config["exact_categories"])
    broad_categories = set(config["hierarchy_categories"])
    alternates = set(candidate.get("alternates") or [])
    exact_match = category if category in exact_categories else next(iter(sorted(alternates.intersection(exact_categories))), None)
    secondary_source = candidate.get("source") == "hunter_discover"
    hierarchy_match = next(iter(sorted(hierarchy.intersection(exact_categories | broad_categories))), None)
    matched_category = exact_match or candidate.get("matched_category") or hierarchy_match
    exact = bool(candidate.get("matched_is_exact", bool(exact_match)))
    broad = not exact and (
        category in broad_categories
        or bool(hierarchy.intersection(exact_categories | broad_categories))
        or bool(alternates.intersection(broad_categories))
        or secondary_source
    )
    text = " ".join((site.get("title") or "", site.get("description") or "", site.get("text") or "", " ".join(site.get("services") or []))).lower()
    matches = [term for term in config["keywords"] if term.lower() in text]
    breakdown = {
        "taxonomy_match": 35 if exact else 30 if secondary_source else 20 if broad else 0,
        "matched_category": matched_category,
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
    if secondary_source:
        reasons.append("Hunter Discover surfaced this company for the target profile.")
    elif exact:
        reasons.append(f"Overture taxonomy matches {matched_category or category}.")
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
        response = httpx.get(
            "https://api.hunter.io/v2/domain-search",
            params={"domain": domain, "api_key": key, "type": "generic", "verification_status": "valid"},
            timeout=15,
        )
        if response.status_code in {401, 403, 429}:
            _release_hunter_credit(period)
            return None
        response.raise_for_status()
        data = response.json().get("data") or {}
        emails = data.get("emails") or []
        generic = sorted(
            (
                item for item in emails
                if item.get("type") == "generic"
                and (item.get("verification") or {}).get("status") == "valid"
                and _email_syntax_ok(str(item.get("value") or ""))
            ),
            key=lambda item: int(item.get("confidence") or 0),
            reverse=True,
        )
        if not generic:
            _release_hunter_credit(period)
            return None
        found = generic[0]
        return {
            "email": str(found["value"]).lower(),
            "source_url": (found.get("sources") or [{}])[0].get("uri"),
            "confidence": float(found.get("confidence") or 0) / 100,
            "verification_status": (found.get("verification") or {}).get("status"),
        }
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


def _enrichment_requires_review(qualified: bool, evidence_changed: bool) -> bool:
    return not qualified or evidence_changed


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
    # Only use contact values supported by the current site fetch or current
    # location source record. Account-level values may be historical.
    email = site["emails"][0] if site.get("emails") else location.get("email")
    phone = site["phones"][0] if site.get("phones") else location.get("phone")
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
    if hunter_evidence and hunter_evidence.get("verification_status") == "valid":
        contact_status = "hunter_verified"
    elif email and email_mx_status(email) == "mx_valid":
        contact_status = "mx_valid"
    else:
        contact_status = "unverified" if email else "phone_only" if phone else "unavailable"
    new_name = str(site.get("name") or lead["name"])
    new_description = (site.get("description") or "")[:1200]
    new_services = site.get("services") or []
    old_social_links = lead.get("social_links") or []
    try:
        old_social_links = json.loads(old_social_links) if isinstance(old_social_links, str) else old_social_links
    except (json.JSONDecodeError, TypeError):
        old_social_links = []
    new_social_links = list(dict.fromkeys([
        *[str(value) for value in old_social_links if value],
        *[str(value) for value in site.get("socials") or [] if value],
    ]))
    new_requirements = " ".join([str(site.get("description") or ""), *[str(x) for x in new_services]])[:1000]
    old_services = lead.get("services") or []
    old_breakdown = lead.get("score_breakdown") or {}
    try:
        old_services = json.loads(old_services) if isinstance(old_services, str) else old_services
        old_breakdown = json.loads(old_breakdown) if isinstance(old_breakdown, str) else old_breakdown
    except (json.JSONDecodeError, TypeError):
        pass
    evidence_changed = any((
        int(lead.get("fit_score") or 0) != score,
        str(lead.get("status") or "") != final_status,
        str(lead.get("url") or "") != str(website_url or location.get("url") or ""),
        str(lead.get("name") or "") != new_name,
        str(lead.get("description") or "") != new_description,
        old_services != new_services,
        old_social_links != new_social_links,
        str(lead.get("requirements") or "") != new_requirements,
        str(lead.get("email") or lead.get("public_email") or "").lower() != str(email or "").lower(),
        str(lead.get("phone") or "") != str(phone or ""),
        old_breakdown != breakdown,
    ))
    require_review = _enrichment_requires_review(qualified, evidence_changed)
    with get_connection() as connection:
        _expire_stale_contacts(connection, lead["id"], location_id, email, phone)
        if site.get("ok"):
            # Replace old page citations after a successful fetch so every
            # current website field points at a page where it was observed.
            connection.execute(
                "DELETE FROM lead_evidence WHERE lead_id=%s AND location_id=%s AND source='company_website'",
                (lead["id"], location_id),
            )
        for page_url in site.get("pages") or []:
            _add_evidence(connection, lead["id"], "website_page", page_url, "company_website", page_url, 1.0, location_id)
        if site.get("title"):
            _add_evidence(connection, lead["id"], "website_title", site["title"], "company_website", website_url, 0.95, location_id)
        if site.get("description"):
            _add_evidence(connection, lead["id"], "website_description", site["description"], "company_website", site.get("description_source") or website_url, 0.9, location_id)
        if site.get("name"):
            _add_evidence(connection, lead["id"], "business_name", site["name"], "company_website", site.get("name_source") or website_url, 0.95, location_id)
        for value in new_services:
            _add_evidence(connection, lead["id"], "service", value, "company_website",
                          (site.get("service_sources") or {}).get(value) or website_url, 0.9, location_id)
        for value in site.get("socials") or []:
            _add_evidence(connection, lead["id"], "social_url", value, "company_website",
                          (site.get("social_sources") or {}).get(value) or website_url, 0.95, location_id)
        brand_config = load_config()["brands"][lead["brand_id"]]
        page_texts = site.get("page_texts") or [{"url": website_url, "text": site.get("text") or ""}]
        for page in page_texts:
            page_url = page.get("url") or website_url
            page_text = str(page.get("text") or "")
            for term in brand_config["keywords"]:
                match = re.search(r"[^.!?]*\b" + re.escape(term) + r"\b[^.!?]*[.!?]?", page_text, re.I)
                if match:
                    _add_evidence(connection, lead["id"], "fit_signal", match.group(0)[:500], "company_website", page_url, 0.9, location_id)
        for value in site.get("emails") or []:
            source_url = (site.get("email_sources") or {}).get(value) or website_url
            _add_evidence(connection, lead["id"], "email", value, "company_website", source_url, 1.0, location_id)
        for value in site.get("phones") or []:
            source_url = (site.get("phone_sources") or {}).get(value) or website_url
            _add_evidence(connection, lead["id"], "phone", value, "company_website", source_url, 1.0, location_id)
            _add_contact(connection, lead["id"], location_id, "phone", value, "company_website", source_url, 1.0, "published")
        for value in site.get("emails") or []:
            verification = email_mx_status(value)
            source_url = (site.get("email_sources") or {}).get(value) or website_url
            _add_contact(connection, lead["id"], location_id, "email", value, "company_website", source_url, 1.0,
                         "mx_valid" if verification == "mx_valid" else verification)
        if hunter_evidence:
            _add_evidence(connection, lead["id"], "email", email, "hunter", hunter_evidence.get("source_url") or "https://hunter.io", hunter_evidence.get("confidence"), location_id)
            _add_contact(connection, lead["id"], location_id, "email", email, "hunter", hunter_evidence.get("source_url") or "https://hunter.io", hunter_evidence.get("confidence"), "hunter_verified")
        revoke_predicate = (
            "(%s=1 AND (review_status='approved' OR outreach_status='approved') "
            "AND outreach_status NOT IN ('sent','sending','delivery_uncertain') AND outreach_sent_at IS NULL)"
        )
        account_revoke_predicate = (
            "(%s=1 AND (review_status='approved' OR outreach_status='approved') "
            "AND outreach_status NOT IN ('sent','sending','delivery_uncertain'))"
        )
        reset = int(require_review)
        connection.execute(
            "UPDATE leads SET url=COALESCE(%s,url), name=COALESCE(NULLIF(%s,''),name), fit_score=%s, why=%s, requirements=%s, "
            "description=%s, services=%s, social_links=%s, email=%s, public_email=%s, phone=%s, stage=%s, "
            "status=CASE WHEN status='contacted' THEN status ELSE %s END, score_version=%s, "
            "score_breakdown=%s, contact_status=%s, last_verified_at=%s, source_title=%s, "
            f"reviewed_by=CASE WHEN {revoke_predicate} THEN NULL ELSE reviewed_by END, "
            f"reviewed_at=CASE WHEN {revoke_predicate} THEN NULL ELSE reviewed_at END, "
            f"review_note=CASE WHEN {revoke_predicate} THEN %s ELSE review_note END, "
            f"outreach_approved_by=CASE WHEN {revoke_predicate} THEN NULL ELSE outreach_approved_by END, "
            f"outreach_approved_at=CASE WHEN {revoke_predicate} THEN NULL ELSE outreach_approved_at END, "
            f"outreach_status=CASE WHEN {revoke_predicate} THEN 'not_approved' ELSE outreach_status END, "
            f"review_status=CASE WHEN {revoke_predicate} THEN 'pending' ELSE review_status END, updated_at=%s WHERE id=%s",
            (website_url or location.get("url"), new_name, score, why[:1200], new_requirements,
             new_description, json.dumps(new_services), json.dumps(new_social_links), email, email, phone,
             "qualified" if qualified else "verified", final_status, SCORE_VERSION, json.dumps(breakdown), contact_status,
             _now() if site.get("ok") else None, site.get("title"),
             reset, reset, reset, "Qualification evidence changed; human review is required again.",
             reset, reset, reset, reset, _now(), lead["id"]),
        )
        connection.execute(
            "UPDATE lead_locations SET last_verified_at=%s, status=%s WHERE id=%s",
            (_now() if site.get("ok") else None, "verified" if site.get("ok") else str(site.get("error") or "unverified").lower(), location_id),
        )
        _record_score(connection, lead["id"], score, breakdown, qualified)
        _sync_account(connection, lead["id"], lead["brand_id"], new_name, lead.get("domain"),
                      website_url or location.get("url"), lead.get("country"), lead.get("category"),
                      "qualified" if qualified else "verified", score, SCORE_VERSION)
        connection.execute(
            "UPDATE lead_accounts SET reviewed_by=CASE WHEN " + account_revoke_predicate + " THEN NULL ELSE reviewed_by END, "
            "reviewed_at=CASE WHEN " + account_revoke_predicate + " THEN NULL ELSE reviewed_at END, "
            "review_note=CASE WHEN " + account_revoke_predicate + " THEN %s ELSE review_note END, "
            "outreach_approved_by=CASE WHEN " + account_revoke_predicate + " THEN NULL ELSE outreach_approved_by END, "
            "outreach_approved_at=CASE WHEN " + account_revoke_predicate + " THEN NULL ELSE outreach_approved_at END, "
            "outreach_status=CASE WHEN " + account_revoke_predicate + " THEN 'not_approved' ELSE outreach_status END, "
            "review_status=CASE WHEN " + account_revoke_predicate + " THEN 'pending' ELSE review_status END, updated_at=%s WHERE id=%s",
            (reset, reset, reset, "Qualification evidence changed; human review is required again.",
             reset, reset, reset, reset, _now(), lead["id"]),
        )


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


def _record_job_progress() -> None:
    try:
        state = _state()
        _save_state(
            jobs_progress_total=int(state.get("jobs_progress_total") or 0) + 1,
            jobs_last_progress_at=_now(),
        )
    except Exception:
        logger.exception("Could not publish lead enrichment progress")


def process_pending_jobs(max_jobs: int = 300) -> tuple[int, list[str]]:
    if not _JOB_RUN_LOCK.acquire(blocking=False):
        return 0, []
    try:
        return _process_pending_jobs(max_jobs)
    finally:
        _JOB_RUN_LOCK.release()


def _process_pending_jobs(max_jobs: int) -> tuple[int, list[str]]:
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
            _record_job_progress()
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
            _record_job_progress()
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
            _record_job_progress()
    return completed, errors


def _snapshot_tracked_places(con, release: str, ids: list[str]) -> dict[str, dict]:
    con.execute("CREATE TEMP TABLE tracked_ids(id VARCHAR)")
    con.executemany("INSERT INTO tracked_ids VALUES (?)", [(value,) for value in ids])
    path = f"{OVERTURE_S3}/release/{release}/theme=places/type=place/*"
    bbox_predicates = []
    bbox_params: list[object] = []
    for west, south, east, north in load_config()["country_bounds"].values():
        bbox_predicates.append("(p.bbox.xmax >= ? AND p.bbox.xmin <= ? AND p.bbox.ymax >= ? AND p.bbox.ymin <= ?)")
        bbox_params.extend((west, east, south, north))
    result = con.execute(
        "SELECT p.id, p.names.primary AS name, p.basic_category, p.taxonomy.primary AS taxonomy_primary, "
        "p.taxonomy.hierarchy AS taxonomy_hierarchy, p.taxonomy.alternates AS taxonomy_alternates, "
        "p.operating_status, p.confidence, p.websites, p.emails, p.phones, p.socials, p.addresses, p.sources, p.bbox "
        "FROM read_parquet(?, hive_partitioning=1) p INNER JOIN tracked_ids t ON p.id=t.id "
        f"WHERE {' OR '.join(bbox_predicates)}",
        [path, *bbox_params],
    )
    columns = [column[0] for column in result.description]
    return {str(row[0]): dict(zip(columns, row)) for row in result.fetchall()}


def _snapshot_record_changed(location: dict, record: dict, release: str) -> bool:
    try:
        old_raw = location.get("raw_record") or {}
        old_raw = json.loads(old_raw) if isinstance(old_raw, str) else old_raw
    except (json.JSONDecodeError, TypeError):
        old_raw = {}
    candidate = _normalize_overture_record(
        {**record, "brand_id": location["brand_id"], "source": "overture_maps"}, release,
    )
    if _source_location_changed(
        location, candidate, location.get("domain"), candidate.get("domain"), location.get("source"),
    ):
        return True
    new_raw = candidate.get("raw_record") or {}
    return any(
        old_raw.get(field) != new_raw.get(field)
        for field in ("taxonomy", "addresses", "websites", "emails", "phones", "socials", "operating_status", "confidence", "bbox")
    )


def _apply_changelog(release: str, previous_release: str | None = None) -> dict:
    """Mark removed Overture matches stale and changed records for re-verification."""
    try:
        import duckdb
    except ImportError:
        return {"removed": 0, "changed": 0, "complete": False}
    with get_connection() as connection:
        tracked = connection.execute(
            "SELECT ll.id, ll.lead_id, ll.external_place_id, ll.name, ll.category, ll.location, ll.country, ll.url, "
            "ll.phone, ll.email, ll.operating_status, ll.confidence, ll.raw_record, l.brand_id, l.domain, l.source "
            "FROM lead_locations ll JOIN leads l ON l.id=ll.lead_id WHERE ll.external_place_id IS NOT NULL"
        ).fetchall()
    ids = list(dict.fromkeys(str(row["external_place_id"]) for row in tracked))
    if not ids:
        return {"removed": 0, "changed": 0, "complete": True}
    try:
        parent_release = _release_parent(release)
    except LeadPipelineError:
        logger.info("Overture release parent unavailable", exc_info=True)
        return {"removed": 0, "changed": 0, "complete": False}
    use_changelog = bool(previous_release and parent_release == previous_release)
    try:
        con = _duckdb_connection(duckdb)
    except Exception:
        logger.info("Overture changelog connection unavailable", exc_info=True)
        return {"removed": 0, "changed": 0, "complete": False}
    changed: list[tuple[str, str, list[str]]] = []
    try:
        con.execute("INSTALL httpfs")
        con.execute("LOAD httpfs")
        con.execute("SET s3_region='us-west-2'")
        if use_changelog:
            con.execute("CREATE TEMP TABLE tracked_ids(id VARCHAR)")
            con.executemany("INSERT INTO tracked_ids VALUES (?)", [(value,) for value in ids])
            table = f"{OVERTURE_S3}/changelog/{release}/theme=places/type=place/change_type=*/*"
            rows = con.execute(
                "SELECT c.id, c.change_type, c.columns_changed FROM read_parquet(?, hive_partitioning=1) c "
                "INNER JOIN tracked_ids t ON c.id=t.id WHERE c.change_type IN ('removed','data_changed')",
                [table],
            ).fetchall()
            changed = [(str(row[0]), str(row[1]), row[2] or []) for row in rows]
        else:
            snapshot = _snapshot_tracked_places(con, release, ids)
            tracked_by_id: dict[str, list[dict]] = {}
            for location in tracked:
                tracked_by_id.setdefault(str(location["external_place_id"]), []).append(location)
            for place_id, locations in tracked_by_id.items():
                current = snapshot.get(place_id)
                if current is None:
                    changed.append((place_id, "removed", []))
                elif any(_snapshot_record_changed(location, current, release) for location in locations):
                    changed.append((place_id, "data_changed", ["taxonomy"]))
    except Exception:
        logger.info("Overture changelog check unavailable", exc_info=True)
        return {"removed": 0, "changed": 0, "complete": False}
    finally:
        con.close()
    removed = 0
    changed_count = 0
    try:
        with get_connection() as connection:
            for place_id, change_type, columns in changed:
                locations = connection.execute("SELECT id, lead_id FROM lead_locations WHERE external_place_id=%s", (place_id,)).fetchall()
                if change_type == "removed":
                    connection.execute("UPDATE lead_locations SET status='source_removed_pending_review' WHERE external_place_id=%s", (place_id,))
                    removed += 1
                elif not columns or set(columns).intersection({
                    "taxonomy", "basic_category", "operating_status", "addresses", "websites", "emails", "phones",
                    "names", "socials", "geometry",
                }):
                    connection.execute("UPDATE lead_locations SET status='needs_reverify' WHERE external_place_id=%s", (place_id,))
                    changed_count += 1
                else:
                    continue
                new_stage = "source_removed_pending_review" if change_type == "removed" else "needs_reverification"
                for location in locations:
                    connection.execute(
                        "UPDATE leads SET stage=%s, "
                        "reviewed_by=CASE WHEN review_status='rejected' OR outreach_status IN ('sent','sending','delivery_uncertain') OR outreach_sent_at IS NOT NULL THEN reviewed_by ELSE NULL END, "
                        "reviewed_at=CASE WHEN review_status='rejected' OR outreach_status IN ('sent','sending','delivery_uncertain') OR outreach_sent_at IS NOT NULL THEN reviewed_at ELSE NULL END, "
                        "review_note=CASE WHEN review_status='rejected' OR outreach_status IN ('sent','sending','delivery_uncertain') OR outreach_sent_at IS NOT NULL THEN review_note ELSE 'Overture source data changed; human review is required again.' END, "
                        "outreach_approved_by=CASE WHEN review_status='rejected' OR outreach_status IN ('sent','sending','delivery_uncertain') OR outreach_sent_at IS NOT NULL THEN outreach_approved_by ELSE NULL END, "
                        "outreach_approved_at=CASE WHEN review_status='rejected' OR outreach_status IN ('sent','sending','delivery_uncertain') OR outreach_sent_at IS NOT NULL THEN outreach_approved_at ELSE NULL END, "
                        "review_status=CASE WHEN review_status='rejected' OR outreach_status IN ('sent','sending','delivery_uncertain') OR outreach_sent_at IS NOT NULL THEN review_status ELSE 'pending' END, "
                        "outreach_status=CASE WHEN outreach_status IN ('sent','sending','delivery_uncertain') OR outreach_sent_at IS NOT NULL THEN outreach_status ELSE 'not_approved' END, "
                        "updated_at=%s WHERE id=%s",
                        (new_stage, _now(), location["lead_id"]),
                    )
                    connection.execute(
                        "UPDATE lead_accounts SET stage=%s, "
                        "reviewed_by=CASE WHEN review_status='rejected' OR outreach_status IN ('sent','sending','delivery_uncertain') THEN reviewed_by ELSE NULL END, "
                        "reviewed_at=CASE WHEN review_status='rejected' OR outreach_status IN ('sent','sending','delivery_uncertain') THEN reviewed_at ELSE NULL END, "
                        "review_note=CASE WHEN review_status='rejected' OR outreach_status IN ('sent','sending','delivery_uncertain') THEN review_note ELSE 'Overture source data changed; human review is required again.' END, "
                        "outreach_approved_by=CASE WHEN review_status='rejected' OR outreach_status IN ('sent','sending','delivery_uncertain') THEN outreach_approved_by ELSE NULL END, "
                        "outreach_approved_at=CASE WHEN review_status='rejected' OR outreach_status IN ('sent','sending','delivery_uncertain') THEN outreach_approved_at ELSE NULL END, "
                        "review_status=CASE WHEN review_status='rejected' OR outreach_status IN ('sent','sending','delivery_uncertain') THEN review_status ELSE 'pending' END, "
                        "outreach_status=CASE WHEN outreach_status IN ('sent','sending','delivery_uncertain') THEN outreach_status ELSE 'not_approved' END, "
                        "updated_at=%s WHERE id=%s",
                        (new_stage, _now(), location["lead_id"]),
                    )
    except Exception:
        logger.info("Could not save Overture changelog updates", exc_info=True)
        return {"removed": 0, "changed": 0, "complete": False}
    return {"removed": removed, "changed": changed_count, "complete": True}


def _hunter_discovery_due(now: datetime | None = None) -> bool:
    key = (os.getenv("HUNTER_API_KEY") or "").strip()
    enabled = os.getenv("LEAD_HUNTER_DISCOVER_ENABLED", "true").lower() not in {"0", "false", "no"}
    if not key or not enabled:
        return False
    now = now or datetime.now(timezone.utc)
    period = now.strftime("%Y-%m")
    state = _state()
    if state.get("hunter_period") != period:
        return True
    if not state.get("hunter_retry_pending"):
        return False
    try:
        last_attempt = datetime.fromisoformat(str(state.get("hunter_last_attempt_at") or ""))
        if last_attempt.tzinfo is None:
            last_attempt = last_attempt.replace(tzinfo=timezone.utc)
        retry_hours = max(1, int(os.getenv("LEAD_HUNTER_RETRY_HOURS", "6")))
        return now - last_attempt.astimezone(timezone.utc) >= timedelta(hours=retry_hours)
    except (TypeError, ValueError):
        return True


def _checkpoint_retry_due(prefix: str, now: datetime | None = None) -> bool:
    state = _state()
    if not state.get(f"{prefix}_retry_pending"):
        return False
    now = now or datetime.now(timezone.utc)
    try:
        retry_at = datetime.fromisoformat(str(state.get(f"{prefix}_retry_at") or ""))
        if retry_at.tzinfo is None:
            retry_at = retry_at.replace(tzinfo=timezone.utc)
        return now >= retry_at.astimezone(timezone.utc)
    except (TypeError, ValueError):
        return True


def _changelog_retry_due(now: datetime | None = None) -> bool:
    if not _state().get("changelog_retry_pending"):
        return False
    now = now or datetime.now(timezone.utc)
    return _checkpoint_retry_due("changelog", now)


def discover_and_enrich() -> dict:
    _set_refresh_phase("Checking the latest Overture release")
    release = latest_release()
    old_state = _state()
    old_release = old_state.get("release")
    # A release marker can survive from an interrupted/older run. Only a
    # successful scrape checkpoint proves that this release was imported.
    overture_due = old_release != release or not old_state.get("last_scraped_at")
    hunter_due = _hunter_discovery_due()
    changelog_retry_for_this_release = old_state.get("changelog_retry_release") == release
    changelog_due = old_state.get("changelog_release") != release and (
        not changelog_retry_for_this_release or _changelog_retry_due()
    )
    if not overture_due and not hunter_due and not changelog_due:
        with get_connection() as connection:
            pending = connection.execute("SELECT COUNT(*) AS total FROM lead_jobs WHERE status='pending'").fetchone()
        return {
            "release": release,
            "discovered": 0,
            "accounts": 0,
            "enriched": 0,
            "pending_jobs": int((pending or {}).get("total") or 0),
            "changelog": {"removed": 0, "changed": 0, "complete": True},
            "errors": [],
            "checkpoint_complete": True,
            "overture_attempted": False,
            "hunter_attempted": False,
            "hunter_checkpoint_complete": True,
            "changelog_attempted": False,
            "changelog_complete": True,
        }
    _set_refresh_phase("Applying the Overture change log")
    change_counts = _apply_changelog(release, old_state.get("changelog_release")) if changelog_due else {"removed": 0, "changed": 0, "complete": True}
    accounts: set[str] = set()
    errors: list[str] = []
    if changelog_due and not change_counts.get("complete"):
        errors.append("Overture changelog could not be read; its checkpoint will be retried.")
    overture_persistence_errors = 0
    hunter_persistence_errors = 0
    discovered = 0

    def persist_batch(candidates: list[dict]) -> None:
        nonlocal discovered, overture_persistence_errors, hunter_persistence_errors
        discovered += len(candidates)
        for candidate in candidates:
            try:
                account = persist_candidate(candidate)
                if account:
                    accounts.add(account)
            except Exception as exc:
                if candidate.get("source") == "hunter_discover":
                    hunter_persistence_errors += 1
                else:
                    overture_persistence_errors += 1
                errors.append(f"{exc.__class__.__name__}")
                logger.info(
                    "Could not persist %s candidate %s",
                    candidate.get("source"), candidate.get("external_place_id"), exc_info=True,
                )
        with get_connection() as connection:
            pending = connection.execute("SELECT COUNT(*) AS total FROM lead_jobs WHERE status='pending'").fetchone()
        _save_state(updated=len(accounts), pending_jobs=int((pending or {}).get("total") or 0))

    if overture_due:
        for country_code in load_config()["countries"]:
            _set_refresh_phase(f"Searching Overture Places ({country_code})")
            country_rows = overture_candidates(release, country=country_code)
            _set_refresh_phase(f"Saving {len(country_rows)} Overture matches ({country_code})")
            persist_batch(country_rows)
    hunter_errors: list[str] = []
    if hunter_due:
        _set_refresh_phase("Checking secondary company discovery")
        hunter_rows, hunter_errors = hunter_discover_candidates()
        persist_batch(hunter_rows)
        errors.extend(hunter_errors)
    _set_refresh_phase("Queueing website verification")
    with get_connection() as connection:
        pending = connection.execute("SELECT COUNT(*) AS total FROM lead_jobs WHERE status='pending'").fetchone()
    return {
        "release": release,
        "discovered": discovered,
        "accounts": len(accounts),
        "enriched": 0,
        "pending_jobs": int((pending or {}).get("total") or 0),
        "changelog": change_counts,
        "errors": errors[:10],
        "checkpoint_complete": overture_persistence_errors == 0,
        "overture_attempted": overture_due,
        "hunter_attempted": hunter_due,
        "hunter_checkpoint_complete": hunter_due and not hunter_errors and hunter_persistence_errors == 0,
        "changelog_attempted": changelog_due,
        "changelog_complete": bool(change_counts.get("complete")),
    }


def resume_pending_jobs() -> dict:
    completed, errors = process_pending_jobs(max_jobs=int(os.getenv("LEAD_MAX_JOBS_PER_RUN", "300")))
    with get_connection() as connection:
        pending = connection.execute("SELECT COUNT(*) AS total FROM lead_jobs WHERE status='pending'").fetchone()
    pending_count = int((pending or {}).get("total") or 0)
    state = _state()
    updates = {}
    if state.get("pending_jobs") != pending_count:
        updates["pending_jobs"] = pending_count
    if updates:
        _save_state(**updates)
    return {"enriched": completed, "pending_jobs": pending_count, "errors": errors[:10]}


def _start_manual_job_worker() -> None:
    """Drain queued website jobs for manual refreshes when scheduled workers are disabled."""
    global _MANUAL_JOB_WORKER_STARTED
    if _SCHEDULER_STARTED:
        return
    with _MANUAL_JOB_WORKER_LOCK:
        if _MANUAL_JOB_WORKER_STARTED:
            return
        _MANUAL_JOB_WORKER_STARTED = True

    def worker() -> None:
        global _MANUAL_JOB_WORKER_STARTED
        try:
            while True:
                result = resume_pending_jobs()
                if result["pending_jobs"] <= 0:
                    return
                if result["enriched"] == 0:
                    time.sleep(max(5, int(os.getenv("LEAD_JOB_POLL_SECONDS", "30"))))
        except Exception:
            logger.exception("Manual lead enrichment worker failed")
        finally:
            with _MANUAL_JOB_WORKER_LOCK:
                _MANUAL_JOB_WORKER_STARTED = False

    try:
        threading.Thread(target=worker, name="aura-lead-manual-jobs", daemon=True).start()
    except Exception:
        with _MANUAL_JOB_WORKER_LOCK:
            _MANUAL_JOB_WORKER_STARTED = False
        logger.exception("Could not start the manual lead enrichment worker")


def _manual_refresh_task() -> None:
    refresh()
    _start_manual_job_worker()


def _retry_checkpoint_values(prefix: str) -> dict:
    state = _state()
    attempts = int(state.get(f"{prefix}_retry_attempts") or 0) + 1
    delay = RETRY_DELAYS[min(attempts - 1, len(RETRY_DELAYS) - 1)]
    return {
        f"{prefix}_retry_pending": True,
        f"{prefix}_retry_attempts": attempts,
        f"{prefix}_retry_at": (datetime.now(timezone.utc) + timedelta(seconds=delay)).isoformat(),
    }


def refresh(*, force: bool = False) -> dict:
    global _RUNNING
    with _RUN_LOCK:
        if _RUNNING:
            return get_status()
        _RUNNING = True
    started = _now()
    try:
        _save_state(
            last_error=None,
            updated=0,
            refreshing=True,
            refresh_started_at=started,
            refresh_phase="Starting source discovery",
        )
        result = discover_and_enrich()
        _set_refresh_phase("Finishing discovery and queuing website checks")
        values = {
            "updated": result["accounts"], "pending_jobs": result["pending_jobs"],
            "last_error": "; ".join(result["errors"]) or None,
            "last_run": started, "last_release_checked_at": _now(), "changelog": result["changelog"],
        }
        if result.get("overture_attempted") and result.get("checkpoint_complete", False):
            values.update(
                last_scraped_at=_now(), release=result["release"],
                discovery_retry_pending=False, discovery_retry_attempts=0, discovery_retry_at=None,
            )
        elif result.get("overture_attempted") and not result.get("checkpoint_complete", False):
            values["last_error"] = values["last_error"] or "Some candidates could not be saved; the Overture release will be retried."
            values.update(_retry_checkpoint_values("discovery"))
        if result.get("changelog_attempted"):
            if result.get("changelog_complete"):
                values.update(
                    changelog_release=result["release"], changelog_retry_release=None,
                    changelog_retry_pending=False, changelog_retry_attempts=0, changelog_retry_at=None,
                )
            else:
                retry_values = _retry_checkpoint_values("changelog")
                values.update(retry_values)
                values["changelog_retry_release"] = result["release"]
        if result.get("hunter_attempted"):
            values.update(
                hunter_period=datetime.now(timezone.utc).strftime("%Y-%m"),
                hunter_retry_pending=not result.get("hunter_checkpoint_complete", False),
                hunter_last_attempt_at=_now(),
            )
        state = _save_state(**values)
        return {**get_status(), **result, **{"last_error": state.get("last_error")}}
    except LeadPipelineError as exc:
        try:
            _save_state(
                last_error=f"{exc.code}: {exc}", pending_jobs=_pending_job_count(),
                **_retry_checkpoint_values("discovery"),
            )
        except Exception:
            logger.exception("Could not save the Overture retry status")
        return get_status()
    except Exception as exc:
        logger.exception("Lead refresh failed unexpectedly")
        try:
            _save_state(
                last_error=f"REFRESH_FAILED: {exc.__class__.__name__}", pending_jobs=_pending_job_count(),
                **_retry_checkpoint_values("discovery"),
            )
        except Exception:
            logger.exception("Could not save the failed Overture refresh status")
        return get_status()
    finally:
        try:
            _save_state(refreshing=False, refresh_phase=None, refresh_finished_at=_now())
        except Exception:
            logger.exception("Could not clear the Overture refresh status")
        finally:
            with _RUN_LOCK:
                _RUNNING = False


def _is_stale() -> bool:
    state = _state()
    if state.get("discovery_retry_pending"):
        return _checkpoint_retry_due("discovery")
    # A catalog check is not an initial discovery. Ensure the first import is
    # attempted even when legacy state already has a recent release check.
    if not state.get("last_scraped_at"):
        return True
    last = state.get("last_release_checked_at") or state.get("last_scraped_at")
    if not last:
        return True
    try:
        return datetime.now(timezone.utc) - datetime.fromisoformat(last) > timedelta(hours=int(os.getenv("LEAD_REFRESH_HOURS", "720")))
    except ValueError:
        return True


def start_scheduler() -> None:
    global _SCHEDULER_STARTED
    if os.getenv("AURA_LEAD_REFRESH", "true").lower() in {"0", "false", "no"} or os.getenv("PYTEST_CURRENT_TEST"):
        return
    with _SCHEDULER_LOCK:
        if _SCHEDULER_STARTED:
            return
        _SCHEDULER_STARTED = True

    import threading
    def refresh_loop() -> None:
        while True:
            try:
                if (
                    _is_stale()
                    or _hunter_discovery_due()
                    or _changelog_retry_due()
                    or _checkpoint_retry_due("discovery")
                ):
                    refresh()
            except Exception:
                logger.exception("Lead discovery scheduler failed")
            time.sleep(max(60, int(os.getenv("LEAD_REFRESH_POLL_SECONDS", "300"))))

    def jobs_loop() -> None:
        while True:
            try:
                resume_pending_jobs()
            except Exception:
                logger.exception("Lead enrichment worker failed")
            time.sleep(max(5, int(os.getenv("LEAD_JOB_POLL_SECONDS", "30"))))

    threading.Thread(target=refresh_loop, name="aura-lead-refresh", daemon=True).start()
    threading.Thread(target=jobs_loop, name="aura-lead-jobs", daemon=True).start()


def _decode_lead_row(row: dict) -> dict:
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
    return row


def _lead_cursor_filter_key(brand_id: str | None, search: str | None, contact: str, sort: str) -> str:
    filters = json.dumps(
        {"brand": brand_id, "search": search, "contact": contact, "sort": sort},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(filters.encode("utf-8")).hexdigest()[:24]


def _encode_lead_cursor(row: dict, sort: str, filter_key: str) -> str:
    position = {"name": row["name"], "id": row["id"]}
    if sort == "fit":
        position["fit_score"] = int(row["fit_score"] or 0)
    payload = json.dumps(
        {"v": 1, "sort": sort, "filter_key": filter_key, "position": position},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_lead_cursor(cursor: str, sort: str, filter_key: str) -> dict:
    try:
        payload = json.loads(base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4)))
        if not isinstance(payload, dict):
            raise ValueError
        position = payload.get("position")
        if not isinstance(position, dict):
            raise ValueError
        if payload.get("v") != 1 or payload.get("sort") != sort or payload.get("filter_key") != filter_key:
            raise ValueError
        if not isinstance(position.get("name"), str) or not isinstance(position.get("id"), str):
            raise ValueError
        if sort == "fit" and (isinstance(position.get("fit_score"), bool) or not isinstance(position.get("fit_score"), int)):
            raise ValueError
        return position
    except (ValueError, TypeError, KeyError, UnicodeDecodeError, json.JSONDecodeError, binascii.Error) as exc:
        raise ValueError("The lead page cursor is invalid or belongs to different filters.") from exc


def list_lead_page(
    *,
    brand_id: str | None = None,
    search: str | None = None,
    contact: str = "all",
    sort: str = "fit",
    limit: int = 40,
    cursor: str | None = None,
) -> dict:
    """Return a bounded keyset page; never scan and serialize the whole lead table."""
    if contact not in {"all", "email", "phone", "reachable"}:
        raise ValueError("Contact filter must be all, email, phone, or reachable.")
    if sort not in {"fit", "name"}:
        raise ValueError("Lead sort must be fit or name.")
    if not 1 <= limit <= 100:
        raise ValueError("Lead page size must be between 1 and 100.")

    # Prefix matching allows common B-tree indexes to narrow company and domain searches.
    normalized_search = (search or "").strip().replace("%", "").replace("_", "").replace("\\", " ")
    normalized_search = re.sub(r"\s+", " ", normalized_search) or None
    if normalized_search is not None and len(normalized_search) < 2:
        raise ValueError("Search must contain at least two characters.")
    if normalized_search is not None and len(normalized_search) > 100:
        raise ValueError("Search must be 100 characters or fewer.")

    filter_key = _lead_cursor_filter_key(brand_id, normalized_search, contact, sort)
    position = _decode_lead_cursor(cursor, sort, filter_key) if cursor else None
    clauses: list[str] = []
    params: list[object] = []
    if brand_id:
        clauses.append("l.brand_id=%s")
        params.append(brand_id)
    if normalized_search:
        clauses.append("(l.name LIKE %s OR l.domain LIKE %s)")
        prefix = f"{normalized_search}%"
        params.extend((prefix, prefix))
    if contact == "email":
        clauses.append("COALESCE(NULLIF(TRIM(l.email), ''), NULLIF(TRIM(l.public_email), '')) IS NOT NULL")
    elif contact == "phone":
        clauses.append("NULLIF(TRIM(l.phone), '') IS NOT NULL")
    elif contact == "reachable":
        clauses.append(
            "(COALESCE(NULLIF(TRIM(l.email), ''), NULLIF(TRIM(l.public_email), '')) IS NOT NULL "
            "OR NULLIF(TRIM(l.phone), '') IS NOT NULL)"
        )
    if position:
        if sort == "fit":
            clauses.append(
                "(l.fit_score < %s OR (l.fit_score = %s AND l.name > %s) "
                "OR (l.fit_score = %s AND l.name = %s AND l.id > %s))"
            )
            score = position["fit_score"]
            params.extend((score, score, position["name"], score, position["name"], position["id"]))
        else:
            clauses.append("(l.name > %s OR (l.name = %s AND l.id > %s))")
            params.extend((position["name"], position["name"], position["id"]))

    order = "l.fit_score DESC, l.name ASC, l.id ASC" if sort == "fit" else "l.name ASC, l.id ASC"
    query = (
        "SELECT l.*, (SELECT COUNT(*) FROM lead_locations AS locations WHERE locations.lead_id=l.id) "
        "AS location_count, (SELECT COUNT(*) FROM lead_evidence AS evidence WHERE evidence.lead_id=l.id) "
        "AS evidence_count FROM leads AS l"
    )
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += f" ORDER BY {order} LIMIT %s"
    params.append(limit + 1)

    with get_connection() as connection:
        rows = connection.execute(query, tuple(params)).fetchall()
    has_more = len(rows) > limit
    page_rows = [_decode_lead_row(row) for row in rows[:limit]]
    next_cursor = _encode_lead_cursor(page_rows[-1], sort, filter_key) if has_more and page_rows else None
    return {"items": page_rows, "has_more": has_more, "next_cursor": next_cursor, "limit": limit}


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
        lead = connection.execute(
            "SELECT id, brand_id, domain, email, public_email, fit_score, status, stage, outreach_status, outreach_sent_at "
            "FROM leads WHERE id=%s", (lead_id,),
        ).fetchone()
        if not lead:
            return None
        if decision == "approved" and (
            lead.get("status") != "qualified"
            or lead.get("stage") != "qualified"
            or int(lead.get("fit_score") or 0) < int(load_config().get("qualification_score", 75))
        ):
            raise ValueError("Only qualified leads can be approved for outreach")
        if lead.get("outreach_status") in {"sent", "sending", "delivery_uncertain"} or lead.get("outreach_sent_at"):
            raise ValueError("This lead already has a sent or unresolved outreach attempt")
        result = connection.execute(
            "UPDATE leads SET review_status=%s, reviewed_by=%s, reviewed_at=%s, review_note=%s, "
            "outreach_status=%s, outreach_approved_by=%s, outreach_approved_at=%s, updated_at=%s WHERE id=%s "
            "AND outreach_status NOT IN ('sent','sending','delivery_uncertain') AND outreach_sent_at IS NULL "
            "AND (%s!='approved' OR (status='qualified' AND stage='qualified' AND fit_score >= %s "
            "AND outreach_status NOT IN ('sent','sending','delivery_uncertain') AND outreach_sent_at IS NULL "
            "AND NOT EXISTS (SELECT 1 FROM lead_suppressions s WHERE s.brand_id=leads.brand_id "
            "AND ((s.domain=leads.domain AND s.domain IS NOT NULL) OR "
            "(s.email=LOWER(COALESCE(leads.email,leads.public_email,'')) AND s.email IS NOT NULL)))))",
            (decision, reviewer[:255], _now(), (note or "")[:2000], "approved" if decision == "approved" else "not_approved",
             reviewer[:255] if decision == "approved" else None, _now() if decision == "approved" else None, _now(), lead_id,
             decision, int(load_config().get("qualification_score", 75))),
        )
        if result.rowcount != 1:
            raise ValueError("Lead qualification or suppression changed. Refresh the lead before approving it.")
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
            connection.execute("UPDATE leads SET review_status='rejected', outreach_status=CASE WHEN outreach_status IN ('sent','sending','delivery_uncertain') THEN outreach_status ELSE 'not_approved' END, outreach_approved_by=NULL, outreach_approved_at=NULL, reviewed_by=%s, reviewed_at=%s, review_note=%s WHERE brand_id=%s AND domain=%s", (actor[:255], _now(), reason or "Suppressed", brand_id, normalized_domain))
            connection.execute("UPDATE lead_accounts SET review_status='rejected', reviewed_by=%s, reviewed_at=%s, review_note=%s, outreach_status=CASE WHEN outreach_status IN ('sent','sending','delivery_uncertain') THEN outreach_status ELSE 'not_approved' END, outreach_approved_by=NULL, outreach_approved_at=NULL WHERE brand_id=%s AND domain=%s", (actor[:255], _now(), reason or "Suppressed", brand_id, normalized_domain))
        if email:
            normalized_email = email.strip().lower()
            connection.execute("UPDATE leads SET review_status='rejected', outreach_status=CASE WHEN outreach_status IN ('sent','sending','delivery_uncertain') THEN outreach_status ELSE 'not_approved' END, outreach_approved_by=NULL, outreach_approved_at=NULL, reviewed_by=%s, reviewed_at=%s, review_note=%s WHERE brand_id=%s AND lower(COALESCE(email, public_email,''))=%s", (actor[:255], _now(), reason or "Suppressed", brand_id, normalized_email))
            connection.execute("UPDATE lead_accounts SET review_status='rejected', reviewed_by=%s, reviewed_at=%s, review_note=%s, outreach_status=CASE WHEN outreach_status IN ('sent','sending','delivery_uncertain') THEN outreach_status ELSE 'not_approved' END, outreach_approved_by=NULL, outreach_approved_at=NULL WHERE brand_id=%s AND id IN (SELECT id FROM leads WHERE brand_id=%s AND lower(COALESCE(email, public_email,''))=%s)", (actor[:255], _now(), reason or "Suppressed", brand_id, brand_id, normalized_email))
    return suppression_id


def approve_outreach(lead_id: str, actor: str) -> dict | None:
    return review_lead(lead_id, "approved", actor, "Outreach explicitly approved")


def mark_outreach_sent(lead_id: str) -> None:
    with get_connection() as connection:
        updated = connection.execute("UPDATE leads SET outreach_status='sent', outreach_sent_at=%s, status='contacted', updated_at=%s WHERE id=%s AND outreach_status='sending'", (_now(), _now(), lead_id))
        if updated.rowcount != 1:
            raise RuntimeError("The outreach send claim was lost before delivery could be recorded")
        connection.execute("UPDATE lead_accounts SET outreach_status='sent', updated_at=%s WHERE id=%s", (_now(), lead_id))


def claim_outreach_send(lead_id: str, expected_email: str, expected_domain: str) -> bool:
    with get_connection() as connection:
        result = connection.execute(
            "UPDATE leads SET outreach_status='sending', updated_at=%s WHERE id=%s AND review_status='approved' AND outreach_status='approved' "
            "AND status='qualified' AND stage='qualified' AND fit_score >= %s AND outreach_sent_at IS NULL "
            "AND LOWER(COALESCE(email,public_email,''))=%s AND COALESCE(domain,'')=%s "
            "AND NOT EXISTS (SELECT 1 FROM lead_suppressions s WHERE s.brand_id=leads.brand_id "
            "AND ((s.domain=leads.domain AND s.domain IS NOT NULL) OR "
            "(s.email=LOWER(COALESCE(leads.email,leads.public_email,'')) AND s.email IS NOT NULL)))",
            (_now(), lead_id, int(load_config().get("qualification_score", 75)), expected_email.lower(), expected_domain.lower()),
        )
        claimed = result.rowcount == 1
        if claimed:
            connection.execute("UPDATE lead_accounts SET outreach_status='sending', updated_at=%s WHERE id=%s AND outreach_status='approved'", (_now(), lead_id))
        return claimed


def mark_outreach_failed(lead_id: str) -> None:
    with get_connection() as connection:
        connection.execute("UPDATE leads SET outreach_status='send_failed', updated_at=%s WHERE id=%s AND outreach_status='sending'", (_now(), lead_id))
        connection.execute("UPDATE lead_accounts SET outreach_status='send_failed', updated_at=%s WHERE id=%s AND outreach_status='sending'", (_now(), lead_id))


def mark_outreach_uncertain(lead_id: str) -> None:
    """Prevent a duplicate send when SMTP or post-send persistence is ambiguous."""
    with get_connection() as connection:
        connection.execute("UPDATE leads SET outreach_status='delivery_uncertain', updated_at=%s WHERE id=%s AND outreach_status='sending'", (_now(), lead_id))
        connection.execute("UPDATE lead_accounts SET outreach_status='delivery_uncertain', updated_at=%s WHERE id=%s AND outreach_status='sending'", (_now(), lead_id))


def hunter_remaining() -> int:
    period = datetime.now(timezone.utc).strftime("%Y-%m")
    limit = max(0, int(os.getenv("LEAD_HUNTER_MONTHLY_CREDIT_LIMIT", "45")))
    with get_connection() as connection:
        row = connection.execute("SELECT used FROM lead_provider_usage WHERE provider='hunter' AND period=%s", (period,)).fetchone()
    return max(0, limit - int((row or {}).get("used") or 0))
