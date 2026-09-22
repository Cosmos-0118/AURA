from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit

from .config import REQUEST_TIMEOUT, SEARXNG_URL


USER_AGENT = "JA-Assure-Competitor-Intelligence/0.1 (+deterministic-monitor)"
RETRYABLE_HTTP_STATUS_CODES = frozenset({408, 425, 429, 500, 502, 503, 504})
MAX_REQUEST_ATTEMPTS = 3
COOKIE_CONTAINER_PATTERN = re.compile(
    r"(?:cookie|consent|onetrust|cookiebot|trustarc|quantcast|usercentrics|"
    r"didomi|gdpr|ccpa|cookieyes|iubenda|osano)",
    re.IGNORECASE,
)
COOKIE_CONTAINER_ATTRIBUTES = frozenset({"id", "class", "role", "aria-label", "aria-labelledby"})
HTML_VOID_ELEMENTS = frozenset({
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
})


class BotProtectionChallenge(ValueError):
    """The origin returned an anti-bot challenge instead of page content."""


@dataclass(slots=True)
class CollectedContent:
    content: str
    source: str
    title: str | None = None
    url: str | None = None
    source_key: str | None = None
    market: str | None = None
    observed_at: str | None = None


@dataclass(slots=True)
class FeedItem:
    title: str
    content: str
    url: str
    published_at: str | None = None


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._tag_stack: list[tuple[str, bool]] = []
        self.title: str | None = None
        self._in_title = False

    @staticmethod
    def _is_cookie_container(attrs: list[tuple[str, str | None]]) -> bool:
        values = [
            value
            for key, value in attrs
            if value and (key in COOKIE_CONTAINER_ATTRIBUTES or key.startswith("data-"))
        ]
        return bool(values and COOKIE_CONTAINER_PATTERN.search(" ".join(values)))

    def _visible_context(self) -> bool:
        return not any(excluded for _, excluded in self._tag_stack)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        excluded = (
            tag in {"script", "style", "noscript", "svg", "template"}
            or self._is_cookie_container(attrs)
            or not self._visible_context()
        )
        if tag not in HTML_VOID_ELEMENTS:
            self._tag_stack.append((tag, excluded))
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._in_title = False
        for index in range(len(self._tag_stack) - 1, -1, -1):
            if self._tag_stack[index][0] == tag:
                del self._tag_stack[index:]
                break

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        if self._in_title and self.title is None:
            self.title = text
        if self._visible_context():
            self._parts.append(text)

    @property
    def text(self) -> str:
        return "\n".join(self._parts)


class StructuredPageParser(VisibleTextParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self.links: list[tuple[str, str]] = []
        self._row: list[str] | None = None
        self._cell: list[str] | None = None
        self._link: list[str] | None = None
        self._href: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        super().handle_starttag(tag, attrs)
        if tag == "tr":
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell = []
        elif tag == "a":
            self._href = dict(attrs).get("href")
            self._link = []

    def handle_data(self, data: str) -> None:
        visible = self._visible_context()
        super().handle_data(data)
        if not visible:
            return
        if self._cell is not None:
            self._cell.append(data)
        if self._link is not None:
            self._link.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(" ".join(" ".join(self._cell).split()))
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self._row:
                self.rows.append(self._row)
            self._row = None
        elif tag == "a" and self._link is not None:
            title = " ".join(" ".join(self._link).split())
            if self._href and title:
                self.links.append((self._href, title))
            self._link = None
            self._href = None
        super().handle_endtag(tag)


INCOME_RISK_CATEGORIES = (
    "Obstetric Risk", "Gynaecology", "Office Gynaecology", "High Risk",
    "Medium Risk", "Low Risk", "Family Medicine - Procedural",
    "Family Medicine - Non-Procedural",
)


def extract_income_pricing_text(text: str) -> str:
    prices: dict[str, str] = {}
    for category in INCOME_RISK_CATEGORIES:
        match = re.search(rf"(?im)^\s*{re.escape(category)}(?!\w)[^\n]*", text)
        if match is None:
            continue
        price = re.search(r"(?:S\$|\$|SGD)\s*([\d,]+(?:\.\d{2})?)", text[match.start():match.start() + 140], re.I)
        if price:
            prices[category] = f"S${price.group(1)}"
    if len(prices) < 6:
        raise ValueError("Too few Income premium rows in changedetection snapshot; retaining baseline")
    discount = re.search(r"\d+% discount[^.]*", text, re.I)
    date = re.search(r"from \d{1,2} [A-Za-z]+ \d{4} to \d{1,2} [A-Za-z]+ \d{4}", text, re.I)
    return json.dumps({"premiums": prices, "discount": discount.group(0) if discount else None,
                       "effective_date": date.group(0) if date else None}, sort_keys=True)


def request_bytes(
    url: str,
    *,
    accept: str = "*/*",
    extra_headers: dict[str, str] | None = None,
    timeout: int | None = None,
) -> tuple[bytes, str]:
    headers = {
        "Accept": accept,
        "User-Agent": USER_AGENT,
    }
    headers.update(extra_headers or {})
    request = urllib.request.Request(
        url,
        headers=headers,
    )
    request_timeout = REQUEST_TIMEOUT if timeout is None else timeout
    for attempt in range(MAX_REQUEST_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=request_timeout) as response:
                body = response.read()
                status = getattr(response, "status", None) or response.getcode()
                if status == 247 or b"kramericaindustries.ac_v2.lib.js" in body[:4096]:
                    raise BotProtectionChallenge(
                        f"Origin returned HTTP 247 bot-protection challenge at {url}"
                    )
                # RSSHub sometimes answers 200 with its landing page when Chromium is busy.
                if b"<title>Welcome to RSSHub!</title>" in body[:4096] and attempt < MAX_REQUEST_ATTEMPTS - 1:
                    time.sleep(2 ** (attempt + 2))
                    continue
                content_type = response.headers.get("Content-Type", "")
                return body, content_type
        except urllib.error.HTTPError as exc:
            if exc.code not in RETRYABLE_HTTP_STATUS_CODES or attempt == MAX_REQUEST_ATTEMPTS - 1:
                raise
        except urllib.error.URLError:
            if attempt == MAX_REQUEST_ATTEMPTS - 1:
                raise
        time.sleep(2**attempt)
    raise RuntimeError(f"Could not fetch {url}")


def collect_website(url: str) -> CollectedContent:
    body, content_type = request_bytes(url, accept="text/html,application/xhtml+xml")
    charset = "utf-8"
    match = re.search(r"charset=([\w-]+)", content_type, re.IGNORECASE)
    if match:
        charset = match.group(1)
    html = body.decode(charset, errors="replace")
    parser = VisibleTextParser()
    parser.feed(html)
    text = parser.text.strip()
    if not text:
        raise ValueError(f"No visible text found at {url}")
    return CollectedContent(content=text, source="website", title=parser.title, url=url)


def _next_data_article_links(html: str, base_url: str) -> list[tuple[str, str]]:
    match = re.search(
        r'<script[^>]+id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>',
        html,
        re.DOTALL | re.IGNORECASE,
    )
    if match is None:
        return []
    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError:
        return []

    links: list[tuple[str, str]] = []

    def visit(value: object) -> None:
        if isinstance(value, dict):
            articles = value.get("articles")
            if isinstance(articles, list):
                for article in articles:
                    if not isinstance(article, dict):
                        continue
                    title = str(article.get("title") or "").strip()
                    buttons = article.get("buttons")
                    if not title or not isinstance(buttons, list):
                        continue
                    for button in buttons:
                        if isinstance(button, dict) and button.get("link"):
                            links.append((str(button["link"]), title))
                            break
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    visit(payload)
    return [(urljoin(base_url, href), title) for href, title in links]


def collect_watch(url: str, kind: str) -> CollectedContent:
    if kind not in {"pricing", "news", "insights"}:
        return collect_website(url)
    body, content_type = request_bytes(url, accept="text/html,application/xhtml+xml")
    match = re.search(r"charset=([\w-]+)", content_type, re.IGNORECASE)
    html = body.decode(match.group(1) if match else "utf-8", errors="replace")
    parser = StructuredPageParser()
    parser.feed(html)
    if kind == "pricing":
        prices: dict[str, str] = {}
        for row in parser.rows:
            if len(row) < 2:
                continue
            price = re.search(r"(?:S\$|\$|SGD)\s*([\d,]+(?:\.\d{2})?)", row[1], re.I)
            if price and row[0].strip().lower() not in {"risk category", "annual premium (s$)"}:
                prices[row[0]] = f"S${price.group(1)}"
        if not prices:
            raise ValueError(f"No premium rows found at {url}; retaining the previous baseline")
        text = parser.text
        discount = re.search(r"\d+% discount[^.]*", text, re.I)
        date = re.search(r"from \d{1,2} [A-Za-z]+ \d{4} to \d{1,2} [A-Za-z]+ \d{4}", text, re.I)
        content = json.dumps({"premiums": prices, "discount": discount.group(0) if discount else None,
                              "effective_date": date.group(0) if date else None}, sort_keys=True)
    else:
        base = urlsplit(url)
        links: dict[str, str] = {}
        page_links = parser.links + _next_data_article_links(html, url)
        for href, title in page_links:
            absolute = urljoin(url, href).split("#", 1)[0]
            parsed = urlsplit(absolute)
            same_publisher = parsed.netloc == base.netloc or (
                base.netloc.endswith("chubb.com") and parsed.netloc == "chubb.mediaroom.com"
            )
            if not same_publisher or parsed.path.rstrip("/") == base.path.rstrip("/"):
                continue
            if len(title) < 12 or not any(part in parsed.path.lower() for part in
                                           ("news", "insight", "press", "article", "casebook", "resource")):
                continue
            links[absolute] = title
        if not links:
            raise ValueError(f"No article links found at {url}; retaining the previous baseline")
        content = "\n".join(f"{link}\t{title}" for link, title in sorted(links.items()))
    return CollectedContent(content=content, source="website", title=parser.title, url=url)


def collect_rss(url: str, source: str = "rss") -> list[FeedItem]:
    # LinkedIn/YouTube via RSSHub need headroom for Chromium; native podcast RSS is fast.
    timeout = 90 if "127.0.0.1:1200" in url or "rsshub:" in url else REQUEST_TIMEOUT
    body, _ = request_bytes(
        url,
        accept="application/rss+xml, application/atom+xml, application/xml",
        timeout=timeout,
    )
    if b"<title>Welcome to RSSHub!</title>" in body[:4096]:
        raise RuntimeError(f"RSSHub route temporarily unavailable at {url}")
    root = ET.fromstring(body)
    items: list[FeedItem] = []
    for item in root.findall(".//item"):
        items.append(
            FeedItem(
                title=_xml_text(item, "title") or "Untitled feed item",
                content=_xml_text(item, "description") or _xml_text(item, "content") or "",
                url=_xml_text(item, "link") or url,
                published_at=_xml_text(item, "pubDate"),
            )
        )
    for entry in root.findall(".//{*}entry"):
        link = next(
            (
                element.attrib.get("href")
                for element in entry.findall("{*}link")
                if element.attrib.get("href")
            ),
            url,
        )
        items.append(
            FeedItem(
                title=_xml_text(entry, "{*}title") or "Untitled feed item",
                content=_xml_text(entry, "{*}summary") or _xml_text(entry, "{*}content") or "",
                url=link,
                published_at=_xml_text(entry, "{*}published") or _xml_text(entry, "{*}updated"),
            )
        )
    return items


def search_searxng(query: str, base_url: str = SEARXNG_URL) -> list[FeedItem]:
    if not base_url:
        raise ValueError("SEARXNG_URL is not configured")
    params = urllib.parse.urlencode({"q": query, "format": "json", "language": "en"})
    body, _ = request_bytes(
        f"{base_url}/search?{params}",
        accept="application/json",
        extra_headers={
            "X-Real-IP": "127.0.0.1",
            "X-Forwarded-For": "127.0.0.1",
        },
    )
    payload = json.loads(body.decode("utf-8"))
    return [
        FeedItem(
            title=str(result.get("title", "Untitled result")),
            content=str(result.get("content", "")),
            url=str(result.get("url", "")),
        )
        for result in payload.get("results", [])
        if result.get("url")
    ]


def _xml_text(parent: ET.Element, path: str) -> str | None:
    element = parent.find(path)
    if element is None or element.text is None:
        return None
    return " ".join(element.text.split())
