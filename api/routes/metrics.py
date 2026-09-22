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
              count(*) as assets_total,
              coalesce(sum(case when status in ('pending_review', 'compliance_failed') then 1 else 0 end), 0)
                as assets_pending,
              (select count(*) from reviews where action = 'reject') as rejected,
              (select count(*) from reviews where action = 'approve') as approved,
              (select count(*) from reviews where edited_body is not null) as edits,
              (select count(distinct asset_id) from reviews) as reviewed_assets,
              (select count(distinct asset_id) from compliance_checks where result = 'FAIL')
                as failed_assets,
              (select count(*) from lessons) as lessons_count
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
