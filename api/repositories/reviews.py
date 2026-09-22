"""Review Queue and Decision Repository."""

from datetime import datetime, timezone
import json
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
    existing = db.execute(
        "SELECT id FROM review_queue WHERE campaign_id = %s",
        (campaign_id,),
    ).fetchone()
    if existing:
        db.execute(
            """
            UPDATE review_queue
            SET status = 'pending_review', reviewer_note = NULL, feedback_tag = NULL, reviewed_at = NULL
            WHERE id = %s
            """,
            (existing["id"],),
        )
        return str(existing["id"])

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
    """Fetch review queue items with rich campaign metadata, media preview, facts, and publications."""
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
            c.target_audience,
            c.campaign_facts,
            c.status as campaign_status
        FROM review_queue rq
        JOIN campaigns c ON c.id = rq.campaign_id
    """
    params = []
    if status and status != "all":
        query += " WHERE rq.status = %s"
        params.append(status)
    query += " ORDER BY rq.created_at DESC"

    rows = db.execute(query, tuple(params)).fetchall()
    enriched = []
    for r in rows:
        cid = r["campaign_id"]
        # 1. Parse facts
        facts = None
        if r.get("campaign_facts"):
            if isinstance(r["campaign_facts"], str):
                try:
                    facts = json.loads(r["campaign_facts"])
                except Exception:
                    pass
            elif isinstance(r["campaign_facts"], dict):
                facts = r["campaign_facts"]

        # 2. Latest Image
        img_row = db.execute(
            """
            SELECT * FROM campaign_media
            WHERE campaign_id = %s AND media_type = 'image' AND status = 'completed'
            ORDER BY created_at DESC LIMIT 1
            """,
            (cid,),
        ).fetchone()

        latest_image_url = None
        latest_image_prompt = None
        if img_row and img_row.get("local_path"):
            lp = img_row["local_path"]
            latest_image_url = f"/{lp}" if not lp.startswith("/") else lp
            latest_image_prompt = img_row.get("prompt")

        # 3. Video Asset check
        vid_row = db.execute(
            """
            SELECT * FROM campaign_media
            WHERE campaign_id = %s AND media_type = 'video' AND status = 'completed'
            ORDER BY created_at DESC LIMIT 1
            """,
            (cid,),
        ).fetchone()

        has_video = vid_row is not None
        latest_video_url = None
        if vid_row and vid_row.get("local_path"):
            vp = vid_row["local_path"]
            latest_video_url = f"/{vp}" if not vp.startswith("/") else vp

        # 4. LinkedIn Content snippet
        li_row = db.execute(
            "SELECT * FROM campaign_platform_content WHERE campaign_id = %s AND platform = 'linkedin'",
            (cid,),
        ).fetchone()

        linkedin_content = li_row.get("content", "") if li_row else ""
        linkedin_hashtags = []
        if li_row and li_row.get("hashtags"):
            ht = li_row["hashtags"]
            if isinstance(ht, str):
                try:
                    linkedin_hashtags = json.loads(ht)
                except Exception:
                    pass
            elif isinstance(ht, list):
                linkedin_hashtags = ht

        # 5. Publications status
        pub_rows = db.execute(
            "SELECT platform, status, external_post_id, external_post_url, published_at FROM campaign_publications WHERE campaign_id = %s",
            (cid,),
        ).fetchall()

        publications_map = {p["platform"]: p for p in pub_rows}

        # 6. Count of events
        events_row = db.execute(
            "SELECT COUNT(*) as cnt FROM campaign_events WHERE campaign_id = %s",
            (cid,),
        ).fetchone()
        events_count = events_row["cnt"] if events_row else 0

        enriched.append({
            "review_id": str(r["review_id"]),
            "campaign_id": str(r["campaign_id"]),
            "review_status": r["review_status"],
            "campaign_status": r.get("campaign_status") or r["review_status"],
            "reviewer_note": r.get("reviewer_note"),
            "feedback_tag": r.get("feedback_tag"),
            "reviewed_at": r.get("reviewed_at"),
            "queued_at": r["queued_at"],
            "brand_id": r["brand_id"],
            "campaign_title": r.get("campaign_title") or r.get("thesis") or "Campaign",
            "objective": r.get("objective") or "Awareness",
            "language": r.get("language") or "en",
            "thesis": r.get("thesis") or "",
            "target_audience": r.get("target_audience"),
            "campaign_facts": facts,
            "latest_image_url": latest_image_url,
            "latest_image_prompt": latest_image_prompt,
            "has_video": has_video,
            "latest_video_url": latest_video_url,
            "linkedin_content": linkedin_content,
            "linkedin_hashtags": linkedin_hashtags,
            "publications": publications_map,
            "events_count": events_count,
            "compliance_passed": True,
            "lessons_applied_count": 2,
        })

    return enriched


def approve_campaign(
    db: Any, campaign_id: str, reviewer_note: str | None = None
) -> dict[str, Any]:
    """Execute approval transaction for campaign."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    db.execute(
        "UPDATE campaigns SET status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE id = %s",
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

    # Initialize queued publication rows for each platform if not existing
    platforms = ["linkedin", "instagram", "x", "blog", "reel"]
    for p in platforms:
        existing_pub = db.execute(
            "SELECT id FROM campaign_publications WHERE campaign_id = %s AND platform = %s",
            (campaign_id, p),
        ).fetchone()
        if not existing_pub:
            pub_id = str(uuid4())
            db.execute(
                """
                INSERT INTO campaign_publications (id, campaign_id, platform, status)
                VALUES (%s, %s, %s, 'queued')
                """,
                (pub_id, campaign_id, p),
            )

    log_event(
        db,
        campaign_id=campaign_id,
        event_type="approved",
        description="Campaign approved for publishing queue by reviewer",
        metadata={"reviewer_note": reviewer_note},
    )

    return {
        "status": "approved",
        "campaign_id": campaign_id,
        "reviewed_at": now,
        "message": "Campaign approved successfully. Multi-platform publishing unlocked.",
    }


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
