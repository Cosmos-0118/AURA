from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

try:
    from ..db import get_connection
    from ..schemas import (
        Asset,
        AssetPatch,
        AssetStatus,
        BrandId,
        ComplianceResult,
        Language,
        LocalizeRequest,
        Platform,
        ReasonTag,
        ReviewAction,
    )
except ImportError:
    from db import get_connection
    from schemas import (
        Asset,
        AssetPatch,
        AssetStatus,
        BrandId,
        ComplianceResult,
        Language,
        LocalizeRequest,
        Platform,
        ReasonTag,
        ReviewAction,
    )

router = APIRouter(prefix="/api/assets", tags=["assets"])

_ASSET_SELECT = """
select a.*,
       c.result as compliance_result,
       c.risk as compliance_risk,
       c.rules as compliance_rules,
       c.issues as compliance_issues,
       c.suggested_revision as compliance_suggested_revision
from content_assets a
left join lateral (
  select result, risk, rules, issues, suggested_revision
  from compliance_checks
  where asset_id = a.id
  order by created_at desc
  limit 1
) c on true
"""


def _asset(row: dict[str, Any]) -> Asset:
    compliance = None
    if row["compliance_result"] is not None:
        compliance = ComplianceResult(
            result=row["compliance_result"],
            risk=row["compliance_risk"],
            rules=row["compliance_rules"],
            issues=row["compliance_issues"],
            suggested_revision=row["compliance_suggested_revision"],
        )
    return Asset(
        id=str(row["id"]),
        campaign_id=str(row["campaign_id"]) if row["campaign_id"] else None,
        brand_id=row["brand_id"],
        platform=row["platform"],
        content_type=row["content_type"],
        variant=row["variant"],
        language=row["language"],
        title=row["title"],
        body=row["body"],
        hashtags=row["hashtags"],
        media_url=row["media_url"],
        status=row["status"],
        compliance=compliance,
        created_at=row["created_at"],
        approved_at=row["approved_at"],
        approved_by=row["approved_by"],
    )


def _get_asset_row(connection, asset_id: str):
    return connection.execute(_ASSET_SELECT + " where a.id = %s", (asset_id,)).fetchone()


def _lesson_recorder():
    try:
        from ..agents.lessons import record_lesson
    except ImportError:
        try:
            from agents.lessons import record_lesson
        except ImportError:
            try:
                from agents._stubs import record_lesson
            except ImportError:
                from ..agents._stubs import record_lesson
    return record_lesson


def _record_lesson(
    asset_id: str,
    reason_tag: str,
    note: str,
    original: str,
    edited: str | None,
    brand_id: str,
    platform: str | None,
) -> None:
    """Call the lesson agent, with a DB fallback if that implementation fails."""

    try:
        _lesson_recorder()(
            asset_id,
            reason_tag,
            note or reason_tag or "Reviewer correction",
            original,
            edited,
            brand_id,
            platform,
        )
        return
    except Exception as recorder_error:
        try:
            with get_connection() as connection:
                connection.execute(
                    """
                    insert into lessons
                      (brand_id, platform, reason_tag, note, original_body, edited_body, asset_id)
                    values (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        brand_id,
                        platform,
                        reason_tag or "OTHER",
                        note or reason_tag or "Reviewer correction",
                        original,
                        edited,
                        asset_id,
                    ),
                )
        except Exception as fallback_error:
            raise RuntimeError("Failed to record reviewer lesson") from recorder_error


@router.get("", response_model=list[Asset])
def list_assets(
    status: str | None = None,
    brand_id: BrandId | None = None,
    platform: Platform | None = None,
    campaign_id: str | None = None,
) -> list[Asset]:
    filters: list[str] = []
    params: list[Any] = []
    if status:
        statuses = ["pending_review", "compliance_failed"] if status == "queue" else status.split(",")
        allowed = {
            "draft",
            "pending_review",
            "compliance_failed",
            "approved",
            "rejected",
            "scheduled",
            "published",
        }
        if any(value not in allowed for value in statuses):
            raise HTTPException(status_code=422, detail="Invalid asset status")
        filters.append("a.status = any(%s)")
        params.append(statuses)
    if brand_id:
        filters.append("a.brand_id = %s")
        params.append(brand_id)
    if platform:
        filters.append("a.platform = %s")
        params.append(platform)
    if campaign_id:
        filters.append("a.campaign_id = %s")
        params.append(campaign_id)
    query = _ASSET_SELECT
    if filters:
        query += " where " + " and ".join(filters)
    query += " order by a.created_at desc"
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [_asset(row) for row in rows]


@router.get("/{asset_id}", response_model=Asset)
def get_asset(asset_id: str) -> Asset:
    with get_connection() as connection:
        row = _get_asset_row(connection, asset_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return _asset(row)


@router.post("/{asset_id}/approve", response_model=Asset)
def approve_asset(asset_id: str, action: ReviewAction | None = None) -> Asset:
    action = action or ReviewAction()
    now = datetime.now(timezone.utc)
    with get_connection() as connection:
        current = _get_asset_row(connection, asset_id)
        if current is None:
            raise HTTPException(status_code=404, detail="Asset not found")
        original = current["body"]
        edited = action.edited_body if action.edited_body is not None else original
        changed = edited != original
        review_action = "edit" if changed else "approve"
        row = connection.execute(
            """
            update content_assets
            set body = %s, status = 'approved', approved_at = %s, approved_by = %s
            where id = %s
            returning id
            """,
            (edited, now, action.approved_by or "reviewer", asset_id),
        ).fetchone()
        connection.execute(
            """
            insert into reviews (asset_id, action, reason_tag, note, original_body, edited_body)
            values (%s, %s, %s, %s, %s, %s)
            """,
            (row["id"], review_action, action.reason_tag, action.note, original, edited if changed else None),
        )
        updated = _get_asset_row(connection, asset_id)

    if changed:
        _record_lesson(
            asset_id,
            action.reason_tag or "OTHER",
            action.note or action.reason_tag or "Reviewer edit",
            original,
            edited,
            updated["brand_id"],
            updated["platform"],
        )
    return _asset(updated)


@router.post("/{asset_id}/reject", response_model=Asset)
def reject_asset(asset_id: str, action: ReviewAction | None = None) -> Asset:
    action = action or ReviewAction()
    reason_tag: ReasonTag = action.reason_tag or "OTHER"
    note = action.note or reason_tag
    with get_connection() as connection:
        current = _get_asset_row(connection, asset_id)
        if current is None:
            raise HTTPException(status_code=404, detail="Asset not found")
        original = current["body"]
        connection.execute(
            "update content_assets set status = 'rejected' where id = %s", (asset_id,)
        )
        connection.execute(
            """
            insert into reviews (asset_id, action, reason_tag, note, original_body, edited_body)
            values (%s, 'reject', %s, %s, %s, %s)
            """,
            (asset_id, reason_tag, note, original, action.edited_body),
        )
        updated = _get_asset_row(connection, asset_id)

    _record_lesson(
        asset_id,
        reason_tag,
        note,
        original,
        action.edited_body,
        updated["brand_id"],
        updated["platform"],
    )
    return _asset(updated)


@router.patch("/{asset_id}", response_model=Asset)
def patch_asset(asset_id: str, body: AssetPatch) -> Asset:
    if body.body is None and body.title is None:
        raise HTTPException(status_code=400, detail="Provide body or title to update")
    with get_connection() as connection:
        current = _get_asset_row(connection, asset_id)
        if current is None:
            raise HTTPException(status_code=404, detail="Asset not found")
        new_body = body.body if body.body is not None else current["body"]
        new_title = body.title if body.title is not None else current["title"]
        connection.execute(
            "update content_assets set body = %s, title = %s where id = %s",
            (new_body, new_title, asset_id),
        )
        connection.execute(
            """
            insert into reviews (asset_id, action, note, original_body, edited_body)
            values (%s, 'edit', 'Edited in review queue', %s, %s)
            """,
            (asset_id, current["body"], new_body if new_body != current["body"] else None),
        )
        updated = _get_asset_row(connection, asset_id)
    return _asset(updated)


@router.post("/{asset_id}/regenerate", response_model=Asset)
def regenerate_asset(asset_id: str) -> Asset:
    raise HTTPException(status_code=501, detail="not in this sprint")


@router.post("/{asset_id}/localize", response_model=Asset)
def localize_asset(asset_id: str, body: LocalizeRequest) -> Asset:
    raise HTTPException(status_code=501, detail="not in this sprint")
