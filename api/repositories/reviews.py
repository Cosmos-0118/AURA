"""Review Queue and Decision Repository."""

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

try:
    from .events import log_event
    from .lessons import create_lesson
except ImportError:
    from repositories.events import log_event
    from repositories.lessons import create_lesson


def enqueue_for_review(db: Any, campaign_id: str) -> str:
    """Insert or update campaign in review_queue."""
    rq_id = str(uuid4())
    db.execute(
        """
        INSERT INTO review_queue (id, campaign_id, status)
        VALUES (%s, %s, 'pending_review')
        """,
        (rq_id, campaign_id),
    )
    return rq_id


def get_review_queue(db: Any, status: str | None = None) -> list[dict[str, Any]]:
    """Fetch review queue items with campaign metadata."""
    query = """
        SELECT
            rq.id as review_id,
            rq.campaign_id,
            rq.status as review_status,
            rq.reviewer_note,
            rq.feedback_tag,
            rq.reviewed_at,
            rq.created_at as queued_at,
            c.brand_id,
            c.title as campaign_title,
            c.objective,
            c.language,
            c.thesis,
            c.target_audience
        FROM review_queue rq
        JOIN campaigns c ON c.id = rq.campaign_id
    """
    params = []
    if status and status != "all":
        query += " WHERE rq.status = %s"
        params.append(status)
    query += " ORDER BY rq.created_at DESC"

    return db.execute(query, tuple(params)).fetchall()


def approve_campaign(
    db: Any, campaign_id: str, reviewer_note: str | None = None
) -> dict[str, Any]:
    """Execute approval transaction for campaign."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    db.execute(
        "UPDATE campaigns SET status = 'approved' WHERE id = %s",
        (campaign_id,),
    )
    db.execute(
        """
        UPDATE review_queue
        SET status = 'approved', reviewer_note = %s, reviewed_at = %s
        WHERE campaign_id = %s
        """,
        (reviewer_note or "Approved by reviewer", now, campaign_id),
    )

    log_event(
        db,
        campaign_id=campaign_id,
        event_type="approved",
        description="Campaign approved for publishing queue by reviewer",
        metadata={"reviewer_note": reviewer_note},
    )

    return {"status": "approved", "campaign_id": campaign_id, "reviewed_at": now}


def reject_campaign(
    db: Any, campaign_id: str, tag: str, note: str, platform: str | None = None
) -> dict[str, Any]:
    """Execute rejection transaction and persist lesson for negative guidance."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Fetch campaign metadata for the lesson
    c_row = db.execute("SELECT * FROM campaigns WHERE id = %s", (campaign_id,)).fetchone()
    brand_id = c_row.get("brand_id") if c_row else None
    thesis = c_row.get("thesis") if c_row else None

    # Update statuses
    db.execute(
        "UPDATE campaigns SET status = 'rejected' WHERE id = %s",
        (campaign_id,),
    )
    db.execute(
        """
        UPDATE review_queue
        SET status = 'rejected', feedback_tag = %s, reviewer_note = %s, reviewed_at = %s
        WHERE campaign_id = %s
        """,
        (tag, note, now, campaign_id),
    )

    # Create lesson in lessons table
    lesson_id = create_lesson(
        db,
        brand_id=brand_id,
        platform=platform,
        tag=tag,
        note=note,
        original_content=thesis,
        source_campaign_id=campaign_id,
    )

    log_event(
        db,
        campaign_id=campaign_id,
        event_type="rejected",
        description=f"Campaign rejected with reason {tag}: {note}",
        metadata={"feedback_tag": tag, "reviewer_note": note, "lesson_id": lesson_id},
    )

    log_event(
        db,
        campaign_id=campaign_id,
        event_type="lesson_created",
        description=f"Generated negative guidance rule: {tag} ({note})",
        metadata={"lesson_id": lesson_id, "brand_id": brand_id, "tag": tag},
    )

    return {
        "status": "rejected",
        "campaign_id": campaign_id,
        "lesson_id": lesson_id,
        "feedback_tag": tag,
        "note": note,
    }


def edit_campaign_content(
    db: Any,
    campaign_id: str,
    platform: str,
    new_content: str,
    new_title: str | None = None,
    tag: str | None = None,
    note: str | None = None,
) -> dict[str, Any]:
    """Edit platform content, preserve original version in event audit, and create lesson if feedback provided."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    # Retrieve current platform content to preserve original
    curr = db.execute(
        "SELECT * FROM campaign_platform_content WHERE campaign_id = %s AND platform = %s",
        (campaign_id, platform),
    ).fetchone()

    original_content = curr.get("content") if curr else ""

    # Update content
    db.execute(
        """
        UPDATE campaign_platform_content
        SET content = %s, title = COALESCE(%s, title)
        WHERE campaign_id = %s AND platform = %s
        """,
        (new_content, new_title, campaign_id, platform),
    )

    # Update campaign status
    db.execute(
        "UPDATE campaigns SET status = 'edited' WHERE id = %s",
        (campaign_id,),
    )
    db.execute(
        """
        UPDATE review_queue
        SET status = 'edited', reviewer_note = %s, feedback_tag = %s, reviewed_at = %s
        WHERE campaign_id = %s
        """,
        (note or "Content revised by editor", tag, now, campaign_id),
    )

    lesson_id = None
    if tag and note:
        c_row = db.execute("SELECT brand_id FROM campaigns WHERE id = %s", (campaign_id,)).fetchone()
        brand_id = c_row.get("brand_id") if c_row else None
        lesson_id = create_lesson(
            db,
            brand_id=brand_id,
            platform=platform,
            tag=tag,
            note=note,
            original_content=original_content,
            corrected_content=new_content,
            source_campaign_id=campaign_id,
        )

    log_event(
        db,
        campaign_id=campaign_id,
        event_type="edited",
        description=f"Edited copy for platform {platform}",
        metadata={
            "platform": platform,
            "original_content": original_content,
            "edited_content": new_content,
            "feedback_tag": tag,
            "note": note,
            "lesson_id": lesson_id,
        },
    )

    return {
        "status": "edited",
        "campaign_id": campaign_id,
        "platform": platform,
        "lesson_id": lesson_id,
    }
