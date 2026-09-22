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
COOKIE_NOISE_PATTERN = re.compile(
    r"(?:"
    r"(?:we\s+use\s+cookies|this\s+(?:site|website)\s+uses\s+cookies)"
    r"(?:\s+to\s+(?:improve|enhance|personalize)\s+(?:your|the)\s+(?:experience|visit|browsing))?|"
    r"(?:accept|reject)(?:\s+(?:all|essential|non[- ]essential))?\s+cookies|"
    r"manage\s+(?:cookie|consent|privacy|preferences?)(?:\s+and)?|"
    r"cookie\s+(?:consent|preferences?|settings?|banner|notice)|"
    r"privacy\s+(?:preferences?|settings?|choices?)|"
    r"(?:non[- ]essential\s+cookies|privacy\s+preference\s+center|onetrust|cookiebot|trustarc|"
    r"quantcast|usercentrics|didomi|cookieyes|iubenda|gdpr\s+(?:consent|settings?)|ccpa\s+(?:consent|settings?))"
    r")",
    re.IGNORECASE,
)
SOURCE_RELIABILITY = {
    "website": 0.94,
    "changedetection": 0.90,
    "news": 0.84,
    "rss": 0.78,
    "rsshub": 0.76,
    "linkedin": 0.72,
    "youtube": 0.72,
}
CHANGE_EVIDENCE_PRIOR = {
    "price_change": 0.94,
    "new_product": 0.80,
    "partnership": 0.78,
    "new_market": 0.74,
    "article": 0.80,
    "social_post": 0.66,
    "positioning_change": 0.58,
}


def normalize_content(content: str) -> str:
    lines = []
    for raw_line in content.splitlines():
        line = " ".join(raw_line.split())
        if not line:
            continue
        if COOKIE_NOISE_PATTERN.search(line):
            substantive = COOKIE_NOISE_PATTERN.sub(" ", line)
            substantive = " ".join(substantive.split()).strip(" .,:;|·-[]()")
            # If consent text shares a line with actual page copy, retain the
            # copy and remove only the matched consent segment. Protect price
            # lines if a malformed/no-punctuation banner match is too broad.
            line = substantive or (line if price_values(line) else "")
        if line:
            lines.append(line)
    return "\n".join(lines)


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


def confidence_for_change(previous: str, current: str, source: str, change_type: str) -> float:
    """Return an explainable evidence score for a detected change.

    This is intentionally deterministic rather than pretending to be a
    calibrated probability. It combines the type of evidence, how much the
    normalized content changed, and the reliability of the collector.
    """
    old = normalize_content(previous)
    new = normalize_content(current)
    old_tokens = set(old.lower().split())
    new_tokens = set(new.lower().split())
    token_delta = len(old_tokens ^ new_tokens)
    length_delta = abs(len(new) - len(old))
    similarity = SequenceMatcher(None, old, new).ratio() if old or new else 1.0
    similarity_signal = min(1.0, max(0.0, (1.0 - similarity) / 0.35))
    token_signal = min(1.0, token_delta / 12.0)
    length_signal = min(1.0, length_delta / 160.0)
    change_strength = (
        0.45 * similarity_signal
        + 0.35 * token_signal
        + 0.20 * length_signal
    )

    old_prices = price_values(old)
    new_prices = price_values(new)
    if change_type == "price_change" and old_prices != new_prices:
        # Structured price extraction is stronger evidence than a generic
        # text delta, even when only one numeric token changed.
        changed_price_count = len(set(old_prices) ^ set(new_prices))
        change_strength = max(change_strength, min(1.0, 0.72 + changed_price_count * 0.07))

    evidence_prior = CHANGE_EVIDENCE_PRIOR.get(change_type, 0.58)
    source_reliability = SOURCE_RELIABILITY.get(source, 0.68)
    score = (
        0.45 * evidence_prior
        + 0.35 * change_strength
        + 0.20 * source_reliability
    )
    return round(min(0.98, max(0.50, score)), 2)


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
        "confidence": confidence_for_change(previous, current, source, change_type),
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
