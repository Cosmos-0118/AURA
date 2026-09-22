"""Auditable rules for insurance marketing copy.

These rules catch claims that require a human to verify the actual policy.
They are not a substitute for a jurisdiction- and product-specific review.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class Rule:
    rule_id: str
    pattern: str
    reason: str
    verdict: Literal["FAIL", "REVIEW"]


RULES = (
    Rule(
        "CLAIM_005",
        r"\bclaim\s+guaranteed\b",
        "A claim decision depends on the applicable policy terms and evidence.",
        "FAIL",
    ),
    Rule(
        "CLAIM_001",
        r"\bguaranteed\b",
        "An unqualified guarantee of protection or outcome is unsafe.",
        "FAIL",
    ),
    Rule(
        "CLAIM_002",
        r"\b100\s*%\s*(?:covered|coverage)\b",
        "Coverage cannot be presented as absolute without verified policy terms.",
        "FAIL",
    ),
    Rule(
        "CLAIM_003",
        r"\b(?:zero\s+risk|risk[-\s]?free)\b",
        "Insurance cannot eliminate every risk.",
        "FAIL",
    ),
    Rule(
        "CLAIM_004",
        r"\b(?:always|fully)\s+covered\b",
        "Coverage depends on policy terms, conditions, and exclusions.",
        "FAIL",
    ),
    Rule(
        "CLAIM_006",
        r"\b(?:all|every)\s+(?:conditions?|illnesses?|losses?)\s+(?:are\s+)?covered\b",
        "The scope of covered events must be checked against the policy.",
        "FAIL",
    ),
    Rule(
        "CLAIM_007",
        r"\bno\s+exclusions\b",
        "An absence of exclusions must be verified in the policy.",
        "FAIL",
    ),
    Rule(
        "CLAIM_008",
        r"\ball\s+claims\s+(?:are\s+)?approved\b",
        "Claim approval depends on the applicable policy and claim evidence.",
        "FAIL",
    ),
    Rule(
        "REVIEW_001",
        r"\b(?:full|complete|comprehensive|unlimited)\s+coverage\b",
        "The breadth of coverage needs policy evidence and clear limits.",
        "REVIEW",
    ),
    Rule(
        "REVIEW_002",
        r"\b(?:instant|immediate)\s+(?:coverage|approval)\b",
        "The effective date or approval process needs product verification.",
        "REVIEW",
    ),
    Rule(
        "REVIEW_003",
        r"\b(?:lowest|cheapest)\s+premiums?\b",
        "Comparative premium claims need current, comparable evidence.",
        "REVIEW",
    ),
)
