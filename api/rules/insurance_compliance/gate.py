"""Pure compliance agent that evaluates copy before review queue admission."""

import re

try:
    from ...schemas import ComplianceIssue, ComplianceResult
except ImportError:  # Supports running from the api directory.
    from schemas import ComplianceIssue, ComplianceResult

from .rubric import RULES, Rule


class InsuranceComplianceGate:
    """Return a structured verdict without external calls or side effects."""

    def check(self, text: str) -> ComplianceResult:
        if not text or not text.strip():
            return ComplianceResult(
                result="REVIEW",
                risk="MEDIUM",
                rules=["REVIEW_000"],
                issues=[ComplianceIssue(
                    text="",
                    reason="Empty marketing copy needs human review.",
                    rule_id="REVIEW_000",
                )],
                suggested_revision="Add product-specific copy supported by the policy.",
            )

        matches: list[tuple[int, int, Rule, str]] = []
        occupied: list[tuple[int, int]] = []
        for rule in RULES:
            for match in re.finditer(rule.pattern, text, re.IGNORECASE):
                span = match.span()
                if rule.rule_id == "CLAIM_001" and re.search(
                    r"\b(?:not\s+(?:offer\s+)?|never\s+|no\s+)$",
                    text[max(0, span[0] - 24):span[0]],
                    re.IGNORECASE,
                ):
                    continue
                if any(span[0] < end and start < span[1] for start, end in occupied):
                    continue
                occupied.append(span)
                matches.append((span[0], span[1], rule, match.group()))

        matches.sort(key=lambda item: item[0])
        seen: set[str] = set()
        issues: list[ComplianceIssue] = []
        verdict = "PASS"
        for _, _, rule, matched_text in matches:
            if rule.rule_id in seen:
                continue
            seen.add(rule.rule_id)
            issues.append(ComplianceIssue(
                text=matched_text,
                reason=rule.reason,
                rule_id=rule.rule_id,
            ))
            if rule.verdict == "FAIL":
                verdict = "FAIL"
            elif verdict == "PASS":
                verdict = "REVIEW"

        return ComplianceResult(
            result=verdict,
            risk={"PASS": "LOW", "REVIEW": "MEDIUM", "FAIL": "HIGH"}[verdict],
            rules=[issue.rule_id for issue in issues],
            issues=issues,
            suggested_revision=(
                "Explore coverage options. Benefits and claim decisions depend on "
                "the policy terms, conditions, exclusions, and eligibility."
                if issues else None
            ),
        )


def check_compliance(text: str, brand_id: str, platform: str) -> ComplianceResult:
    """Contract-compatible entry point for the campaign pipeline.

    Brand and platform are retained for the frozen interface; the current
    conservative rubric applies equally to all marketing copy.
    """

    return InsuranceComplianceGate().check(text)
