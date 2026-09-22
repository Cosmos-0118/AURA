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
COOKIE_BANNER_LINE_PATTERN = re.compile(
    r"(?:\b(?:we|this\s+(?:site|website))\s+use(?:s)?\b[^\n]*\bcookies?\b|"
    r"\buses\s+cookies?\b|\b(?:cookie|consent|privacy)\s+(?:banner|notice|preferences?|settings?)\b|"
    r"\b(?:necessary|optional|analytics|non[- ]essential)\s+cookies?\b|"
    r"\b(?:accept|reject|manage)\b[^\n]*\b(?:cookies?|consent|preferences?|privacy)\b)",
    re.IGNORECASE,
)
COOKIE_COPY_SUFFIX_PATTERN = re.compile(
    r"(?:^|\s+)\b(?:we|this\s+(?:site|website))\s+use(?:s)?\b"
    r"(?=[^\n]*\bcookies?\b)[^\n]*$",
    re.IGNORECASE,
)
LOCATION_PROMPT_PATTERN = re.compile(
    r"(?:^hello,?\s+we\s+have\s+detected\s+you\s+are\s+visiting\s+from\b|"
    r"^would\s+you\s+like\s+to\s+go\s+to\s+the\s+.+?\s+website\??"
    r"(?:\s+(?:yes|no|yes\s+no|no\s+yes))?$)",
    re.IGNORECASE,
)
TRANSIENT_CONTROL_PATTERN = re.compile(
    r"^(?:×|x|yes|no|yes\s+no|no\s+yes|accept\s+all|preferences)$", re.IGNORECASE
)
CONSENT_CONTROL_PATTERN = re.compile(r"^(?:×|x|accept\s+all|preferences)$", re.IGNORECASE)
INTERSTITIAL_PATTERN = re.compile(
    r"^(?:please\s+enable\s+javascript|javascript\s+is\s+required|"
    r"checking\s+your\s+browser|just\s+a\s+moment|access\s+denied|"
    r"verify\s+(?:you\s+are\s+)?human|security\s+check)\b.*$",
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


def _normalized_lines(content: str) -> tuple[list[str], int]:
    lines: list[str] = []
    removed_transient_chars = 0
    raw_lines = [" ".join(raw_line.split()) for raw_line in content.splitlines()]
    raw_lines = [line for line in raw_lines if line]
    has_cookie_signal = any(COOKIE_BANNER_LINE_PATTERN.search(line) for line in raw_lines)
    location_prompt_active = False

    for index, line in enumerate(raw_lines):
        original_line = line
        if LOCATION_PROMPT_PATTERN.search(line):
            removed_transient_chars += len(line)
            location_prompt_active = True
            continue
        if location_prompt_active and TRANSIENT_CONTROL_PATTERN.fullmatch(line):
            removed_transient_chars += len(line)
            continue
        location_prompt_active = False

        if has_cookie_signal and CONSENT_CONTROL_PATTERN.fullmatch(line):
            removed_transient_chars += len(line)
            continue
        # Consent providers often append a variable-length paragraph to real
        # copy or a price row. Keep the preceding evidence and discard that
        # suffix so wording changes cannot create an event.
        line_before_cookie_suffix = line
        line = COOKIE_COPY_SUFFIX_PATTERN.sub("", line).strip()
        removed_transient_chars += max(0, len(line_before_cookie_suffix) - len(line))
        if COOKIE_NOISE_PATTERN.search(line):
            substantive = COOKIE_NOISE_PATTERN.sub(" ", line)
            substantive = " ".join(substantive.split()).strip(" .,:;|·-[]()")
            # If consent text shares a line with actual page copy, retain the
            # copy and remove only the matched consent segment. Protect price
            # lines if a malformed/no-punctuation banner match is too broad.
            line = substantive or (line if price_values(line) else "")
        if CONSENT_CONTROL_PATTERN.fullmatch(line) and (
            has_cookie_signal or (line.casefold() == "preferences" and index == len(raw_lines) - 1)
        ):
            removed_transient_chars += len(line)
            continue
        if COOKIE_BANNER_LINE_PATTERN.search(line):
            # A changedetection text snapshot can put a consent block and real
            # copy on one line. Keep the real copy only when the remaining
            # text no longer looks like consent UI.
            if price_values(line) or (
                line != original_line
                and not re.search(r"\b(?:cookie|consent|privacy)\b", line, re.IGNORECASE)
            ):
                pass
            else:
                removed_transient_chars += len(original_line)
                continue
        if line:
            lines.append(line)
    return lines, removed_transient_chars


def normalize_content(content: str) -> str:
    lines, _ = _normalized_lines(content)
    return "\n".join(lines)


MARKET_TERMS = {
    "sg": ("howden india", "india site", "india website", "indonesia site", "malaysia site", "thailand site", "hong kong site"),
    "hk": ("howden india", "india site", "indonesia site", "malaysia site", "singapore site", "thailand site"),
    "my": ("howden india", "india site", "indonesia site", "singapore site", "thailand site", "hong kong site"),
    "th": ("howden india", "india site", "indonesia site", "singapore site", "malaysia site", "hong kong site"),
}


def capture_quality_error(
    content: str,
    *,
    baseline: str | None = None,
    expected_url: str | None = None,
) -> str | None:
    """Reject captures that contain only, or are dominated by, transient UI."""
    lines, removed_transient_chars = _normalized_lines(content)
    normalized_length = sum(len(line) for line in lines)
    if not lines:
        return "capture contains no substantive page content after transient UI filtering"
    if (
        removed_transient_chars >= 80
        and removed_transient_chars > normalized_length * 2
        and normalized_length < 32
    ):
        return "capture is dominated by transient consent or location UI"
    if baseline and removed_transient_chars >= 80:
        baseline_length = len(normalize_content(baseline))
        if baseline_length >= 128 and normalized_length < baseline_length * 0.25:
            return "capture is much shorter than the valid baseline after transient UI filtering"
    if normalized_length < 320 and any(INTERSTITIAL_PATTERN.search(line) for line in lines):
        return "capture looks like an access or JavaScript interstitial; retaining baseline"
    if expected_url and baseline:
        locale_match = re.search(r"/([a-z]{2})(?:-[a-z]{2})?/", expected_url, re.IGNORECASE)
        locale = locale_match.group(1).casefold() if locale_match else ""
        recent_lines = [line.casefold().strip(" .:|-") for line in lines[:12]]
        baseline_text = normalize_content(baseline)
        similarity = SequenceMatcher(None, baseline_text, "\n".join(lines)).ratio()
        if (
            locale in MARKET_TERMS
            and similarity < 0.55
            and any(term in recent_lines for term in MARKET_TERMS[locale])
        ):
            return "capture appears to be from a different market; retaining baseline"
    return None


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
