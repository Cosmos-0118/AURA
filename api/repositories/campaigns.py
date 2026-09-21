"""Campaigns and Platform Content Repository."""

import json
from typing import Any
from uuid import uuid4

try:
    from .events import log_event
    from .reviews import enqueue_for_review
except ImportError:
    from repositories.events import log_event
    from repositories.reviews import enqueue_for_review


def create_campaign(
    db: Any,
    campaign_id: str,
    brand_id: str,
    objective: str,
    language: str,
    thesis: str,
    target_audience: str | None = None,
    status: str = "draft",
    title: str | None = None,
) -> str:
    """Create a campaign row in draft or generating status."""
    db.execute(
        """
        INSERT INTO campaigns
            (id, brand_id, title, objective, language, thesis, target_audience, status)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (campaign_id, brand_id, title or thesis[:100], objective, language, thesis, target_audience, status),
    )

    log_event(
        db,
        campaign_id=campaign_id,
        event_type="campaign_created",
        description=f"Created campaign for brand {brand_id}: {thesis[:60]}",
        metadata={"brand_id": brand_id, "objective": objective, "language": language},
    )
    return campaign_id


def save_generated_campaign_package(
    db: Any,
    campaign_id: str,
    brand_id: str,
    objective: str,
    language: str,
    thesis: str,
    target_audience: str | None,
    content_pkg: dict[str, Any],
    lessons_used: list[dict[str, Any]],
    provider: str,
    model: str,
) -> None:
    """Atomically persist generated campaign, platform content records, and audit event."""
    title = content_pkg.get("campaign_title") or thesis[:120]
    lessons_json = json.dumps(lessons_used) if lessons_used else None

    # Check if campaign exists; update or insert
    existing = db.execute("SELECT id FROM campaigns WHERE id = %s", (campaign_id,)).fetchone()
    if existing:
        db.execute(
            """
            UPDATE campaigns
            SET
                title = %s,
                status = 'generated',
                generation_provider = %s,
                generation_model = %s,
                lessons_used = %s
            WHERE id = %s
            """,
            (title, provider, model, lessons_json, campaign_id),
        )
    else:
        db.execute(
            """
            INSERT INTO campaigns
                (id, brand_id, title, objective, language, thesis, target_audience, status, generation_provider, generation_model, lessons_used)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, 'generated', %s, %s, %s)
            """,
            (campaign_id, brand_id, title, objective, language, thesis, target_audience, provider, model, lessons_json),
        )

    # Platforms to persist
    platforms = ["linkedin", "instagram", "x", "reel", "blog"]
    for p in platforms:
        p_data = content_pkg.get(p)
        if not p_data:
            continue

        cpc_id = str(uuid4())
        p_title = None
        content_text = ""
        hashtags = []
        hook = None
        script = None
        captions = None
        visual_concept = None
        img_prompt = content_pkg.get("image_generation_prompt")
        vid_prompt = content_pkg.get("video_generation_prompt")

        if isinstance(p_data, dict):
            p_title = p_data.get("title")
            content_text = p_data.get("content") or p_data.get("caption") or p_data.get("hook", "")
            hashtags = p_data.get("hashtags", [])
            hook = p_data.get("hook")
            script = p_data.get("script") or p_data.get("voiceover")
            captions = p_data.get("captions")
            visual_concept = p_data.get("visual_concept")
            if p == "reel" and p_data.get("scenes"):
                visual_concept = json.dumps(p_data.get("scenes"))
        elif isinstance(p_data, str):
            content_text = p_data

        db.execute(
            """
            INSERT INTO campaign_platform_content
                (id, campaign_id, platform, title, content, hashtags, hook, script, captions, visual_concept, image_generation_prompt, video_generation_prompt, language)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                title = VALUES(title),
                content = VALUES(content),
                hashtags = VALUES(hashtags),
                hook = VALUES(hook),
                script = VALUES(script),
                captions = VALUES(captions),
                visual_concept = VALUES(visual_concept),
                image_generation_prompt = VALUES(image_generation_prompt),
                video_generation_prompt = VALUES(video_generation_prompt)
            """,
            (
                cpc_id,
                campaign_id,
                p,
                p_title,
                content_text,
                json.dumps(hashtags),
                hook,
                script,
                captions,
                visual_concept,
                img_prompt,
                vid_prompt,
                language,
            ),
        )

    log_event(
        db,
        campaign_id=campaign_id,
        event_type="generation_completed",
        description=f"Generated multi-channel content suite with model {model}",
        metadata={"provider": provider, "model": model, "channels": platforms},
    )


def get_campaign_detail(db: Any, campaign_id: str) -> dict[str, Any] | None:
    """Retrieve full campaign record with platform content, media items, and events."""
    campaign = db.execute("SELECT * FROM campaigns WHERE id = %s", (campaign_id,)).fetchone()
    if not campaign:
        return None

    # Parse lessons_used
    if isinstance(campaign.get("lessons_used"), str):
        try:
            campaign["lessons_used"] = json.loads(campaign["lessons_used"])
        except Exception:
            pass

    contents = db.execute(
        "SELECT * FROM campaign_platform_content WHERE campaign_id = %s ORDER BY created_at ASC",
        (campaign_id,),
    ).fetchall()

    for item in contents:
        if isinstance(item.get("hashtags"), str):
            try:
                item["hashtags"] = json.loads(item["hashtags"])
            except Exception:
                item["hashtags"] = []

    media = db.execute(
        "SELECT * FROM campaign_media WHERE campaign_id = %s ORDER BY created_at ASC",
        (campaign_id,),
    ).fetchall()

    review = db.execute(
        "SELECT * FROM review_queue WHERE campaign_id = %s ORDER BY created_at DESC LIMIT 1",
        (campaign_id,),
    ).fetchone()

    events = db.execute(
        "SELECT * FROM campaign_events WHERE campaign_id = %s ORDER BY created_at ASC",
        (campaign_id,),
    ).fetchall()

    return {
        "campaign": campaign,
        "contents": contents,
        "media": media,
        "review": review,
        "events": events,
    }


def list_campaigns(
    db: Any, brand_id: str | None = None, status: str | None = None
) -> list[dict[str, Any]]:
    """List campaigns with optional brand and status filtering."""
    query = "SELECT * FROM campaigns"
    params = []
    clauses = []

    if brand_id:
        clauses.append("brand_id = %s")
        params.append(brand_id)
    if status:
        clauses.append("status = %s")
        params.append(status)

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY created_at DESC"
    return db.execute(query, tuple(params)).fetchall()


def submit_for_verification(db: Any, campaign_id: str) -> dict[str, Any]:
    """Execute submission transaction: transition status, insert into review_queue, log event."""
    c_row = db.execute("SELECT * FROM campaigns WHERE id = %s", (campaign_id,)).fetchone()
    if not c_row:
        raise ValueError(f"Campaign {campaign_id} not found")

    # Update campaign status
    db.execute(
        "UPDATE campaigns SET status = 'pending_review' WHERE id = %s",
        (campaign_id,),
    )

    # Insert review queue record
    enqueue_for_review(db, campaign_id)

    # Log event
    log_event(
        db,
        campaign_id=campaign_id,
        event_type="submitted_for_review",
        description="Campaign submitted for human verification in Review Queue",
        metadata={"brand_id": c_row["brand_id"], "thesis": c_row["thesis"]},
    )

    return {
        "status": "pending_review",
        "message": "Campaign submitted for verification.",
        "campaign_id": campaign_id,
    }
