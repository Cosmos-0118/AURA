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
    platforms: list[str] | str | None = None,
) -> str:
    """Create a campaign row in draft or generating status."""
    platforms_val = (
        json.dumps(platforms)
        if isinstance(platforms, list)
        else (platforms or '["linkedin"]')
    )
    db.execute(
        """
        INSERT INTO campaigns
            (id, brand_id, title, topic, goal, objective, language, thesis, target_audience, status, platforms)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            campaign_id,
            brand_id,
            title or thesis[:100],
            thesis,
            objective,
            objective,
            language,
            thesis,
            target_audience,
            status,
            platforms_val,
        ),
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
    campaign_facts_val = content_pkg.get("campaign_facts")
    facts_json = json.dumps(campaign_facts_val) if campaign_facts_val else None

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
                lessons_used = %s,
                campaign_facts = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (title, provider, model, lessons_json, facts_json, campaign_id),
        )
    else:
        db.execute(
            """
            INSERT INTO campaigns
                (id, brand_id, title, objective, language, thesis, target_audience, status, generation_provider, generation_model, lessons_used, campaign_facts)
            VALUES
                (%s, %s, %s, %s, %s, %s, %s, 'generated', %s, %s, %s, %s)
            """,
            (campaign_id, brand_id, title, objective, language, thesis, target_audience, provider, model, lessons_json, facts_json),
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

        values = (
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
        )
        existing_content = db.execute(
            "SELECT id FROM campaign_platform_content WHERE campaign_id = %s AND platform = %s",
            (campaign_id, p),
        ).fetchone()
        if existing_content:
            db.execute(
                """
                UPDATE campaign_platform_content
                SET title = %s,
                    content = %s,
                    hashtags = %s,
                    hook = %s,
                    script = %s,
                    captions = %s,
                    visual_concept = %s,
                    image_generation_prompt = %s,
                    video_generation_prompt = %s,
                    language = %s
                WHERE id = %s
                """,
                values + (existing_content["id"],),
            )
        else:
            db.execute(
                """
                INSERT INTO campaign_platform_content
                    (id, campaign_id, platform, title, content, hashtags, hook, script, captions, visual_concept, image_generation_prompt, video_generation_prompt, language)
                VALUES
                    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (cpc_id, campaign_id, p) + values,
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

    curr_status = c_row.get("status") or "draft"
    if curr_status == "pending_review":
        return {
            "success": True,
            "campaign_id": campaign_id,
            "status": "pending_review",
            "message": "Campaign is already enqueued for verification.",
        }

    valid_statuses = ["generated", "edited", "draft", "rejected", "approved"]
    if curr_status not in valid_statuses:
        raise ValueError(
            f"Campaign cannot be submitted for verification from current status '{curr_status}'. "
            f"Allowed states: {', '.join(valid_statuses)}."
        )

    # Update campaign status
    db.execute(
        "UPDATE campaigns SET status = 'pending_review', updated_at = CURRENT_TIMESTAMP WHERE id = %s",
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
        metadata={"brand_id": c_row["brand_id"], "thesis": c_row.get("thesis")},
    )

    return {
        "success": True,
        "campaign_id": campaign_id,
        "status": "pending_review",
        "message": "Campaign submitted for verification.",
    }


def resubmit_campaign_for_review(db: Any, campaign_id: str, note: str | None = None) -> dict[str, Any]:
    """Resubmit a campaign for review, incrementing cycle and recording audit trail."""
    c_row = db.execute("SELECT * FROM campaigns WHERE id = %s", (campaign_id,)).fetchone()
    if not c_row:
        raise ValueError(f"Campaign {campaign_id} not found")

    db.execute(
        "UPDATE campaigns SET status = 'pending_review', updated_at = CURRENT_TIMESTAMP WHERE id = %s",
        (campaign_id,),
    )

    enqueue_for_review(db, campaign_id, is_resubmission=True)

    # Get updated cycle
    curr_rq = db.execute(
        "SELECT review_cycle FROM review_queue WHERE campaign_id = %s AND is_current = 1 LIMIT 1",
        (campaign_id,),
    ).fetchone()
    cycle = curr_rq.get("review_cycle", 1) if curr_rq else 1

    log_event(
        db,
        campaign_id=campaign_id,
        event_type="resubmitted_for_review",
        description=f"Campaign resubmitted for review (Cycle {cycle}). Note: {note or 'None provided'}",
        metadata={"review_cycle": cycle, "note": note},
    )

    return {
        "success": True,
        "campaign_id": campaign_id,
        "status": "pending_review",
        "review_cycle": cycle,
        "message": f"Campaign resubmitted for review (Cycle {cycle}).",
    }


def list_campaign_history_summaries(db: Any) -> list[dict[str, Any]]:
    """List all campaigns with summary counts, review cycles, and media status."""
    campaigns = db.execute(
        "SELECT * FROM campaigns ORDER BY created_at DESC"
    ).fetchall()

    results = []
    for c in campaigns:
        cid = str(c["id"])

        # Check media
        media_rows = db.execute(
            "SELECT media_type, media_stage, status, watermarked FROM campaign_media WHERE campaign_id = %s",
            (cid,),
        ).fetchall()
        has_final_image = any(
            m["media_type"] == "image" and m.get("media_stage") == "final" and m.get("status") == "completed"
            for m in media_rows
        )
        has_final_video = any(
            m["media_type"] == "video" and m.get("media_stage") == "final" and m.get("status") == "completed"
            for m in media_rows
        )
        has_original_image = any(
            m["media_type"] == "image" and m.get("media_stage") == "original" and m.get("status") == "completed"
            for m in media_rows
        )

        # Review cycle
        rq = db.execute(
            "SELECT review_cycle, status FROM review_queue WHERE campaign_id = %s ORDER BY created_at DESC LIMIT 1",
            (cid,),
        ).fetchone()
        review_cycle = rq.get("review_cycle", 1) if rq else 1
        review_status = rq.get("status") if rq else None

        # Publications count
        pub_count_row = db.execute(
            "SELECT COUNT(*) as cnt FROM campaign_publications WHERE campaign_id = %s AND status = 'published'",
            (cid,),
        ).fetchone()
        pub_count = pub_count_row["cnt"] if pub_count_row else 0

        # Platforms
        platforms_val = c.get("platforms")
        if isinstance(platforms_val, str):
            try:
                platforms_val = json.loads(platforms_val)
            except Exception:
                platforms_val = [platforms_val]
        elif not platforms_val:
            content_plats = db.execute(
                "SELECT DISTINCT platform FROM campaign_platform_content WHERE campaign_id = %s",
                (cid,),
            ).fetchall()
            platforms_val = [p["platform"] for p in content_plats] or ["linkedin"]

        results.append({
            "id": cid,
            "brand_id": c["brand_id"],
            "title": c.get("title") or c.get("thesis") or "Untitled Campaign",
            "thesis": c.get("thesis"),
            "objective": c.get("objective") or c.get("goal") or "Awareness",
            "status": c.get("status") or "draft",
            "created_at": c["created_at"],
            "updated_at": c.get("updated_at"),
            "platforms": platforms_val,
            "has_final_image": has_final_image,
            "has_final_video": has_final_video,
            "has_original_image": has_original_image,
            "review_cycle": review_cycle,
            "review_status": review_status,
            "publications_count": pub_count,
        })

    return results


def get_campaign_workspace_history(db: Any, campaign_id: str) -> dict[str, Any]:
    """Retrieve full history data including all versions of content, media, reviews, and events."""
    c_row = db.execute("SELECT * FROM campaigns WHERE id = %s", (campaign_id,)).fetchone()
    if not c_row:
        raise ValueError(f"Campaign {campaign_id} not found")

    # Content across all versions
    contents = db.execute(
        """
        SELECT * FROM campaign_platform_content
        WHERE campaign_id = %s
        ORDER BY platform ASC, version ASC, created_at ASC
        """,
        (campaign_id,),
    ).fetchall()

    for item in contents:
        if isinstance(item.get("hashtags"), str):
            try:
                item["hashtags"] = json.loads(item["hashtags"])
            except Exception:
                item["hashtags"] = []
        if "version" not in item or item["version"] is None:
            item["version"] = 1
        if "is_current" not in item or item["is_current"] is None:
            item["is_current"] = 1

    # Media across all versions
    media = db.execute(
        "SELECT * FROM campaign_media WHERE campaign_id = %s ORDER BY created_at ASC",
        (campaign_id,),
    ).fetchall()

    for m in media:
        if m.get("watermark_config") and isinstance(m["watermark_config"], str):
            try:
                m["watermark_config"] = json.loads(m["watermark_config"])
            except Exception:
                pass
        lp = m.get("local_path")
        m["local_path"] = f"/{lp}" if lp and not lp.startswith("/") else lp

    # Review history cycles
    review_cycles = db.execute(
        "SELECT * FROM review_queue WHERE campaign_id = %s ORDER BY created_at ASC",
        (campaign_id,),
    ).fetchall()

    # Publications
    publications = db.execute(
        "SELECT * FROM campaign_publications WHERE campaign_id = %s ORDER BY created_at DESC",
        (campaign_id,),
    ).fetchall()

    # Events
    events = db.execute(
        "SELECT * FROM campaign_events WHERE campaign_id = %s ORDER BY created_at ASC",
        (campaign_id,),
    ).fetchall()
    for e in events:
        if isinstance(e.get("metadata"), str):
            try:
                e["metadata"] = json.loads(e["metadata"])
            except Exception:
                pass

    # Lessons
    lessons = []
    try:
        lessons = db.execute(
            "SELECT * FROM lessons WHERE source_campaign_id = %s ORDER BY created_at DESC",
            (campaign_id,),
        ).fetchall()
    except Exception:
        pass

    if not lessons:
        try:
            lessons = db.execute(
                "SELECT * FROM lessons_learned WHERE campaign_id = %s ORDER BY created_at DESC",
                (campaign_id,),
            ).fetchall()
        except Exception:
            lessons = []

    return {
        "campaign": c_row,
        "contents": contents,
        "media": media,
        "review_cycles": review_cycles,
        "publications": publications,
        "events": events,
        "lessons": lessons,
    }


def save_assistant_regenerated_content(
    db: Any,
    campaign_id: str,
    platform: str,
    content: str,
    title: str | None = None,
    hashtags: list[str] | None = None,
    script: str | None = None,
    visual_concept: str | None = None,
    generation_prompt: str | None = None,
) -> dict[str, Any]:
    """Persist new version of platform content generated by AURA Assistant."""
    # Find current max version for this platform
    v_row = db.execute(
        "SELECT MAX(version) as max_v FROM campaign_platform_content WHERE campaign_id = %s AND platform = %s",
        (campaign_id, platform),
    ).fetchone()
    next_v = (v_row["max_v"] or 1) + 1 if v_row and v_row.get("max_v") else 2

    # Set prior versions is_current = 0
    db.execute(
        "UPDATE campaign_platform_content SET is_current = 0 WHERE campaign_id = %s AND platform = %s",
        (campaign_id, platform),
    )

    new_id = str(uuid4())
    ht_json = json.dumps(hashtags or [])
    db.execute(
        """
        INSERT INTO campaign_platform_content
            (id, campaign_id, platform, title, content, hashtags, script, visual_concept,
             image_generation_prompt, video_generation_prompt, version, is_current)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
        """,
        (
            new_id,
            campaign_id,
            platform,
            title,
            content,
            ht_json,
            script,
            visual_concept,
            generation_prompt if platform in ["linkedin", "instagram", "blog"] else None,
            generation_prompt if platform in ["reel", "x"] else None,
            next_v,
        ),
    )

    log_event(
        db,
        campaign_id=campaign_id,
        event_type="content_regenerated",
        description=f"AURA Assistant regenerated {platform.upper()} content to version {next_v}",
        metadata={"platform": platform, "version": next_v, "title": title},
    )

    return {
        "id": new_id,
        "campaign_id": campaign_id,
        "platform": platform,
        "title": title,
        "content": content,
        "hashtags": hashtags or [],
        "script": script,
        "visual_concept": visual_concept,
        "generation_prompt": generation_prompt,
        "version": next_v,
        "is_current": True,
    }

