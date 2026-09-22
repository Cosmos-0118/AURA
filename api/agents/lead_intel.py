"""Daily web discovery for Lead Intelligence.

Product searches find company sites and public posts. Name, fit score, contact
details, and the reason on the dashboard come from those public pages.
"""

from __future__ import annotations

import json
import logging
import os
import re
import socket
import threading
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from urllib.parse import urljoin, urlparse

import httpx

try:
    from ..db import get_connection
except ImportError:
    from db import get_connection

logger = logging.getLogger("aura.lead_intel")

REFRESH_HOURS = 24
SEARCH_HOST = "api.search.tinyfish.ai"
SEARCH_URL = f"https://{SEARCH_HOST}"
MAX_CANDIDATES = 60
RESULTS_PER_QUERY = 8
_STATE_PATH = Path(__file__).resolve().parents[2] / ".aura" / "lead-refresh.json"
_LEADS_PATH = Path(__file__).resolve().parents[2] / ".aura" / "leads.json"
_LOCK = threading.Lock()
_DNS_LOCK = threading.Lock()
_RUNNING = False

# Search regions only. Companies are whatever TinyFish returns.
LOCATIONS = ("US", "GB", "AE", "IN", "SG", "MY", "AU")
SKIP_HOSTS = {
    "google.com",
    "bing.com",
    "duckduckgo.com",
    "wikipedia.org",
    "facebook.com",
    "instagram.com",
    "youtube.com",
    "pinterest.com",
    "tinyfish.ai",
}

QUERIES: list[dict[str, str]] = [
    {
        "brand_id": "jade",
        "query": "jewellery manufacturer wholesale",
        "domain_type": "web",
        "purpose": "Find jewellery businesses that may need specialist stock and transit cover",
    },
    {
        "brand_id": "jade",
        "query": "luxury watch retailer",
        "domain_type": "web",
        "purpose": "Find watch retailers that may need specialist high-value cover",
    },
    {
        "brand_id": "jade",
        "query": "site:linkedin.com/posts jewellery wholesale OR watch retailer",
        "domain_type": "web",
        "purpose": "Find public posts about jewellery and watch businesses",
    },
    {
        "brand_id": "doctorshield",
        "query": "private hospital group",
        "domain_type": "web",
        "purpose": "Find private hospitals that may need professional indemnity",
    },
    {
        "brand_id": "doctorshield",
        "query": "specialist clinic aesthetic clinic",
        "domain_type": "web",
        "purpose": "Find clinics that may need professional indemnity",
    },
    {
        "brand_id": "doctorshield",
        "query": "site:linkedin.com/posts medical indemnity OR private hospital",
        "domain_type": "web",
        "purpose": "Find public posts about clinics and medical indemnity",
    },
    {
        "brand_id": "jaguar",
        "query": "cash in transit company",
        "domain_type": "web",
        "purpose": "Find cash-in-transit companies that may need secure logistics support",
    },
    {
        "brand_id": "jaguar",
        "query": "valuables logistics armored transport",
        "domain_type": "web",
        "purpose": "Find valuables logistics firms that may need secure transit support",
    },
    {
        "brand_id": "jaguar",
        "query": "site:linkedin.com/posts cash in transit",
        "domain_type": "web",
        "purpose": "Find public posts about cash-in-transit and secure logistics",
    },
    {
        "brand_id": "jade",
        "query": "jewellery retailer",
        "domain_type": "news",
        "purpose": "Find news about jewellery businesses",
    },
    {
        "brand_id": "doctorshield",
        "query": "private hospital clinic",
        "domain_type": "news",
        "purpose": "Find news about private hospitals and clinics",
    },
    {
        "brand_id": "jaguar",
        "query": "cash in transit logistics",
        "domain_type": "news",
        "purpose": "Find news about cash-in-transit companies",
    },
]

KEYWORDS = {
    "jade": ("jewellery", "jewelry", "jeweller", "gold", "diamond", "watch", "retail", "wholesale"),
    "doctorshield": ("hospital", "clinic", "doctor", "medical", "surgery", "specialist", "patient", "healthcare"),
    "jaguar": ("transit", "logistics", "security", "vault", "valuables", "cash", "armored", "armoured"),
}

COUNTRY_WORDS = (
    ("malaysia", "Malaysia"),
    ("singapore", "Singapore"),
    ("dubai", "UAE"),
    ("emirates", "UAE"),
    ("united kingdom", "UK"),
    ("london", "UK"),
    ("india", "India"),
    ("chennai", "India"),
    ("united states", "USA"),
    ("minnesota", "USA"),
)


def _load_state() -> dict:
    try:
        return json.loads(_STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _save_state(state: dict) -> None:
    _STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STATE_PATH.write_text(json.dumps(state), encoding="utf-8")


def refresh_status() -> dict:
    state = _load_state()
    return {
        "refreshing": _RUNNING,
        "configured": key_configured(),
        "last_scraped_at": state.get("last_scraped_at"),
        "last_error": state.get("last_error"),
        "updated": state.get("updated", 0),
        "watched": len(QUERIES),
    }


def tinyfish_key() -> str:
    value = (os.getenv("TinyFish_API_KEY") or os.getenv("TINYFISH_API_KEY") or "").strip().strip('"').strip("'")
    if not value or value.startswith("your_"):
        return ""
    return value


def key_configured() -> bool:
    return bool(tinyfish_key())


def _host(url: str) -> str:
    host = urlparse(url).netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _skip_host(host: str) -> bool:
    return any(host == skip or host.endswith(f".{skip}") for skip in SKIP_HOSTS)


def _result_identity(url: str) -> str:
    host = _host(url)
    if host.endswith("linkedin.com"):
        return url.split("?", 1)[0].rstrip("/")
    return host


def _needs_company_lookup(url: str, domain_type: str) -> bool:
    return domain_type == "news" or _host(url).endswith("linkedin.com")


def unique_results(results: list[dict]) -> list[dict]:
    """Drop skipped sites and duplicate company domains. LinkedIn posts stay separate."""
    seen: set[str] = set()
    kept: list[dict] = []
    for item in results:
        url = str(item.get("url") or "")
        host = _host(url)
        if not url or not host or _skip_host(host):
            continue
        identity = _result_identity(url)
        if identity in seen:
            continue
        seen.add(identity)
        kept.append(item)
    return kept


def _tinyfish_get(params: dict) -> httpx.Response:
    """TinyFish answers on IPv4. This network resets the IPv6 route."""
    with _DNS_LOCK:
        original = socket.getaddrinfo

        def prefer_ipv4(host, port, family=0, type=0, proto=0, flags=0):
            if host == SEARCH_HOST:
                family = socket.AF_INET
            return original(host, port, family, type, proto, flags)

        socket.getaddrinfo = prefer_ipv4
        try:
            return httpx.get(
                SEARCH_URL,
                params=params,
                headers={"X-API-Key": tinyfish_key(), "Accept": "application/json"},
                timeout=35.0,
            )
        finally:
            socket.getaddrinfo = original


def _search_problem(response: httpx.Response) -> str | None:
    if response.status_code == 401:
        return "API key was rejected"
    if response.status_code == 402:
        return "Search API access is required"
    if response.status_code == 429:
        return "rate limit reached"
    if response.status_code >= 400:
        return f"HTTP {response.status_code}"
    return None


def search_web(query: str, purpose: str, location: str, domain_type: str) -> list[dict]:
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            response = _tinyfish_get(
                {
                    "query": query,
                    "purpose": purpose,
                    "location": location,
                    "language": "en",
                    "domain_type": domain_type,
                }
            )
            problem = _search_problem(response)
            if problem:
                raise RuntimeError(problem)
            payload = response.json()
            results = payload.get("results") if isinstance(payload, dict) else None
            if not isinstance(results, list):
                return []
            return results[:RESULTS_PER_QUERY]
        except RuntimeError:
            raise
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(0.4)
    if last_error is None:
        return []
    raise last_error


def discover_candidates(
    on_candidate: Callable[[dict], None] | None = None,
    on_error: Callable[[str], None] | None = None,
) -> tuple[list[dict], list[str]]:
    found: list[dict] = []
    seen: set[str] = set()
    errors: list[str] = []
    for location in LOCATIONS:
        for spec in QUERIES:
            if len(found) >= MAX_CANDIDATES:
                return found, errors
            try:
                results = search_web(spec["query"], spec["purpose"], location, spec["domain_type"])
            except Exception as exc:
                detail = str(exc).strip().splitlines()[0][:80] if str(exc).strip() else exc.__class__.__name__
                message = f"{spec['query'][:40]}: {detail}"
                if message not in errors:
                    errors.append(message)
                    if on_error is not None:
                        on_error(message)
                logger.info("Search skipped (%s)", exc.__class__.__name__)
                if len(errors) >= 3 and not found:
                    return found, errors
                continue
            added = 0
            for item in unique_results(results):
                identity = _result_identity(str(item.get("url") or ""))
                if identity in seen:
                    continue
                seen.add(identity)
                candidate = {
                    "brand_id": spec["brand_id"],
                    "domain_type": spec["domain_type"],
                    "location": location,
                    "url": item.get("url"),
                    "title": item.get("title") or "",
                    "snippet": item.get("snippet") or "",
                }
                found.append(candidate)
                if on_candidate is not None:
                    on_candidate(candidate)
                added += 1
                if added >= 3 or len(found) >= MAX_CANDIDATES:
                    break
            time.sleep(0.2)
    return found, errors


def _company_site(name: str, location: str) -> str | None:
    if len(name) < 2:
        return None
    try:
        results = search_web(
            f"{name} official website",
            "Find the company website for a discovered business",
            location,
            "web",
        )
    except Exception:
        return None
    for item in results:
        url = str(item.get("url") or "")
        host = _host(url)
        if url and host and not _skip_host(host) and not host.endswith("linkedin.com"):
            return url
    return None


def build_lead(
    brand_id: str,
    source_url: str,
    source_title: str,
    snippet: str,
    page: dict,
    market: str = "",
) -> dict | None:
    blob = f"{source_title} {snippet} {page.get('description') or ''} {page.get('text') or ''}"
    score, why = _score(brand_id, blob)
    if score <= 20:
        return None
    company_url = page.get("company_url") or source_url
    region = {"US": "USA", "GB": "UK", "AE": "UAE", "IN": "India", "SG": "Singapore", "MY": "Malaysia", "AU": "Australia"}.get(market, market)
    return {
        "id": _lead_id(brand_id, company_url),
        "brand_id": brand_id,
        "name": _company_name(str(page.get("title") or source_title), company_url),
        "url": company_url,
        "country": _country(blob, region),
        "fit_score": score,
        "why": why,
        "email": page.get("email"),
        "phone": page.get("phone"),
        "requirements": _requirements(
            brand_id,
            str(page.get("description") or snippet),
            str(page.get("text") or snippet),
        ),
        "source_url": source_url,
        "source_title": source_title,
    }


def _visible_text(html: str) -> tuple[str, str, str]:
    cleaned = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
    cleaned = re.sub(r"(?is)<style.*?>.*?</style>", " ", cleaned)
    title_match = re.search(r"(?is)<title[^>]*>(.*?)</title>", cleaned)
    desc_match = re.search(
        r"(?is)<meta[^>]+name=[\"']description[\"'][^>]+content=[\"'](.*?)[\"']",
        cleaned,
    )
    if not desc_match:
        desc_match = re.search(
            r"(?is)<meta[^>]+content=[\"'](.*?)[\"'][^>]+name=[\"']description[\"']",
            cleaned,
        )
    title = unescape(re.sub(r"\s+", " ", title_match.group(1)).strip()) if title_match else ""
    description = unescape(re.sub(r"\s+", " ", desc_match.group(1)).strip()) if desc_match else ""
    text = re.sub(r"(?is)<[^>]+>", " ", cleaned)
    text = unescape(re.sub(r"\s+", " ", text)).strip()
    return title[:180], description[:400], text[:5000]


def _company_name(title: str, url: str) -> str:
    part = re.split(r"\s[|\-–—:]\s", title)[0].strip() if title else ""
    if len(part) < 2:
        host = url.split("//", 1)[-1].split("/")[0].removeprefix("www.")
        part = host.split(".")[0].replace("-", " ").title()
    return part[:120]


def _country(text: str, market: str) -> str:
    lowered = text.lower()
    for word, country in COUNTRY_WORDS:
        if word in lowered:
            return country
    return market


def _score(brand_id: str, text: str) -> tuple[int, str]:
    hits = [word for word in KEYWORDS[brand_id] if word in text.lower()]
    if not hits:
        return 20, "Public homepage did not mention this brand's audience."
    score = min(96, 40 + len(hits) * 8)
    shown = ", ".join(hits[:4])
    return score, f"Public homepage mentions {shown}."


_EMAIL_RE = re.compile(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", re.I)
_PHONE_RE = re.compile(r"(?:\+\d{1,3}[\s().-]*)(?:\d[\s().-]*){7,14}\d")
_SKIP_EMAIL = ("example.", "sentry", "wixpress", "schema.org", "godaddy", "cloudflare", "noreply", "no-reply")


def _fetch_html(url: str) -> str:
    response = httpx.get(
        url,
        timeout=8.0,
        follow_redirects=True,
        headers={"User-Agent": "AURA-LeadIntelligence/0.1 (public page check)"},
    )
    response.raise_for_status()
    return response.text


def _published_email(html: str) -> str | None:
    found: list[str] = []
    for raw in re.findall(r"mailto:([^?\"'\s>]+)", html, flags=re.I) + _EMAIL_RE.findall(html):
        email = unescape(raw).strip().lower().strip(".")
        if "@" not in email or any(skip in email for skip in _SKIP_EMAIL):
            continue
        if email.split("@", 1)[1].endswith((".png", ".jpg", ".svg", ".webp")):
            continue
        found.append(email)
    if not found:
        return None

    def rank(email: str) -> int:
        local = email.split("@", 1)[0]
        if local in {"info", "contact", "hello", "enquiries", "enquiry", "customerservice", "care", "sales"}:
            return 0
        if any(word in local for word in ("privacy", "career", "job", "press", "media")):
            return 2
        return 1

    return sorted(set(found), key=rank)[0]


def _published_phone(html: str) -> str | None:
    tel = re.search(r"tel:([+\d][^\"'\s>]{6,})", html, flags=re.I)
    if tel:
        return re.sub(r"\s+", " ", unescape(tel.group(1))).strip()[:40]
    match = _PHONE_RE.search(unescape(re.sub(r"<[^>]+>", " ", html)))
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(0)).strip()[:40]


def _contact_page(html: str, base_url: str) -> str | None:
    for href in re.findall(r"href=[\"']([^\"']+)[\"']", html, flags=re.I):
        if href.startswith(("mailto:", "tel:", "#", "javascript:")):
            continue
        if "contact" not in href.lower():
            continue
        target = urljoin(base_url, href)
        if target.rstrip("/") != base_url.rstrip("/"):
            return target
    return None


def _requirements(brand_id: str, description: str, text: str) -> str:
    keywords = KEYWORDS[brand_id]
    sentences = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    picked = [sentence for sentence in sentences if any(word in sentence.lower() for word in keywords)]
    parts: list[str] = []
    if description:
        parts.append(description)
    for sentence in picked:
        if sentence not in parts:
            parts.append(sentence)
        if len(parts) == 3:
            break
    summary = " ".join(parts).strip()
    if not summary:
        return "No specific operating requirement was visible on the public page."
    return summary[:420]


def _read_company(url: str) -> dict[str, str | None]:
    html = _fetch_html(url)
    title, description, text = _visible_text(html)
    email = _published_email(html)
    phone = _published_phone(html)
    if email is None or phone is None:
        contact_url = _contact_page(html, url)
        if contact_url:
            try:
                contact_html = _fetch_html(contact_url)
            except Exception:
                contact_html = ""
            if contact_html:
                email = email or _published_email(contact_html)
                phone = phone or _published_phone(contact_html)
                _, contact_description, contact_text = _visible_text(contact_html)
                description = description or contact_description
                text = f"{text} {contact_text}"[:5000]
    return {
        "title": title,
        "description": description,
        "text": text,
        "email": email,
        "phone": phone,
    }


def load_scraped_leads(brand_id: str | None = None) -> list[dict]:
    try:
        rows = json.loads(_LEADS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if brand_id:
        rows = [row for row in rows if row.get("brand_id") == brand_id]
    return sorted(rows, key=lambda row: (-int(row.get("fit_score") or 0), row.get("name") or ""))


def _save_scraped_leads(rows: list[dict]) -> None:
    _LEADS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _LEADS_PATH.write_text(json.dumps(rows), encoding="utf-8")


def _lead_id(brand_id: str, url: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"{brand_id}:{url}"))


def _upsert(connection, row: dict) -> None:
    updated = connection.execute(
        """
        update leads
        set name = %s, country = %s, fit_score = %s, why = %s,
            url = %s, email = %s, phone = %s, requirements = %s,
            source_url = %s, source_title = %s
        where brand_id = %s and url = %s
        """,
        (
            row["name"], row["country"], row["fit_score"], row["why"],
            row.get("url"), row.get("email"), row.get("phone"),
            row.get("requirements"), row.get("source_url"), row.get("source_title"),
            row["brand_id"], row["url"],
        ),
    )
    changed = getattr(updated, "rowcount", None)
    if changed is None:
        changed = getattr(getattr(updated, "cursor", None), "rowcount", 0)
    if changed:
        return
    connection.execute(
        """
        insert into leads (id, brand_id, name, url, country, fit_score, why,
                           email, phone, requirements, source_url, source_title)
        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            row["id"], row["brand_id"], row["name"], row["url"], row["country"],
            row["fit_score"], row["why"], row.get("email"), row.get("phone"),
            row.get("requirements"), row.get("source_url"), row.get("source_title"),
        ),
    )


def _store_database(rows: list[dict]) -> str | None:
    try:
        with get_connection() as connection:
            for row in rows:
                _upsert(connection, row)
    except Exception as exc:
        logger.info("Lead database update skipped (%s)", exc.__class__.__name__)
        return exc.__class__.__name__
    return None


def _qualify_candidate(candidate: dict) -> dict | None:
    source_url = str(candidate.get("url") or "")
    if not source_url:
        return None
    company_url = source_url
    if _needs_company_lookup(source_url, str(candidate.get("domain_type") or "web")):
        company_url = _company_site(
            _company_name(str(candidate.get("title") or ""), source_url),
            str(candidate.get("location") or "US"),
        ) or source_url
    if _needs_company_lookup(company_url, "web") and company_url == source_url:
        page = {
            "title": candidate.get("title") or "",
            "description": candidate.get("snippet") or "",
            "text": candidate.get("snippet") or "",
            "email": None,
            "phone": None,
            "company_url": source_url,
        }
    else:
        page = _read_company(company_url)
        page["company_url"] = company_url
    return build_lead(
        str(candidate["brand_id"]),
        source_url,
        str(candidate.get("title") or ""),
        str(candidate.get("snippet") or ""),
        page,
        str(candidate.get("location") or ""),
    )


def refresh_leads(*, claim: bool = True) -> dict:
    """Search the web and store each matching company as soon as its page is read."""
    global _RUNNING
    if claim:
        with _LOCK:
            if _RUNNING:
                return refresh_status()
            _RUNNING = True
    rows: list[dict] = []
    errors: list[str] = []

    def publish_state() -> None:
        _save_state(
            {
                "last_scraped_at": datetime.now(timezone.utc).isoformat(),
                "updated": len(rows),
                "last_error": "; ".join(errors[:5]) if errors else None,
            }
        )

    def on_error(message: str) -> None:
        if message not in errors:
            errors.append(message)
        publish_state()

    def on_candidate(candidate: dict) -> None:
        source_url = str(candidate.get("url") or "")
        try:
            lead = _qualify_candidate(candidate)
        except Exception as exc:
            errors.append(f"{source_url}: {exc.__class__.__name__}")
            logger.info("Skipped %s (%s)", source_url, exc.__class__.__name__)
            publish_state()
            return
        if lead is None or any(row["id"] == lead["id"] for row in rows):
            return
        rows.append(lead)
        _save_scraped_leads(rows)
        publish_state()
        time.sleep(0.4)

    try:
        if not key_configured():
            _save_state(
                {
                    "last_scraped_at": None,
                    "updated": 0,
                    "last_error": "TinyFish_API_KEY is not configured",
                }
            )
            _save_scraped_leads([])
            return refresh_status()
        previous = _load_state()
        _save_scraped_leads([])
        _save_state(
            {
                "last_scraped_at": previous.get("last_scraped_at"),
                "updated": 0,
                "last_error": None,
            }
        )
        discover_candidates(on_candidate=on_candidate, on_error=on_error)
        db_error = _store_database(rows)
        if db_error:
            errors.append(f"database: {db_error}")
        publish_state()
        logger.info("Lead discovery stored %s sites", len(rows))
        return refresh_status()
    finally:
        with _LOCK:
            _RUNNING = False


def _is_stale() -> bool:
    raw = _load_state().get("last_scraped_at")
    if not raw:
        return True
    try:
        last = datetime.fromisoformat(raw)
    except ValueError:
        return True
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - last > timedelta(hours=REFRESH_HOURS)


def run_daily_loop() -> None:
    """Check once an hour and refresh when the last read is older than a day."""
    while True:
        try:
            if _is_stale():
                refresh_leads()
        except Exception:
            logger.exception("Lead refresh failed")
        time.sleep(60 * 60)


def start_daily_refresh() -> None:
    if os.getenv("AURA_LEAD_REFRESH", "true").lower() in {"0", "false", "no"}:
        return
    if os.getenv("PYTEST_CURRENT_TEST"):
        return
    thread = threading.Thread(target=run_daily_loop, name="aura-lead-refresh", daemon=True)
    thread.start()


def start_refresh_in_background() -> dict:
    global _RUNNING
    with _LOCK:
        if _RUNNING:
            return refresh_status()
        _RUNNING = True
    thread = threading.Thread(
        target=lambda: refresh_leads(claim=False),
        name="aura-lead-refresh-once",
        daemon=True,
    )
    thread.start()
    return refresh_status()
