"""Deterministic compliance checks for generated marketing copy."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

try:
    from ..schemas import ComplianceIssue, ComplianceResult
except ImportError:  # Supports `cd api && uv run ...`.
    from schemas import ComplianceIssue, ComplianceResult


_RULES_PATH = Path(__file__).resolve().parent.parent / "rules" / "banned_terms.json"


@dataclass(frozen=True)
class _Rule:
    rule_id: str
    terms: tuple[str, ...]
    reason: str


def _load_rules() -> tuple[_Rule, ...]:
    """Load the small standard-library rule set from a path next to this module."""

    with _RULES_PATH.open(encoding="utf-8") as rules_file:
        raw_rules: list[dict[str, Any]] = json.load(rules_file)
    return tuple(
        _Rule(
            rule_id=str(raw_rule["rule_id"]),
            terms=tuple(str(term) for term in raw_rule["terms"]),
            reason=str(raw_rule["reason"]),
        )
        for raw_rule in raw_rules
    )


_RULES = _load_rules()
_RULE_ORDER = {rule.rule_id: index for index, rule in enumerate(_RULES)}


def _pattern(term: str) -> re.Pattern[str]:
    """Match a literal term without matching inside a larger word."""

    return re.compile(r"(?<!\w)" + re.escape(term) + r"(?!\w)", re.IGNORECASE)


_TERM_PATTERNS = {
    (rule.rule_id, term): _pattern(term)
    for rule in _RULES
    for term in rule.terms
}


@dataclass(frozen=True)
class _Match:
    rule: _Rule
    term: str
    start: int
    end: int
    text: str


def _find_matches(text: str) -> list[_Match]:
    candidates: list[_Match] = []
    for rule in _RULES:
        for term in rule.terms:
            for match in _TERM_PATTERNS[(rule.rule_id, term)].finditer(text):
                candidates.append(
                    _Match(
                        rule=rule,
                        term=term,
                        start=match.start(),
                        end=match.end(),
                        text=match.group(0),
                    )
                )

    # Prefer specific/longer phrases first, then retain only non-overlapping
    # matches. This prevents "claim guaranteed" from also emitting the
    # generic "guaranteed" rule for the same span.
    candidates.sort(key=lambda item: (-(item.end - item.start), item.start, _RULE_ORDER[item.rule.rule_id]))
    selected: list[_Match] = []
    selected_rule_ids: set[str] = set()
    for candidate in candidates:
        if candidate.rule.rule_id in selected_rule_ids:
            continue
        if any(candidate.start < item.end and item.start < candidate.end for item in selected):
            continue
        selected.append(candidate)
        selected_rule_ids.add(candidate.rule.rule_id)

    return sorted(selected, key=lambda item: (_RULE_ORDER[item.rule.rule_id], item.start))


def _suggested_revision(text: str) -> str:
    """Replace absolute wording with deterministic qualified alternatives."""

    revision = text
    replacements = (
        (r"\bclaim guaranteed\b", "claim assessed subject to policy terms"),
        (r"\balways covered\b", "coverage may apply subject to policy terms"),
        (r"\b100% covered\b", "coverage subject to policy terms"),
        (r"\bzero risk\b", "reduced risk"),
        # Keep a noun after common constructions, e.g. "guaranteed protection"
        # becomes "protection subject to policy terms".
        (r"\bguaranteed\s+([A-Za-z][\w-]*)", r"\1 subject to policy terms"),
        (r"\bguaranteed\b", "subject to policy terms"),
    )
    for pattern, replacement in replacements:
        revision = re.sub(pattern, replacement, revision, flags=re.IGNORECASE)
    return revision


def check_compliance(text: str, brand_id: str, platform: str) -> ComplianceResult:
    """Return a deterministic verdict for hard absolute-claim rules.

    ``brand_id`` and ``platform`` remain part of the frozen interface. The
    hard-rule pass is deliberately brand/platform independent so the same
    safety guarantee applies to every generated asset.
    """

    del brand_id, platform
    matches = _find_matches(text)
    if not matches:
        return ComplianceResult(result="PASS", risk="LOW")

    issues = [
        ComplianceIssue(text=match.text, reason=match.rule.reason, rule_id=match.rule.rule_id)
        for match in matches
    ]
    return ComplianceResult(
        result="FAIL",
        risk="HIGH",
        rules=[match.rule.rule_id for match in matches],
        issues=issues,
        suggested_revision=_suggested_revision(text),
    )
