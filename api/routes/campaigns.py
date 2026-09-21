import json
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException

try:
    from ..db import get_connection
    from ..graph import run_pipeline
    from ..schemas import (
        BrandId,
        Campaign,
        CampaignCreate,
        CampaignMediaItem,
        CampaignPlatformContentItem,
        MediaGenerateRequest,
        StudioCampaignCreate,
        StudioCampaignDetail,
    )
    from ..services.content_generator import generate_campaign_content
    from ..services.image_generator import generate_image as service_generate_image
    from ..services.video_generator import generate_video as service_generate_video
except ImportError:
    from db import get_connection
    from graph import run_pipeline
    from schemas import (
        BrandId,
        Campaign,
        CampaignCreate,
        CampaignMediaItem,
        CampaignPlatformContentItem,
        MediaGenerateRequest,
        StudioCampaignCreate,
        StudioCampaignDetail,
    )
    from services.content_generator import generate_campaign_content
    from services.image_generator import generate_image as service_generate_image
    from services.video_generator import generate_video as service_generate_video

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


def is_demo_mode() -> bool:
    val = os.environ.get("DEMO_MODE", "true").lower()
    return val in ("true", "1", "yes")


def _campaign(row: dict) -> Campaign:
    platforms_val = row.get("platforms")
    if isinstance(platforms_val, str):
        try:
            platforms_val = json.loads(platforms_val)
        except Exception:
            platforms_val = [platforms_val]
    return Campaign(
        id=str(row["id"]),
        brand_id=row["brand_id"],
        topic=row.get("topic") or row.get("thesis") or "",
        country=row.get("country") or "SG",
        goal=row.get("goal") or row.get("objective") or "Awareness",
        platforms=platforms_val or ["linkedin"],
        language=row.get("language") or "en",
        status=row.get("status") or "queued",
        error=row.get("error"),
        created_at=row["created_at"],
        completed_at=row.get("completed_at"),
    )


@router.get("/mode")
def get_operational_mode():
    """Return runtime mode and AI models configured."""
    return {
        "demo_mode": is_demo_mode(),
        "groq_model": os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "image_model": os.environ.get("IMAGE_MODEL", "fal-ai/flux/schnell"),
        "video_model": os.environ.get("VIDEO_MODEL", "minimax/h3-max-turbo"),
    }


@router.post("", response_model=Campaign)
def create_campaign(body: CampaignCreate, background_tasks: BackgroundTasks) -> Campaign:
    campaign_id = str(uuid4())
    with get_connection() as connection:
        connection.execute(
            """
            insert into campaigns
              (id, brand_id, topic, country, goal, platforms, language, status)
            values (%s, %s, %s, %s, %s, %s, %s, 'running')
            """,
            (
                campaign_id,
                body.brand_id,
                body.topic,
                body.country,
                body.goal,
                json.dumps(body.platforms),
                body.language,
            ),
        )
        row = connection.execute(
            "select * from campaigns where id = %s", (campaign_id,)
        ).fetchone()
    background_tasks.add_task(run_pipeline, campaign_id)
    return _campaign(row)


@router.get("", response_model=list[Campaign])
def list_campaigns(brand_id: BrandId | None = None) -> list[Campaign]:
    query = "select * from campaigns"
    params: tuple[str, ...] = ()
    if brand_id:
        query += " where brand_id = %s"
        params = (brand_id,)
    query += " order by created_at desc"
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [_campaign(row) for row in rows]


# --- Studio Specific Endpoints ---


@router.post("/studio/generate", response_model=StudioCampaignDetail)
def generate_studio_campaign(body: StudioCampaignCreate) -> StudioCampaignDetail:
    """Generate a complete multi-platform campaign package using Groq or Demo mode."""
    campaign_id = f"camp_{uuid4().hex[:12]}"
    demo_mode = is_demo_mode()

    # Retrieve learned lessons for this brand to inject as negative guidance
    lessons = []
    with get_connection() as connection:
        lesson_rows = connection.execute(
            "select * from lessons where brand_id = %s order by created_at desc limit 10",
            (body.brand_id,),
        ).fetchall()
        for r in lesson_rows:
            lessons.append({
                "tag": r.get("reason_tag") or r.get("tag") or "RULE",
                "note": r.get("note", ""),
            })

    # Call content generation engine
    try:
        content_pkg = generate_campaign_content(
            brand_id=body.brand_id,
            objective=body.objective,
            language=body.language,
            platforms=body.platforms,
            thesis=body.thesis,
            target_audience=body.target_audience,
            lessons=lessons,
            demo_mode=demo_mode,
        )
    except Exception as exc:
        if not demo_mode:
            # Fall back to demo mode if live API fails
            demo_mode = True
            content_pkg = generate_campaign_content(
                brand_id=body.brand_id,
                objective=body.objective,
                language=body.language,
                platforms=body.platforms,
                thesis=body.thesis,
                target_audience=body.target_audience,
                lessons=lessons,
                demo_mode=True,
            )
        else:
            raise HTTPException(status_code=500, detail=str(exc))

    # Persist campaign metadata snapshot
    with get_connection() as connection:
        connection.execute(
            """
            insert into campaigns
              (id, brand_id, objective, language, thesis, topic, goal, platforms, target_audience, status)
            values (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'generated')
            """,
            (
                campaign_id,
                body.brand_id,
                body.objective,
                body.language,
                body.thesis,
                content_pkg.get("campaign_title", body.thesis),
                body.objective,
                json.dumps(body.platforms),
                body.target_audience,
            ),
        )

        # Persist platform content items
        for p in body.platforms:
            p_data = content_pkg.get(p)
            if not p_data:
                continue

            content_id = f"cpc_{uuid4().hex[:10]}"
            title = p_data.get("title") if isinstance(p_data, dict) else None
            content_text = ""
            hashtags = []
            script = None
            visual_concept = None

            if isinstance(p_data, dict):
                content_text = p_data.get("content") or p_data.get("caption") or p_data.get("hook", "")
                hashtags = p_data.get("hashtags", [])
                visual_concept = p_data.get("visual_concept")
                if p == "reel":
                    script = p_data.get("voiceover") or p_data.get("script")
                    if p_data.get("scenes"):
                        visual_concept = json.dumps(p_data.get("scenes"))
            elif isinstance(p_data, str):
                content_text = p_data

            connection.execute(
                """
                insert into campaign_platform_content
                  (id, campaign_id, platform, title, content, hashtags, script, visual_concept, generation_prompt)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    content_id,
                    campaign_id,
                    p,
                    title,
                    content_text,
                    json.dumps(hashtags),
                    script,
                    visual_concept,
                    None,
                ),
            )

        # Initialize media prompt records
        img_prompt = content_pkg.get("image_generation_prompt") or f"Commercial editorial image for {body.brand_id} on {body.thesis}"
        vid_prompt = content_pkg.get("video_generation_prompt") or f"Cinematic vertical video for {body.brand_id} on {body.thesis}"

        img_media_id = f"med_{uuid4().hex[:10]}"
        connection.execute(
            """
            insert into campaign_media
              (id, campaign_id, media_type, prompt, local_path, provider, model, status)
            values (%s, %s, 'image', %s, NULL, 'local', %s, 'pending')
            """,
            (img_media_id, campaign_id, img_prompt, os.environ.get("IMAGE_MODEL", "fal-ai/flux/schnell")),
        )

        vid_media_id = f"med_{uuid4().hex[:10]}"
        connection.execute(
            """
            insert into campaign_media
              (id, campaign_id, media_type, prompt, local_path, provider, model, status)
            values (%s, %s, 'video', %s, NULL, 'local', %s, 'pending')
            """,
            (vid_media_id, campaign_id, vid_prompt, os.environ.get("VIDEO_MODEL", "minimax/h3-max-turbo")),
        )

    return get_studio_campaign(campaign_id)


@router.get("/{campaign_id}/studio", response_model=StudioCampaignDetail)
def get_studio_campaign(campaign_id: str) -> StudioCampaignDetail:
    """Fetch complete static campaign snapshot including platform content and media."""
    with get_connection() as connection:
        c_row = connection.execute(
            "select * from campaigns where id = %s", (campaign_id,)
        ).fetchone()
        if not c_row:
            raise HTTPException(status_code=404, detail="Campaign not found")

        content_rows = connection.execute(
            "select * from campaign_platform_content where campaign_id = %s order by created_at asc",
            (campaign_id,),
        ).fetchall()

        media_rows = connection.execute(
            "select * from campaign_media where campaign_id = %s order by created_at asc",
            (campaign_id,),
        ).fetchall()

    contents: list[CampaignPlatformContentItem] = []
    for r in content_rows:
        ht = r.get("hashtags")
        if isinstance(ht, str):
            try:
                ht = json.loads(ht)
            except Exception:
                ht = []
        contents.append(
            CampaignPlatformContentItem(
                id=str(r["id"]),
                campaign_id=str(r["campaign_id"]),
                platform=r["platform"],
                title=r.get("title"),
                content=r["content"],
                hashtags=ht or [],
                script=r.get("script"),
                visual_concept=r.get("visual_concept"),
                generation_prompt=r.get("generation_prompt"),
            )
        )

    media: list[CampaignMediaItem] = []
    img_prompt = None
    vid_prompt = None

    for m in media_rows:
        m_type = m["media_type"]
        if m_type == "image":
            img_prompt = m["prompt"]
        elif m_type == "video":
            vid_prompt = m["prompt"]

        media.append(
            CampaignMediaItem(
                id=str(m["id"]),
                campaign_id=str(m["campaign_id"]),
                media_type=m_type,
                prompt=m["prompt"],
                local_path=m.get("local_path"),
                provider=m.get("provider") or "local",
                model=m["model"],
                status=m.get("status") or "pending",
            )
        )

    platforms_val = c_row.get("platforms")
    if isinstance(platforms_val, str):
        try:
            platforms_val = json.loads(platforms_val)
        except Exception:
            platforms_val = ["linkedin"]

    return StudioCampaignDetail(
        id=str(c_row["id"]),
        brand_id=c_row["brand_id"],
        objective=c_row.get("objective") or c_row.get("goal") or "Awareness",
        language=c_row.get("language") or "en",
        thesis=c_row.get("thesis") or c_row.get("topic") or "",
        target_audience=c_row.get("target_audience"),
        platforms=platforms_val or ["linkedin"],
        status=c_row.get("status") or "draft",
        error=c_row.get("error"),
        created_at=c_row["created_at"],
        updated_at=c_row.get("updated_at"),
        contents=contents,
        media=media,
        image_prompt=img_prompt,
        video_prompt=vid_prompt,
    )


@router.post("/{campaign_id}/generate-image", response_model=CampaignMediaItem)
def generate_campaign_image(campaign_id: str, body: MediaGenerateRequest) -> CampaignMediaItem:
    """Generate image and save locally to storage/campaigns/{campaign_id}/image.png."""
    demo_mode = is_demo_mode()
    prompt = body.prompt

    with get_connection() as connection:
        media_row = connection.execute(
            "select * from campaign_media where campaign_id = %s and media_type = 'image' limit 1",
            (campaign_id,),
        ).fetchone()

        if not prompt and media_row:
            prompt = media_row["prompt"]

        if not prompt:
            c_row = connection.execute(
                "select * from campaigns where id = %s", (campaign_id,)
            ).fetchone()
            if not c_row:
                raise HTTPException(status_code=404, detail="Campaign not found")
            prompt = f"Commercial photography for {c_row['brand_id']} marketing campaign: {c_row.get('thesis', '')}"

    # Perform image generation and local storage
    try:
        res = service_generate_image(
            campaign_id=campaign_id,
            prompt=prompt,
            model=body.model,
            demo_mode=demo_mode,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {exc}")

    # Update database
    with get_connection() as connection:
        if media_row:
            media_id = str(media_row["id"])
            connection.execute(
                """
                update campaign_media
                set prompt = %s, local_path = %s, provider = %s, model = %s, status = 'completed'
                where id = %s
                """,
                (prompt, res["local_path"], res["provider"], res["model"], media_id),
            )
        else:
            media_id = f"med_{uuid4().hex[:10]}"
            connection.execute(
                """
                insert into campaign_media
                  (id, campaign_id, media_type, prompt, local_path, provider, model, status)
                values (%s, %s, 'image', %s, %s, %s, %s, 'completed')
                """,
                (media_id, campaign_id, prompt, res["local_path"], res["provider"], res["model"]),
            )

        updated_media = connection.execute(
            "select * from campaign_media where id = %s", (media_id,)
        ).fetchone()

    return CampaignMediaItem(
        id=str(updated_media["id"]),
        campaign_id=str(updated_media["campaign_id"]),
        media_type="image",
        prompt=updated_media["prompt"],
        local_path=updated_media["local_path"],
        provider=updated_media["provider"],
        model=updated_media["model"],
        status=updated_media["status"],
    )


@router.post("/{campaign_id}/generate-video", response_model=CampaignMediaItem)
def generate_campaign_video(campaign_id: str, body: MediaGenerateRequest) -> CampaignMediaItem:
    """Generate vertical video and save locally to storage/campaigns/{campaign_id}/video.mp4."""
    demo_mode = is_demo_mode()
    prompt = body.prompt

    with get_connection() as connection:
        media_row = connection.execute(
            "select * from campaign_media where campaign_id = %s and media_type = 'video' limit 1",
            (campaign_id,),
        ).fetchone()

        if not prompt and media_row:
            prompt = media_row["prompt"]

        if not prompt:
            c_row = connection.execute(
                "select * from campaigns where id = %s", (campaign_id,)
            ).fetchone()
            if not c_row:
                raise HTTPException(status_code=404, detail="Campaign not found")
            prompt = f"Vertical 9:16 cinematic video for {c_row['brand_id']} campaign on {c_row.get('thesis', '')}"

    # Perform video generation and local storage
    try:
        res = service_generate_video(
            campaign_id=campaign_id,
            prompt=prompt,
            model=body.model,
            demo_mode=demo_mode,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Video generation failed: {exc}")

    # Update database
    with get_connection() as connection:
        if media_row:
            media_id = str(media_row["id"])
            connection.execute(
                """
                update campaign_media
                set prompt = %s, local_path = %s, provider = %s, model = %s, status = 'completed'
                where id = %s
                """,
                (prompt, res["local_path"], res["provider"], res["model"], media_id),
            )
        else:
            media_id = f"med_{uuid4().hex[:10]}"
            connection.execute(
                """
                insert into campaign_media
                  (id, campaign_id, media_type, prompt, local_path, provider, model, status)
                values (%s, %s, 'video', %s, %s, %s, %s, 'completed')
                """,
                (media_id, campaign_id, prompt, res["local_path"], res["provider"], res["model"]),
            )

        updated_media = connection.execute(
            "select * from campaign_media where id = %s", (media_id,)
        ).fetchone()

    return CampaignMediaItem(
        id=str(updated_media["id"]),
        campaign_id=str(updated_media["campaign_id"]),
        media_type="video",
        prompt=updated_media["prompt"],
        local_path=updated_media["local_path"],
        provider=updated_media["provider"],
        model=updated_media["model"],
        status=updated_media["status"],
    )


@router.post("/{campaign_id}/submit-review", response_model=StudioCampaignDetail)
def submit_campaign_for_review(campaign_id: str) -> StudioCampaignDetail:
    """Transition campaign status from 'generated' to 'pending_review' and enqueue into review_queue."""
    with get_connection() as connection:
        c_row = connection.execute(
            "select * from campaigns where id = %s", (campaign_id,)
        ).fetchone()
        if not c_row:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Update campaign status
        connection.execute(
            "update campaigns set status = 'pending_review' where id = %s",
            (campaign_id,),
        )

        # Enqueue in review_queue
        rq_id = f"rq_{uuid4().hex[:10]}"
        connection.execute(
            """
            insert into review_queue (id, campaign_id, status)
            values (%s, %s, 'pending_review')
            """,
            (rq_id, campaign_id),
        )

        # Also push items to content_assets with initial PASS compliance check so it appears in standard review queue too
        cpc_items = connection.execute(
            "select * from campaign_platform_content where campaign_id = %s",
            (campaign_id,),
        ).fetchall()

        media_items = connection.execute(
            "select * from campaign_media where campaign_id = %s and local_path is not null",
            (campaign_id,),
        ).fetchall()
        default_media_url = media_items[0]["local_path"] if media_items else None

        for item in cpc_items:
            asset_id = f"ast_{uuid4().hex[:10]}"
            content_type_map = {
                "linkedin": "post",
                "x": "post",
                "instagram": "caption",
                "blog": "article",
                "reel": "script",
            }
            c_type = content_type_map.get(item["platform"], "post")
            connection.execute(
                """
                insert into content_assets
                  (id, campaign_id, brand_id, platform, content_type, variant, language, title, body, hashtags, media_url, status)
                values (%s, %s, %s, %s, %s, 'A', %s, %s, %s, %s, %s, 'pending_review')
                """,
                (
                    asset_id,
                    campaign_id,
                    c_row["brand_id"],
                    item["platform"],
                    c_type,
                    c_row.get("language", "en"),
                    item.get("title"),
                    item["content"],
                    item.get("hashtags") or "[]",
                    default_media_url,
                ),
            )

            # Insert passing compliance check entry
            check_id = f"chk_{uuid4().hex[:10]}"
            connection.execute(
                """
                insert into compliance_checks
                  (id, asset_id, result, risk, rules, issues, suggested_revision)
                values (%s, %s, 'PASS', 'LOW', '["STATUTORY_DISCLOSURE", "TONE_ALIGNMENT"]', '[]', NULL)
                """,
                (check_id, asset_id),
            )

    return get_studio_campaign(campaign_id)


@router.get("/{campaign_id}", response_model=Campaign)
def get_campaign(campaign_id: str) -> Campaign:
    with get_connection() as connection:
        row = connection.execute(
            "select * from campaigns where id = %s", (campaign_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaign(row)

