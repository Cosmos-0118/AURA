"""The intentionally small AURA campaign pipeline."""

import os

from psycopg.types.json import Json

try:
    from .db import get_connection
    from .schemas import ContentRequest
except ImportError:  # Supports `cd api && uv run uvicorn main:app`.
    from db import get_connection
    from schemas import ContentRequest


def _agent_functions():
    use_mocks = os.getenv("AURA_MOCK_AGENTS", "true").lower() == "true"
    if use_mocks:
        try:
            from .agents._stubs import check_compliance, generate_content, get_relevant_lessons
        except ImportError:
            from agents._stubs import check_compliance, generate_content, get_relevant_lessons
        return generate_content, check_compliance, get_relevant_lessons

    try:
        from .agents.content import generate_content
        from .agents.compliance import check_compliance
        from .agents.lessons import get_relevant_lessons
    except ImportError:
        try:
            from agents.content import generate_content
            from agents.compliance import check_compliance
            from agents.lessons import get_relevant_lessons
        except ImportError:
            from agents._stubs import check_compliance, generate_content, get_relevant_lessons
    return generate_content, check_compliance, get_relevant_lessons


def _set_campaign_status(campaign_id: str, status: str, error: str | None = None) -> None:
    with get_connection() as connection:
        connection.execute(
            """
            update campaigns
            set status = %s,
                error = %s,
                completed_at = case when %s in ('completed', 'failed') then now() else completed_at end
            where id = %s
            """,
            (status, error, status, campaign_id),
        )


def run_pipeline(campaign_id: str) -> None:
    """Generate, check, and persist a campaign without introducing a graph framework."""

    try:
        with get_connection() as connection:
            campaign = connection.execute(
                "select * from campaigns where id = %s", (campaign_id,)
            ).fetchone()
        if campaign is None:
            return

        _set_campaign_status(campaign_id, "running")
        generate_content, check_compliance, get_relevant_lessons = _agent_functions()
        lessons = get_relevant_lessons(campaign["brand_id"], "linkedin")
        request = ContentRequest(
            brand_id=campaign["brand_id"],
            topic=campaign["topic"],
            country=campaign["country"],
            goal=campaign["goal"],
            platforms=campaign["platforms"],
            language=campaign["language"],
            lessons=lessons,
            research_summary=None,
        )
        generated_assets = generate_content(request)

        with get_connection() as connection:
            for generated in generated_assets:
                compliance = check_compliance(
                    generated.body, campaign["brand_id"], generated.platform
                )
                asset_status = (
                    "compliance_failed" if compliance.result == "FAIL" else "pending_review"
                )
                asset = connection.execute(
                    """
                    insert into content_assets
                      (campaign_id, brand_id, platform, content_type, variant, language,
                       title, body, hashtags, status)
                    values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    returning id
                    """,
                    (
                        campaign_id,
                        campaign["brand_id"],
                        generated.platform,
                        generated.content_type,
                        generated.variant,
                        campaign["language"],
                        generated.title,
                        generated.body,
                        Json(generated.hashtags),
                        asset_status,
                    ),
                ).fetchone()
                connection.execute(
                    """
                    insert into compliance_checks
                      (asset_id, result, risk, rules, issues, suggested_revision)
                    values (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        asset["id"],
                        compliance.result,
                        compliance.risk,
                        Json(compliance.rules),
                        Json([issue.model_dump() for issue in compliance.issues]),
                        compliance.suggested_revision,
                    ),
                )

        _set_campaign_status(campaign_id, "completed")
    except Exception as exc:
        try:
            _set_campaign_status(campaign_id, "failed", str(exc))
        except Exception:
            pass
