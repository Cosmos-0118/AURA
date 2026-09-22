import json
import os
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Header, HTTPException
from pydantic import BaseModel

try:
    from ..db import get_db, transaction
    from ..graph import run_pipeline
    from ..repositories import (
        campaigns as campaign_repo,
        events as event_repo,
        lessons as lesson_repo,
        media as media_repo,
        reviews as review_repo,
    )
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
    from db import get_db, transaction
    from graph import run_pipeline
    from repositories import (
        campaigns as campaign_repo,
        events as event_repo,
        lessons as lesson_repo,
        media as media_repo,
        reviews as review_repo,
    )
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

_RUNTIME_DEMO_MODE: bool | None = None


def is_demo_mode(header_val: Any = None) -> bool:
    if header_val is not None and isinstance(header_val, str):
        return header_val.lower() in ("true", "1", "yes")
    if _RUNTIME_DEMO_MODE is not None:
        return _RUNTIME_DEMO_MODE
    val = os.environ.get("DEMO_MODE", "false" if os.environ.get("GROQ_API_KEY") else "true").lower()
    return val in ("true", "1", "yes")


def set_runtime_demo_mode(demo: bool) -> None:
    global _RUNTIME_DEMO_MODE
    _RUNTIME_DEMO_MODE = demo


class ModeUpdateRequest(BaseModel):
    demo_mode: bool


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
    has_groq = bool(os.environ.get("GROQ_API_KEY"))
    has_fal = bool(os.environ.get("FAL_KEY") or os.environ.get("FAL_AI_API_KEY"))
    return {
        "demo_mode": is_demo_mode(),
        "groq_model": os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b"),
        "image_model": os.environ.get("IMAGE_MODEL", "google/nano-banana-2-lites"),
        "video_model": os.environ.get("VIDEO_MODEL", "minimax/h3-max-turbo/text-to-video"),
        "has_groq_key": has_groq,
        "has_fal_key": has_fal,
        "status": "connected",
    }


@router.post("/mode")
def update_operational_mode(body: ModeUpdateRequest):
    """Toggle between mock mode and real API mode at runtime."""
    set_runtime_demo_mode(body.demo_mode)
    return get_operational_mode()


@router.get("/health")
def api_health():
    """Diagnostic health check for database, groq, and fal services."""
    db_status = "connected"
    try:
        with get_db() as db:
            db.execute("SELECT 1")
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "ok",
        "demo_mode": is_demo_mode(),
        "groq_connected": bool(os.environ.get("GROQ_API_KEY")),
        "fal_connected": bool(os.environ.get("FAL_KEY") or os.environ.get("FAL_AI_API_KEY")),
        "database": db_status,
    }


# --- Review Decision Models ---
class ReviewApproveRequest(BaseModel):
    reviewer_note: str | None = None


class ReviewRejectRequest(BaseModel):
    tag: str = "TOO_SALESY"
    note: str
    platform: str | None = None


class ReviewEditRequest(BaseModel):
    platform: str
    new_content: str
    new_title: str | None = None
    tag: str | None = None
    note: str | None = None


# --- Standard Campaign Endpoints ---


@router.post("", response_model=Campaign)
def create_campaign(body: CampaignCreate, background_tasks: BackgroundTasks) -> Campaign:
    campaign_id = str(uuid4())
    with transaction() as db:
        campaign_repo.create_campaign(
            db=db,
            campaign_id=campaign_id,
            brand_id=body.brand_id,
            objective=body.goal,
            language=body.language,
            thesis=body.topic,
            status="draft",
        )
    background_tasks.add_task(run_pipeline, campaign_id)
    with get_db() as db:
        detail = campaign_repo.get_campaign_detail(db, campaign_id)
    if not detail:
        raise HTTPException(status_code=500, detail="Failed to create campaign")
    return _campaign(detail["campaign"])


@router.get("", response_model=list[Campaign])
def list_campaigns(brand_id: BrandId | None = None) -> list[Campaign]:
    with get_db() as db:
        rows = campaign_repo.list_campaigns(db, brand_id=brand_id)
    return [_campaign(row) for row in rows]


# --- Studio Specific Endpoints ---


@router.post("/studio/generate", response_model=StudioCampaignDetail)
def generate_studio_campaign(
    body: StudioCampaignCreate,
    x_demo_mode: str | None = Header(None, alias="X-Demo-Mode"),
) -> StudioCampaignDetail:
    """Generate a complete multi-platform campaign package using Groq or Demo mode, with repository persistence."""
    campaign_id = str(uuid4())
    demo_mode = is_demo_mode(x_demo_mode)

    # Step 1: Retrieve learned lessons from MySQL for negative guidance
    lessons_used: list[dict[str, Any]] = []
    with get_db() as db:
        lesson_rows = lesson_repo.list_lessons(db, brand_id=body.brand_id, limit=10)
        for r in lesson_rows:
            tag = r.get("tag") or r.get("reason_tag") or "RULE"
            note = r.get("note", "")
            lessons_used.append({"id": str(r["id"]), "tag": tag, "note": note})

    # Step 2: Create initial campaign in draft / generating status
    with transaction() as db:
        campaign_repo.create_campaign(
            db=db,
            campaign_id=campaign_id,
            brand_id=body.brand_id,
            objective=body.objective,
            language=body.language,
            thesis=body.thesis,
            target_audience=body.target_audience,
            status="generating",
        )
        event_repo.log_event(
            db,
            campaign_id=campaign_id,
            event_type="generation_started",
            description=f"Initiated campaign content generation for {body.brand_id}",
            metadata={"platforms": body.platforms, "lessons_count": len(lessons_used)},
        )

    # Step 3: Run content generation engine
    provider = "demo_local" if demo_mode else "groq"
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
    try:
        content_pkg = generate_campaign_content(
            brand_id=body.brand_id,
            objective=body.objective,
            language=body.language,
            platforms=body.platforms,
            thesis=body.thesis,
            target_audience=body.target_audience,
            lessons=lessons_used,
            demo_mode=demo_mode,
        )
    except Exception as exc:
        if not demo_mode:
            # Clean fallback to demo mode
            provider = "demo_fallback"
            content_pkg = generate_campaign_content(
                brand_id=body.brand_id,
                objective=body.objective,
                language=body.language,
                platforms=body.platforms,
                thesis=body.thesis,
                target_audience=body.target_audience,
                lessons=lessons_used,
                demo_mode=True,
            )
        else:
            raise HTTPException(status_code=500, detail=str(exc))

    # Step 4: Atomically persist generated campaign and all platform contents
    with transaction() as db:
        campaign_repo.save_generated_campaign_package(
            db=db,
            campaign_id=campaign_id,
            brand_id=body.brand_id,
            objective=body.objective,
            language=body.language,
            thesis=body.thesis,
            target_audience=body.target_audience,
            content_pkg=content_pkg,
            lessons_used=lessons_used,
            provider=provider,
            model=model,
        )

    return get_studio_campaign(campaign_id)


@router.get("/{campaign_id}/studio", response_model=StudioCampaignDetail)
def get_studio_campaign(campaign_id: str) -> StudioCampaignDetail:
    """Fetch complete static campaign snapshot including platform content and media."""
    with get_db() as db:
        detail = campaign_repo.get_campaign_detail(db, campaign_id)

    if not detail:
        raise HTTPException(status_code=404, detail="Campaign not found")

    c_row = detail["campaign"]
    contents: list[CampaignPlatformContentItem] = []
    img_prompt = None
    vid_prompt = None

    for r in detail["contents"]:
        ht = r.get("hashtags")
        if isinstance(ht, str):
            try:
                ht = json.loads(ht)
            except Exception:
                ht = []
        if r.get("image_generation_prompt") and not img_prompt:
            img_prompt = r["image_generation_prompt"]
        if r.get("video_generation_prompt") and not vid_prompt:
            vid_prompt = r["video_generation_prompt"]

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
                generation_prompt=r.get("image_generation_prompt") or r.get("video_generation_prompt"),
            )
        )

    media: list[CampaignMediaItem] = []
    for m in detail["media"]:
        # Map relative path to frontend URL
        local_path = m.get("local_path")
        media_url = f"/{local_path}" if local_path and not local_path.startswith("/") else local_path

        media.append(
            CampaignMediaItem(
                id=str(m["id"]),
                campaign_id=str(m["campaign_id"]),
                media_type=m["media_type"],
                prompt=m["prompt"],
                local_path=media_url,
                provider=m.get("provider") or "local",
                model=m["model"],
                status=m.get("status") or "pending",
            )
        )

    platforms_val = [c.platform for c in contents] or ["linkedin"]

    return StudioCampaignDetail(
        id=str(c_row["id"]),
        brand_id=c_row["brand_id"],
        objective=c_row.get("objective") or "Awareness",
        language=c_row.get("language") or "en",
        thesis=c_row.get("thesis") or c_row.get("title") or "",
        target_audience=c_row.get("target_audience"),
        platforms=platforms_val,
        status=c_row.get("status") or "draft",
        error=None,
        created_at=c_row["created_at"],
        updated_at=c_row.get("updated_at"),
        contents=contents,
        media=media,
        image_prompt=img_prompt,
        video_prompt=vid_prompt,
    )


@router.post("/{campaign_id}/generate-image", response_model=CampaignMediaItem)
def generate_campaign_image(
    campaign_id: str,
    body: MediaGenerateRequest,
    x_demo_mode: str | None = Header(None, alias="X-Demo-Mode"),
) -> CampaignMediaItem:
    """Generate image and save locally to storage/campaigns/{campaign_id}/image/{filename}."""
    demo_mode = is_demo_mode(x_demo_mode)
    chosen_model = body.model or os.environ.get("IMAGE_MODEL", "google/nano-banana-2-lites")
    prompt = body.prompt

    # 1. Load campaign and image prompt from MySQL
    with get_db() as db:
        detail = campaign_repo.get_campaign_detail(db, campaign_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Campaign not found")

        if not prompt:
            for c in detail["contents"]:
                if c.get("image_generation_prompt"):
                    prompt = c["image_generation_prompt"]
                    break
        if not prompt:
            brand_title = detail["campaign"]["brand_id"].upper()
            thesis = detail["campaign"]["thesis"]
            prompt = (
                f'Commercial advertising poster with bold typography text overlay. '
                f'Large prominent headline text overlay across the top reads: "COME TO {brand_title} · {thesis[:32].upper()}". '
                f'Secondary sub-headline text overlay reads: "INSTITUTIONAL RISK PROTECTION · SINGAPORE". '
                f'High-contrast graphic design poster layout with legible typography text overlay.'
            )

    # 2. Record media generating in MySQL
    media_id = str(uuid4())
    with transaction() as db:
        media_repo.record_media_generating(
            db=db,
            campaign_id=campaign_id,
            media_type="image",
            prompt=prompt,
            model=chosen_model,
            provider="demo_local" if demo_mode else "fal",
            media_id=media_id,
        )

    # 3. Generate image and save to local storage
    try:
        res = service_generate_image(
            campaign_id=campaign_id,
            prompt=prompt,
            model=chosen_model,
            demo_mode=demo_mode,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Image generation failed: {exc}")

    # 4. Update media row with completed file info in MySQL
    with transaction() as db:
        updated_media = media_repo.update_media_completed(
            db=db,
            media_id=media_id,
            campaign_id=campaign_id,
            media_type="image",
            local_path=res["local_path"],
            filename=res["filename"],
            mime_type=res["mime_type"],
            file_size=res["file_size"],
        )

    media_url = f"/{res['local_path']}"
    return CampaignMediaItem(
        id=str(updated_media["id"]),
        campaign_id=str(updated_media["campaign_id"]),
        media_type="image",
        prompt=updated_media["prompt"],
        local_path=media_url,
        provider=updated_media["provider"],
        model=updated_media["model"],
        status=updated_media["status"],
    )


@router.post("/{campaign_id}/generate-video", response_model=CampaignMediaItem)
def generate_campaign_video(
    campaign_id: str,
    body: MediaGenerateRequest,
    x_demo_mode: str | None = Header(None, alias="X-Demo-Mode"),
) -> CampaignMediaItem:
    """Generate vertical Reel video and save locally to storage/campaigns/{campaign_id}/video/{filename}."""
    demo_mode = is_demo_mode(x_demo_mode)
    chosen_model = body.model or os.environ.get("VIDEO_MODEL", "minimax/h3-max-turbo/text-to-video")
    prompt = body.prompt

    # 1. Load campaign and video prompt from MySQL
    with get_db() as db:
        detail = campaign_repo.get_campaign_detail(db, campaign_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Campaign not found")

        if not prompt:
            for c in detail["contents"]:
                if c.get("video_generation_prompt"):
                    prompt = c["video_generation_prompt"]
                    break
        if not prompt:
            prompt = f"Vertical 9:16 cinematic video for {detail['campaign']['brand_id']} on {detail['campaign']['thesis']}"

    # 2. Record media generating in MySQL
    media_id = str(uuid4())
    with transaction() as db:
        media_repo.record_media_generating(
            db=db,
            campaign_id=campaign_id,
            media_type="video",
            prompt=prompt,
            model=chosen_model,
            provider="demo_local" if demo_mode else "fal",
            media_id=media_id,
        )

    # 3. Generate video and save to local storage
    try:
        res = service_generate_video(
            campaign_id=campaign_id,
            prompt=prompt,
            model=chosen_model,
            demo_mode=demo_mode,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Video generation failed: {exc}")

    # 4. Update media row with completed file info in MySQL
    with transaction() as db:
        updated_media = media_repo.update_media_completed(
            db=db,
            media_id=media_id,
            campaign_id=campaign_id,
            media_type="video",
            local_path=res["local_path"],
            filename=res["filename"],
            mime_type=res["mime_type"],
            file_size=res["file_size"],
            duration_seconds=res.get("duration_seconds", 5.0),
        )

    media_url = f"/{res['local_path']}"
    return CampaignMediaItem(
        id=str(updated_media["id"]),
        campaign_id=str(updated_media["campaign_id"]),
        media_type="video",
        prompt=updated_media["prompt"],
        local_path=media_url,
        provider=updated_media["provider"],
        model=updated_media["model"],
        status=updated_media["status"],
    )


@router.post("/{campaign_id}/submit-review")
def submit_campaign_review(campaign_id: str):
    """Transition campaign status from 'generated' to 'pending_review' and enqueue into review_queue."""
    try:
        with transaction() as db:
            result = campaign_repo.submit_for_verification(db, campaign_id)
        return result
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# --- Review Decision Endpoints ---


@router.get("/review-queue")
def get_campaign_review_queue(status: str | None = None):
    """Retrieve campaigns in the Review Queue."""
    with get_db() as db:
        return review_repo.get_review_queue(db, status=status)


@router.post("/{campaign_id}/approve")
def approve_campaign_route(campaign_id: str, body: ReviewApproveRequest = ReviewApproveRequest()):
    """Approve campaign in review queue."""
    with transaction() as db:
        return review_repo.approve_campaign(db, campaign_id, reviewer_note=body.reviewer_note)


@router.post("/{campaign_id}/reject")
def reject_campaign_route(campaign_id: str, body: ReviewRejectRequest):
    """Reject campaign in review queue and record lesson in MySQL."""
    with transaction() as db:
        return review_repo.reject_campaign(
            db, campaign_id, tag=body.tag, note=body.note, platform=body.platform
        )


@router.post("/{campaign_id}/edit")
def edit_campaign_content_route(campaign_id: str, body: ReviewEditRequest):
    """Edit platform content, preserve original, and record lesson if feedback provided."""
    with transaction() as db:
        return review_repo.edit_campaign_content(
            db,
            campaign_id=campaign_id,
            platform=body.platform,
            new_content=body.new_content,
            new_title=body.new_title,
            tag=body.tag,
            note=body.note,
        )


@router.get("/{campaign_id}/events")
def get_campaign_events(campaign_id: str):
    """Retrieve audit trail of events for this campaign."""
    with get_db() as db:
        return event_repo.list_events_for_campaign(db, campaign_id)


@router.get("/{campaign_id}", response_model=Campaign)
def get_campaign(campaign_id: str) -> Campaign:
    with get_db() as db:
        detail = campaign_repo.get_campaign_detail(db, campaign_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaign(detail["campaign"])
