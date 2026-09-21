"""Mock agent functions used until the real M4/M5 implementations land."""

from datetime import datetime, timezone
import hashlib

try:
    from ..db import get_connection
    from ..schemas import (
        ComplianceIssue,
        ComplianceResult,
        ContentRequest,
        GeneratedAsset,
    )
except ImportError:  # Supports `cd api && uv run uvicorn main:app`.
    from db import get_connection
    from schemas import ComplianceIssue, ComplianceResult, ContentRequest, GeneratedAsset


def generate_content(req: ContentRequest) -> list[GeneratedAsset]:
    """Return one deterministic draft per requested platform."""

    return [
        GeneratedAsset(
            platform=platform,
            content_type="post" if platform == "linkedin" else "caption",
            title=f"{req.topic}: a clearer next step",
            body=(
                f"For {req.country}, {req.topic.lower()} deserves clear, practical guidance. "
                f"{req.goal} starts with a specialist conversation shaped around your needs."
            ),
            hashtags=[f"#{req.brand_id.title()}", "#RiskManagement"],
        )
        for platform in req.platforms
    ]


def localize(
    asset: GeneratedAsset,
    language: str,
    country: str,
    brand_id: str,
) -> GeneratedAsset:
    """Keep the mock deterministic while preserving the contract."""

    del country, brand_id
    return asset.model_copy()


def check_compliance(text: str, brand_id: str, platform: str) -> ComplianceResult:
    """Catch the demo's absolute-claim failure without an LLM call."""

    del brand_id, platform
    lower = text.lower()
    banned = [
        ("guaranteed", "Unsupported absolute coverage claim", "CLAIM_001"),
        ("100% covered", "Unsupported absolute coverage claim", "CLAIM_002"),
        ("zero risk", "Unsupported absolute risk claim", "CLAIM_003"),
    ]
    issues = [
        ComplianceIssue(text=term, reason=reason, rule_id=rule_id)
        for term, reason, rule_id in banned
        if term in lower
    ]
    if issues:
        return ComplianceResult(
            result="FAIL",
            risk="HIGH",
            rules=[issue.rule_id for issue in issues],
            issues=issues,
            suggested_revision="Replace absolute wording with coverage subject to policy terms.",
        )
    return ComplianceResult(result="PASS", risk="LOW")


def get_relevant_lessons(brand_id: str, platform: str, limit: int = 5) -> list[str]:
    try:
        with get_connection() as connection:
            rows = connection.execute(
                """
                select note
                from lessons
                where brand_id = %s and (platform = %s or platform is null)
                order by created_at desc
                limit %s
                """,
                (brand_id, platform, limit),
            ).fetchall()
        return [row["note"] for row in rows]
    except Exception:
        return []


def record_lesson(
    asset_id: str,
    reason_tag: str,
    note: str,
    original: str,
    edited: str | None,
    brand_id: str,
    platform: str | None = None,
) -> None:
    """Persist the mock lesson so the seeded demo remains end-to-end useful."""

    safe_note = note or reason_tag or "Reviewer correction"
    with get_connection() as connection:
        connection.execute(
            """
            insert into lessons
              (brand_id, platform, reason_tag, note, original_body, edited_body, asset_id)
            values (%s, %s, %s, %s, %s, %s, %s)
            """,
            (brand_id, platform, reason_tag or "OTHER", safe_note, original, edited, asset_id),
        )


def scan_competitor(competitor_id: str) -> dict:
    digest = hashlib.sha256(competitor_id.encode()).hexdigest()
    return {
        "competitor_id": competitor_id,
        "hash": digest,
        "changed": False,
        "summary": "skipped in the hackathon mock",
    }


def now_utc() -> datetime:
    return datetime.now(timezone.utc)
