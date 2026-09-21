from fastapi import APIRouter

try:
    from ..db import get_connection
    from ..schemas import Metrics
except ImportError:
    from db import get_connection
    from schemas import Metrics

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("", response_model=Metrics)
def get_metrics() -> Metrics:
    with get_connection() as connection:
        row = connection.execute(
            """
            select
              count(*)::int as assets_total,
              count(*) filter (where status in ('pending_review', 'compliance_failed'))::int
                as assets_pending,
              (select count(*)::int from reviews where action = 'reject') as rejected,
              (select count(*)::int from reviews where action = 'approve') as approved,
              (select count(*)::int from reviews where edited_body is not null) as edits,
              (select count(distinct asset_id)::int from reviews) as reviewed_assets,
              (select count(distinct asset_id)::int from compliance_checks where result = 'FAIL')
                as failed_assets,
              (select count(*)::int from lessons) as lessons_count
            from content_assets
            """
        ).fetchone()

    decisions = row["approved"] + row["rejected"]
    assets_total = row["assets_total"]
    reviewed_assets = row["reviewed_assets"]
    return Metrics(
        rejection_rate=row["rejected"] / decisions if decisions else 0.0,
        avg_edits_per_post=row["edits"] / reviewed_assets if reviewed_assets else 0.0,
        lessons_count=row["lessons_count"],
        compliance_failure_rate=row["failed_assets"] / assets_total if assets_total else 0.0,
        assets_total=assets_total,
        assets_pending=row["assets_pending"],
    )
