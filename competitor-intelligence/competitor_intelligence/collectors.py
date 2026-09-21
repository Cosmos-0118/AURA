from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from html.parser import HTMLParser

from .config import REQUEST_TIMEOUT, SEARXNG_URL


USER_AGENT = "JA-Assure-Competitor-Intelligence/0.1 (+deterministic-monitor)"


@dataclass(slots=True)
class CollectedContent:
    content: str
    source: str
    title: str | None = None
    url: str | None = None


@dataclass(slots=True)
class FeedItem:
    title: str
    content: str
    url: str
    published_at: str | None = None


class VisibleTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._hidden = 0
        self._parts: list[str] = []
        self.title: str | None = None
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg", "template"}:
            self._hidden += 1
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        if tag in {"script", "style", "noscript", "svg", "template"}:
            self._hidden = max(0, self._hidden - 1)

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        if self._in_title and self.title is None:
            self.title = text
        if self._hidden == 0:
            self._parts.append(text)

    @property
    def text(self) -> str:
        return "\n".join(self._parts)


def request_bytes(url: str, *, accept: str = "*/*") -> tuple[bytes, str]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": USER_AGENT,
        },
    )
    with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        content_type = response.headers.get("Content-Type", "")
        return response.read(), content_type


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


def collect_rss(url: str, source: str = "rss") -> list[FeedItem]:
    body, _ = request_bytes(url, accept="application/rss+xml, application/atom+xml, application/xml")
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
    body, _ = request_bytes(f"{base_url}/search?{params}", accept="application/json")
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
