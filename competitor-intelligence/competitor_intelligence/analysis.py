from __future__ import annotations

import hashlib
import re
from difflib import SequenceMatcher

from .models import Competitor, Snapshot
from .store import new_id


PRICE_PATTERN = re.compile(
    r"(?:(?:SGD|MYR|HKD|IDR|THB|USD|S\$|RM|HK\$|฿)\s*[\d,]+(?:\.\d{1,2})?|[\d,]+(?:\.\d{1,2})?\s*(?:SGD|MYR|HKD|IDR|THB|USD))",
    re.IGNORECASE,
)


def normalize_content(content: str) -> str:
    lines = [" ".join(line.split()) for line in content.splitlines()]
    return "\n".join(line for line in lines if line)


def content_hash(content: str) -> str:
    stable_text = " ".join(normalize_content(content).split())
    return hashlib.sha256(stable_text.encode("utf-8")).hexdigest()


def meaningful_change(previous: str, current: str) -> bool:
    old = normalize_content(previous)
    new = normalize_content(current)
    if old == new:
        return False
    if price_values(old) != price_values(new) and (price_values(old) or price_values(new)):
        return True
    ratio = SequenceMatcher(None, old, new).ratio()
    changed_tokens = set(new.lower().split()) ^ set(old.lower().split())
    return ratio < 0.995 and (len(changed_tokens) >= 3 or abs(len(new) - len(old)) > 40)


def price_values(text: str) -> list[str]:
    return [match.group(0).strip() for match in PRICE_PATTERN.finditer(text)]


def build_change_summary(previous: str, current: str) -> str:
    old_prices = price_values(previous)
    new_prices = price_values(current)
    if old_prices != new_prices and (old_prices or new_prices):
        return f"Price signals changed from {', '.join(old_prices) or 'none'} to {', '.join(new_prices) or 'none'}."
    old_words = set(previous.lower().split())
    new_words = [word for word in current.split() if word.lower() not in old_words]
    excerpt = " ".join(new_words[:18])
    return f"Page content changed. New text includes: {excerpt or 'updated copy'}."


def evidence_excerpt(current: str, max_length: int = 320) -> str:
    text = " ".join(current.split())
    return text[:max_length] + ("…" if len(text) > max_length else "")


def classify_change(competitor: Competitor, previous: str, current: str, source: str) -> dict[str, object]:
    old_lower = previous.lower()
    new_lower = current.lower()
    old_prices = price_values(previous)
    new_prices = price_values(current)
    if old_prices != new_prices and (old_prices or new_prices):
        change_type = "price_change"
        impact = "high"
        summary = f"Pricing signals changed for {competitor.name}."
        previous_value = ", ".join(old_prices) or None
        current_value = ", ".join(new_prices) or None
    elif any(term in new_lower and term not in old_lower for term in ("new plan", "launch", "introduced", "new product")):
        change_type = "new_product"
        impact = "high"
        summary = f"A possible new product or plan appeared for {competitor.name}."
        previous_value = current_value = None
    elif any(term in new_lower and term not in old_lower for term in ("partnership", "partnered", "association")):
        change_type = "partnership"
        impact = "high"
        summary = f"A partnership signal appeared for {competitor.name}."
        previous_value = current_value = None
    elif any(term in new_lower and term not in old_lower for term in ("malaysia", "singapore", "hong kong", "indonesia", "thailand")):
        change_type = "new_market"
        impact = "medium"
        summary = f"Market coverage language changed for {competitor.name}."
        previous_value = current_value = None
    elif source in {"linkedin", "youtube", "rss", "rsshub", "news"}:
        change_type = "social_post"
        impact = "low"
        summary = f"A new public content signal appeared for {competitor.name}."
        previous_value = current_value = None
    else:
        change_type = "positioning_change"
        impact = "medium"
        summary = f"Positioning or coverage copy changed for {competitor.name}."
        previous_value = current_value = None
    return {
        "change_type": change_type,
        "impact": impact,
        "summary": summary,
        "previous_value": previous_value,
        "current_value": current_value,
        "why_it_matters": f"The change may affect {competitor.niche} positioning in {', '.join(competitor.countries)}.",
        "recommended_action": "Review the evidence with the brand owner and decide whether a measured content or product response is warranted.",
        "evidence": evidence_excerpt(current),
        "confidence": 0.82,
    }


def new_snapshot(
    competitor_id: str,
    content: str,
    source: str,
    source_key: str,
    source_url: str | None,
    market: str | None,
    scraped_at: str,
    summary: str | None,
) -> Snapshot:
    return Snapshot(
        id=new_id("snapshot"),
        competitor_id=competitor_id,
        content_hash=content_hash(content),
        content=normalize_content(content),
        source=source,
        source_key=source_key,
        source_url=source_url,
        market=market,
        scraped_at=scraped_at,
        change_summary=summary,
    )
