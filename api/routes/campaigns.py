import json
import os
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, File, Form, Header, HTTPException, UploadFile
from pydantic import BaseModel

try:
    from ..db import get_db, reset_campaign_data, transaction
    from ..graph import run_pipeline
    from ..repositories import (
        campaigns as campaign_repo,
        events as event_repo,
        lessons as lesson_repo,
        media as media_repo,
        publications as publication_repo,
        reviews as review_repo,
    )
    from ..schemas import (
        AssistantChatRequest,
        AssistantChatResponse,
        BrandId,
        Campaign,
        CampaignCreate,
        CampaignEventItem,
        CampaignFacts,
        CampaignMediaItem,
        CampaignPlatformContentItem,
        CampaignPublicationItem,
        CampaignReviewCard,
        CampaignSubmitResult,
        CampaignWorkspaceHistory,
        HistoryCampaignSummary,
        MediaGenerateRequest,
        PublishResponse,
        ResubmitReviewRequest,
        ResubmitReviewResponse,
        StudioCampaignCreate,
        StudioCampaignDetail,
        WatermarkLogoItem,
    )
    from ..agents.compliance import check_compliance
    from ..services.content_generator import generate_campaign_content
    from ..services.image_generator import (
        apply_watermark_to_image,
        generate_image as service_generate_image,
    )
    from ..services.publisher import publish_campaign_platform
    from ..publishing import publish_to_platform
    from ..services.video_generator import (
        generate_video as service_generate_video,
        save_watermarked_video_bytes,
    )
except ImportError:
    from db import get_db, reset_campaign_data, transaction
    from graph import run_pipeline
    from repositories import (
        campaigns as campaign_repo,
        events as event_repo,
        lessons as lesson_repo,
        media as media_repo,
        publications as publication_repo,
        reviews as review_repo,
    )
    from schemas import (
        AssistantChatRequest,
        AssistantChatResponse,
        BrandId,
        Campaign,
        CampaignCreate,
        CampaignEventItem,
        CampaignFacts,
        CampaignMediaItem,
        CampaignPlatformContentItem,
        CampaignPublicationItem,
        CampaignReviewCard,
        CampaignSubmitResult,
        CampaignWorkspaceHistory,
        HistoryCampaignSummary,
        MediaGenerateRequest,
        PublishResponse,
        ResubmitReviewRequest,
        ResubmitReviewResponse,
        StudioCampaignCreate,
        StudioCampaignDetail,
        WatermarkLogoItem,
    )
    from agents.compliance import check_compliance
    from services.content_generator import generate_campaign_content
    from services.image_generator import (
        apply_watermark_to_image,
        generate_image as service_generate_image,
    )
    from services.publisher import publish_campaign_platform
    from publishing import publish_to_platform
    from services.video_generator import (
        generate_video as service_generate_video,
        save_watermarked_video_bytes,
    )

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


class ApplyWatermarkRequest(BaseModel):
    media_type: str = "image"  # "image" | "video"
    parent_media_id: str | None = None
    logo_preset: str | None = None
    logo_anchor: str = "bottom-right"
    logo_scale: float = 80.0
    logo_opacity: float = 90.0
    custom_text: str | None = None
    image_data: str | None = None
    logos: list[WatermarkLogoItem] = []
    watermark_config: dict[str, Any] | None = None



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

    # Step 2: Run generation within try-except to ensure CORS headers and clear errors
    try:
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
                platforms=body.platforms,
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
        model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
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
    except Exception as exc:
        logger.error(f"Campaign studio generation failed: {exc}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Campaign content generation failed: {exc}")

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
                media_stage=m.get("media_stage") or "final",
                watermarked=bool(m.get("watermarked")),
                logo_path=m.get("logo_path"),
                logo_position=m.get("logo_position"),
                logo_scale=m.get("logo_scale"),
                logo_opacity=m.get("logo_opacity"),
                parent_media_id=str(m["parent_media_id"]) if m.get("parent_media_id") else None,
            )
        )

    platforms_val = [c.platform for c in contents] or ["linkedin"]

    raw_facts = c_row.get("campaign_facts")
    facts_obj = None
    if isinstance(raw_facts, str):
        try:
            facts_data = json.loads(raw_facts)
            if isinstance(facts_data, dict):
                facts_obj = CampaignFacts(**facts_data)
        except Exception:
            pass
    elif isinstance(raw_facts, dict):
        facts_obj = CampaignFacts(**raw_facts)

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
        campaign_facts=facts_obj,
    )


@router.post("/{campaign_id}/generate-image", response_model=CampaignMediaItem)
def generate_campaign_image(
    campaign_id: str,
    body: MediaGenerateRequest,
    x_demo_mode: str | None = Header(None, alias="X-Demo-Mode"),
) -> CampaignMediaItem:
    """Generate original 1:1 square image and save locally to storage/campaigns/{campaign_id}/image/{filename}."""
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
            brand_id = detail["campaign"]["brand_id"]
            brand_title = brand_id.upper()
            thesis = detail["campaign"]["thesis"]
            raw_facts = detail["campaign"].get("campaign_facts")
            facts_dict = {}
            if isinstance(raw_facts, str):
                try:
                    facts_dict = json.loads(raw_facts)
                except Exception:
                    pass
            elif isinstance(raw_facts, dict):
                facts_dict = raw_facts

            event_title = facts_dict.get("event_name") or f"COME TO {brand_title} · {thesis[:32].upper()}"
            event_date = facts_dict.get("date") or "OCTOBER 2026"
            event_loc = facts_dict.get("location") or "SINGAPORE"
            prompt = (
                f'Commercial advertising poster with bold typography text overlay. '
                f'Large prominent headline text overlay across the top reads: "{event_title.upper()}". '
                f'Secondary sub-headline text overlay reads: "{event_date.upper()} · {event_loc.upper()}". '
                f'High-contrast graphic design poster layout with legible typography text overlay.'
            )

    # 2. Record media generating in MySQL (original stage)
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
            media_stage="original",
        )

    # 3. Generate image and save to local storage
    try:
        res = service_generate_image(
            campaign_id=campaign_id,
            prompt=prompt,
            model=chosen_model,
            demo_mode=demo_mode,
            brand_id=detail["campaign"]["brand_id"],
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
            media_stage="original",
            watermarked=False,
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
        media_stage="original",
        watermarked=False,
    )


@router.post("/{campaign_id}/generate-video", response_model=CampaignMediaItem)
def generate_campaign_video(
    campaign_id: str,
    body: MediaGenerateRequest,
    x_demo_mode: str | None = Header(None, alias="X-Demo-Mode"),
) -> CampaignMediaItem:
    """Generate original vertical 9:16 Reel video and save locally to storage/campaigns/{campaign_id}/video/{filename}."""
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

    # 2. Record media generating in MySQL (original stage)
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
            media_stage="original",
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
            media_stage="original",
            watermarked=False,
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
        media_stage="original",
        watermarked=False,
    )


@router.post("/{campaign_id}/apply-watermark", response_model=CampaignMediaItem)
def apply_campaign_watermark(campaign_id: str, body: ApplyWatermarkRequest) -> CampaignMediaItem:
    """Apply brand logo and text overlay to create final watermarked asset."""
    with get_db() as db:
        detail = campaign_repo.get_campaign_detail(db, campaign_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Campaign not found")

        # Find parent media
        parent = None
        if body.parent_media_id:
            parent = media_repo.get_media_by_id(db, body.parent_media_id)
        if not parent:
            for m in reversed(detail["media"]):
                if m["media_type"] == body.media_type:
                    parent = m
                    break

        if not parent:
            raise HTTPException(status_code=400, detail=f"No {body.media_type} asset found to watermark")

    # Build logos payload and watermark config
    logos_payload = [l.model_dump() for l in body.logos] if body.logos else []
    if not logos_payload and body.logo_preset:
        logos_payload = [{
            "logo_path": body.logo_preset,
            "anchor": body.logo_anchor,
            "scale": body.logo_scale,
            "opacity": body.logo_opacity,
        }]

    config_dict = body.watermark_config or {
        "logos": logos_payload,
        "custom_text": body.custom_text,
        "primary_anchor": body.logo_anchor,
        "primary_scale": body.logo_scale,
        "primary_opacity": body.logo_opacity,
    }

    # Apply watermark to image
    if body.media_type == "image":
        res = apply_watermark_to_image(
            campaign_id=campaign_id,
            original_media_path=parent["local_path"],
            brand_id=body.logo_preset or detail["campaign"]["brand_id"],
            logo_anchor=body.logo_anchor,
            logo_scale=body.logo_scale,
            logo_opacity=body.logo_opacity,
            custom_text=body.custom_text,
            image_data_base64=body.image_data,
            logos=logos_payload,
        )
    else:
        raise HTTPException(
            status_code=400,
            detail="For video watermarking, export the composited video and upload via upload-watermarked-media",
        )

    with transaction() as db:
        saved = media_repo.record_watermarked_media(
            db=db,
            campaign_id=campaign_id,
            media_type="image",
            prompt=parent["prompt"],
            local_path=res["local_path"],
            filename=res["filename"],
            mime_type=res["mime_type"],
            file_size=res["file_size"],
            parent_media_id=str(parent["id"]),
            logo_path=body.logo_preset or (logos_payload[0].get("logo_path") if logos_payload else None) or "/logo/ja.png",
            logo_position=body.logo_anchor,
            logo_scale=body.logo_scale,
            logo_opacity=body.logo_opacity,
            watermark_config=json.dumps(config_dict),
        )

    media_url = f"/{saved['local_path']}" if not saved['local_path'].startswith('/') else saved['local_path']
    return CampaignMediaItem(
        id=str(saved["id"]),
        campaign_id=str(saved["campaign_id"]),
        media_type="image",
        prompt=saved["prompt"],
        local_path=media_url,
        provider=saved.get("provider") or "local",
        model=saved["model"],
        status="completed",
        media_stage="final",
        watermarked=True,
        logo_path=saved.get("logo_path"),
        logo_position=body.logo_anchor,
        logo_scale=body.logo_scale,
        logo_opacity=body.logo_opacity,
        parent_media_id=str(parent["id"]),
        watermark_config=config_dict,
    )


@router.post("/{campaign_id}/upload-watermarked-media", response_model=CampaignMediaItem)
async def upload_watermarked_media(
    campaign_id: str,
    file: UploadFile = File(...),
    media_type: str = Form("video"),
    parent_media_id: str | None = Form(None),
    logo_anchor: str = Form("bottom-right"),
    logo_scale: float = Form(80.0),
    logo_opacity: float = Form(90.0),
    watermark_config: str | None = Form(None),
) -> CampaignMediaItem:
    """Save user-exported watermarked video or image file as the final version."""
    content_bytes = await file.read()
    ext = os.path.splitext(file.filename or "")[1] or (".mp4" if media_type == "video" else ".png")

    with get_db() as db:
        detail = campaign_repo.get_campaign_detail(db, campaign_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Campaign not found")

        parent = None
        if parent_media_id:
            parent = media_repo.get_media_by_id(db, parent_media_id)
        if not parent:
            for m in reversed(detail["media"]):
                if m["media_type"] == media_type:
                    parent = m
                    break

        prompt = parent["prompt"] if parent else f"Watermarked {media_type} asset"
        parent_id_str = str(parent["id"]) if parent else None

    if media_type == "video":
        res = save_watermarked_video_bytes(
            campaign_id=campaign_id,
            raw_video_bytes=content_bytes,
            extension=ext,
        )
    else:
        target_path, filename, rel_path = media_repo.determine_next_media_path(
            campaign_id, "image", stage="final"
        )
        with open(target_path, "wb") as f:
            f.write(content_bytes)
        res = {
            "local_path": rel_path,
            "filename": filename,
            "mime_type": file.content_type or "image/png",
            "file_size": len(content_bytes),
        }

    config_dict = None
    if watermark_config:
        try:
            config_dict = json.loads(watermark_config)
        except Exception:
            config_dict = {"raw": watermark_config}

    with transaction() as db:
        saved = media_repo.record_watermarked_media(
            db=db,
            campaign_id=campaign_id,
            media_type=media_type,
            prompt=prompt,
            local_path=res["local_path"],
            filename=res["filename"],
            mime_type=res["mime_type"],
            file_size=res["file_size"],
            parent_media_id=parent_id_str,
            logo_position=logo_anchor,
            logo_scale=logo_scale,
            logo_opacity=logo_opacity,
            watermark_config=watermark_config,
        )

    media_url = f"/{saved['local_path']}" if not saved['local_path'].startswith('/') else saved['local_path']
    return CampaignMediaItem(
        id=str(saved["id"]),
        campaign_id=str(saved["campaign_id"]),
        media_type=media_type,
        prompt=saved["prompt"],
        local_path=media_url,
        provider=saved.get("provider") or "local",
        model=saved["model"],
        status="completed",
        media_stage="final",
        watermarked=True,
        logo_position=logo_anchor,
        logo_scale=logo_scale,
        logo_opacity=logo_opacity,
        parent_media_id=parent_id_str,
        watermark_config=config_dict,
    )



@router.post("/{campaign_id}/submit", response_model=CampaignSubmitResult)
@router.post("/{campaign_id}/submit-review", response_model=CampaignSubmitResult)
def submit_campaign_review(campaign_id: str) -> CampaignSubmitResult:
    """Transition campaign status from 'generated' to 'pending_review' and enqueue into review_queue."""
    try:
        with transaction() as db:
            result = campaign_repo.submit_for_verification(db, campaign_id)
        return CampaignSubmitResult(**result)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# --- Review Decision Endpoints ---


@router.get("/review-queue", response_model=list[CampaignReviewCard])
def get_campaign_review_queue(status: str | None = None) -> list[CampaignReviewCard]:
    """Retrieve unified campaign review cards for Review Queue."""
    with get_db() as db:
        items = review_repo.get_review_queue(db, status=status)
    return [CampaignReviewCard(**it) for it in items]


@router.post("/{campaign_id}/approve")
def approve_campaign_route(campaign_id: str, body: ReviewApproveRequest | None = None):
    """Approve campaign in review queue, unlocking multi-platform publishing."""
    reviewer_note = body.reviewer_note if body else None
    with transaction() as db:
        return review_repo.approve_campaign(db, campaign_id, reviewer_note=reviewer_note)


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


@router.post("/{campaign_id}/publish/linkedin", response_model=PublishResponse)
def publish_campaign_linkedin_route(campaign_id: str) -> PublishResponse:
    """Publish approved campaign asset to LinkedIn via Buffer."""
    try:
        with transaction() as db:
            res = publish_to_platform(db, campaign_id, "linkedin")
        return PublishResponse(**res)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{campaign_id}/publish/instagram", response_model=PublishResponse)
def publish_campaign_instagram_route(campaign_id: str) -> PublishResponse:
    """Publish approved campaign asset to Instagram via Buffer."""
    try:
        with transaction() as db:
            res = publish_to_platform(db, campaign_id, "instagram")
        return PublishResponse(**res)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{campaign_id}/publish/x", response_model=PublishResponse)
def publish_campaign_x_route(campaign_id: str) -> PublishResponse:
    """Publish approved campaign asset to X via Buffer."""
    try:
        with transaction() as db:
            res = publish_to_platform(db, campaign_id, "x")
        return PublishResponse(**res)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{campaign_id}/publish/{platform}", response_model=PublishResponse)
def publish_campaign_platform_route(campaign_id: str, platform: str) -> PublishResponse:
    """Publish approved campaign asset to specific platform (e.g. linkedin, instagram, x) via Buffer."""
    try:
        with transaction() as db:
            res = publish_to_platform(db, campaign_id, platform)
        return PublishResponse(**res)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{campaign_id}/publications", response_model=list[CampaignPublicationItem])
def get_campaign_publications_route(campaign_id: str) -> list[CampaignPublicationItem]:
    """Get publishing status for all platforms for a given campaign."""
    with get_db() as db:
        rows = publication_repo.get_campaign_publications(db, campaign_id)
    return [
        CampaignPublicationItem(
            id=str(r["id"]),
            campaign_id=str(r["campaign_id"]),
            platform=r["platform"],
            status=r["status"],
            external_post_id=r.get("external_post_id"),
            external_post_url=r.get("external_post_url"),
            published_content=r.get("published_content"),
            media_id=str(r["media_id"]) if r.get("media_id") else None,
            error_message=r.get("error_message"),
            published_at=r.get("published_at"),
            created_at=r.get("created_at"),
        )
        for r in rows
    ]


@router.get("/{campaign_id}/history", response_model=list[CampaignEventItem])
def get_campaign_history_route(campaign_id: str) -> list[CampaignEventItem]:
    """Retrieve full chronological audit trail of events for this campaign."""
    with get_db() as db:
        rows = event_repo.list_events_for_campaign(db, campaign_id)
    items = []
    for r in rows:
        meta = r.get("metadata")
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {"raw": meta}
        items.append(
            CampaignEventItem(
                id=str(r["id"]),
                campaign_id=str(r["campaign_id"]),
                event_type=r["event_type"],
                actor=r.get("actor", "system"),
                description=r.get("description"),
                metadata=meta,
                created_at=r["created_at"],
            )
        )
    return items


@router.get("/{campaign_id}/media", response_model=list[CampaignMediaItem])
def get_campaign_media_route(campaign_id: str) -> list[CampaignMediaItem]:
    """Retrieve complete versioned media history (v1, v2, v3...) for this campaign."""
    with get_db() as db:
        rows = media_repo.get_media_for_campaign(db, campaign_id)
    items = []
    for m in rows:
        lp = m.get("local_path")
        m_url = f"/{lp}" if lp and not lp.startswith("/") else lp
        items.append(
            CampaignMediaItem(
                id=str(m["id"]),
                campaign_id=str(m["campaign_id"]),
                media_type=m["media_type"],
                prompt=m["prompt"],
                local_path=m_url,
                provider=m.get("provider") or "local",
                model=m["model"],
                status=m.get("status") or "completed",
                media_stage=m.get("media_stage") or "final",
                watermarked=bool(m.get("watermarked")),
                logo_path=m.get("logo_path"),
                logo_position=m.get("logo_position"),
                logo_scale=m.get("logo_scale"),
                logo_opacity=m.get("logo_opacity"),
                parent_media_id=str(m["parent_media_id"]) if m.get("parent_media_id") else None,
            )
        )
    return items


@router.post("/reset-data")
def reset_campaign_data_route():
    """Delete all test campaign data, media files, publications, and events for a fresh start."""
    import shutil
    from pathlib import Path

    if os.environ.get("AURA_ALLOW_RESET_DATA", "false").lower() not in {"1", "true", "yes", "on"}:
        raise HTTPException(status_code=403, detail="Reset is disabled unless AURA_ALLOW_RESET_DATA is enabled.")

    with transaction() as db:
        counts = reset_campaign_data(db)

    # Clean local media storage
    storage_camp = Path(__file__).resolve().parent.parent.parent / "storage" / "campaigns"
    if storage_camp.exists():
        shutil.rmtree(storage_camp, ignore_errors=True)
        storage_camp.mkdir(parents=True, exist_ok=True)

    return {"success": True, "message": "All test campaigns and media files wiped clean.", "deleted": counts}


@router.get("/history-list", response_model=list[HistoryCampaignSummary])
def get_campaigns_history_list() -> list[HistoryCampaignSummary]:
    """List all campaigns formatted for History Archive with review cycles and media status."""
    with get_db() as db:
        items = campaign_repo.list_campaign_history_summaries(db)
    return [HistoryCampaignSummary(**it) for it in items]


@router.get("/{campaign_id}/workspace-history", response_model=CampaignWorkspaceHistory)
def get_campaign_workspace_history_route(campaign_id: str) -> CampaignWorkspaceHistory:
    """Fetch complete historical detail for campaign workspace: all versions of content, media, review cycles, and audit events."""
    try:
        with get_db() as db:
            data = campaign_repo.get_campaign_workspace_history(db, campaign_id)
        return CampaignWorkspaceHistory(**data)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch workspace history: {exc}")


@router.post("/{campaign_id}/resubmit", response_model=ResubmitReviewResponse)
def resubmit_campaign_review_route(
    campaign_id: str, body: ResubmitReviewRequest | None = None
) -> ResubmitReviewResponse:
    """Resubmit campaign to review queue, creating a new review cycle."""
    note = body.note if body else None
    try:
        with transaction() as db:
            res = campaign_repo.resubmit_campaign_for_review(db, campaign_id, note=note)
        return ResubmitReviewResponse(**res)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/{campaign_id}/chat", response_model=AssistantChatResponse)
def assistant_chat_route(campaign_id: str, body: AssistantChatRequest) -> AssistantChatResponse:
    """AURA Assistant contextual regeneration chat for History Workspace.
    Regenerates platform content copy, image/video prompts, or media.
    Evaluates compliance on regenerated copy.
    Never auto-publishes.
    """
    with get_db() as db:
        detail = campaign_repo.get_campaign_detail(db, campaign_id)
        if not detail:
            raise HTTPException(status_code=404, detail="Campaign not found")

    camp = detail["campaign"]
    brand_id = camp["brand_id"]
    current_contents = [c for c in detail["contents"] if c.get("is_current", 1)]
    if not current_contents:
        current_contents = detail["contents"]

    # Determine targeted platform(s)
    target_platform = body.target_platform
    platforms_to_update = []
    if target_platform and target_platform != "all":
        platforms_to_update = [target_platform]
    else:
        # Check if user message explicitly mentions any platform
        msg_lower = body.message.lower()
        for p in ["linkedin", "instagram", "x", "blog", "reel"]:
            if p in msg_lower:
                platforms_to_update.append(p)
        if not platforms_to_update:
            platforms_to_update = [c["platform"] for c in current_contents] or ["linkedin"]

    # Groq OpenAI or local generation
    api_key = os.environ.get("GROQ_API_KEY")
    regenerated_payload = None
    reply_text = ""

    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
            groq_model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

            context_str = f"Campaign Title: {camp.get('title')}\nThesis: {camp.get('thesis')}\nBrand: {brand_id}\nObjective: {camp.get('objective')}\nTarget Audience: {camp.get('target_audience')}\n\nCurrent Contents:\n"
            for c in current_contents:
                context_str += f"- Platform: {c['platform']}\n  Title: {c.get('title')}\n  Content: {c.get('content')}\n"

            sys_prompt = f"""You are AURA Assistant, an expert AI compliance and marketing campaign specialist for JA Assure ({brand_id}).
The user wants to revise or regenerate parts of this existing marketing campaign.
User instructions: "{body.message}"
Target Platforms to update: {', '.join(platforms_to_update)}

COMPLIANCE RULES:
- Never guarantee absolute risk-free protection, foolproof security, or 100% loss prevention.
- Always maintain regulatory compliance for insurance and professional indemnity.

OUTPUT FORMAT:
Respond with a strict JSON object with:
{{
  "reply": "Clear, professional explanation of the changes made and compliance rationale.",
  "platforms": {{
    "<platform_name>": {{
      "title": "optional updated headline",
      "content": "updated platform body copy",
      "hashtags": ["#tag1", "#tag2"],
      "script": "optional script for reels",
      "visual_concept": "optional visual concept",
      "generation_prompt": "updated image/video prompt if requested"
    }}
  }},
  "image_generation_prompt": "updated visual poster prompt if applicable",
  "video_generation_prompt": "updated video prompt if applicable"
}}"""

            resp = client.chat.completions.create(
                model=groq_model,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": f"Context:\n{context_str}\n\nInstruction: {body.message}"},
                ],
                temperature=0.7,
                response_format={"type": "json_object"},
            )
            regenerated_payload = json.loads(resp.choices[0].message.content or "{}")
            reply_text = regenerated_payload.get("reply", "Updated campaign content per your instructions.")
        except Exception:
            pass

    if not regenerated_payload:
        reply_text = f"Updated campaign copy for {', '.join(platforms_to_update)} based on your request: \"{body.message}\"."
        regenerated_payload = {"platforms": {}}
        for p in platforms_to_update:
            existing_c = next((c for c in current_contents if c["platform"] == p), None)
            base_content = existing_c["content"] if existing_c else camp.get("thesis", "Marketing update")
            regenerated_payload["platforms"][p] = {
                "title": (existing_c.get("title") or "Revised Campaign Update") if existing_c else "Revised Update",
                "content": f"{base_content}\n\n[Revised: {body.message}]",
                "hashtags": existing_c.get("hashtags", ["#AURA", f"#{brand_id.title()}"]) if existing_c else ["#AURA"],
                "generation_prompt": existing_c.get("image_generation_prompt") if existing_c else None,
            }

    # Save regenerated content versions & run compliance
    updated_items = []
    compliance_results = {}

    with transaction() as db:
        for p, data in regenerated_payload.get("platforms", {}).items():
            if not isinstance(data, dict):
                continue
            content = data.get("content", "")
            title = data.get("title")
            hashtags = data.get("hashtags", [])
            script = data.get("script")
            visual_concept = data.get("visual_concept")
            gen_prompt = data.get("generation_prompt") or regenerated_payload.get("image_generation_prompt")

            # Run deterministic compliance
            c_check = check_compliance(f"{title or ''} {content}", brand_id, p)
            compliance_results[p] = {
                "result": c_check.result,
                "risk": c_check.risk,
                "issues": [i.model_dump() for i in c_check.issues],
                "suggested_revision": c_check.suggested_revision,
            }

            saved = campaign_repo.save_assistant_regenerated_content(
                db=db,
                campaign_id=campaign_id,
                platform=p,
                content=content,
                title=title,
                hashtags=hashtags,
                script=script,
                visual_concept=visual_concept,
                generation_prompt=gen_prompt,
            )
            updated_items.append(CampaignPlatformContentItem(**saved))

    # Media regeneration if requested
    new_media_item = None
    if body.regenerate_media:
        media_prompt = (
            regenerated_payload.get(f"{body.media_type}_generation_prompt")
            or regenerated_payload.get("image_generation_prompt")
            or f"Revised visual asset for {brand_id} - {camp.get('thesis')}"
        )
        if body.media_type == "image":
            img_model = os.environ.get("IMAGE_MODEL", "google/nano-banana-2-lites")
            media_id = str(uuid4())
            with transaction() as db:
                media_repo.record_media_generating(
                    db=db,
                    campaign_id=campaign_id,
                    media_type="image",
                    prompt=media_prompt,
                    model=img_model,
                    provider="demo_local" if is_demo_mode() else "fal",
                    media_id=media_id,
                    media_stage="original",
                )
            gen_res = service_generate_image(
                campaign_id=campaign_id,
                prompt=media_prompt,
                brand_id=brand_id,
                demo_mode=is_demo_mode(),
            )
            with transaction() as db:
                saved_media = media_repo.update_media_completed(
                    db=db,
                    media_id=media_id,
                    campaign_id=campaign_id,
                    media_type="image",
                    local_path=gen_res["local_path"],
                    filename=gen_res["filename"],
                    mime_type=gen_res["mime_type"],
                    file_size=gen_res["file_size"],
                    media_stage="original",
                    watermarked=False,
                )
            new_media_item = CampaignMediaItem(
                id=str(saved_media["id"]),
                campaign_id=campaign_id,
                media_type="image",
                prompt=media_prompt,
                local_path=f"/{gen_res['local_path']}",
                model=img_model,
                status="completed",
                media_stage="original",
                watermarked=False,
            )
        elif body.media_type == "video":
            vid_model = os.environ.get("VIDEO_MODEL", "minimax/h3-max-turbo/text-to-video")
            media_id = str(uuid4())
            with transaction() as db:
                media_repo.record_media_generating(
                    db=db,
                    campaign_id=campaign_id,
                    media_type="video",
                    prompt=media_prompt,
                    model=vid_model,
                    provider="demo_local" if is_demo_mode() else "fal",
                    media_id=media_id,
                    media_stage="original",
                )
            gen_res = service_generate_video(
                campaign_id=campaign_id,
                prompt=media_prompt,
                demo_mode=is_demo_mode(),
            )
            with transaction() as db:
                saved_media = media_repo.update_media_completed(
                    db=db,
                    media_id=media_id,
                    campaign_id=campaign_id,
                    media_type="video",
                    local_path=gen_res["local_path"],
                    filename=gen_res["filename"],
                    mime_type=gen_res["mime_type"],
                    file_size=gen_res["file_size"],
                    duration_seconds=gen_res.get("duration_seconds", 5.0),
                    media_stage="original",
                    watermarked=False,
                )
            new_media_item = CampaignMediaItem(
                id=str(saved_media["id"]),
                campaign_id=campaign_id,
                media_type="video",
                prompt=media_prompt,
                local_path=f"/{gen_res['local_path']}",
                model=vid_model,
                status="completed",
                media_stage="original",
                watermarked=False,
            )

    return AssistantChatResponse(
        reply=reply_text,
        campaign_id=campaign_id,
        regenerated_platforms=list(regenerated_payload.get("platforms", {}).keys()),
        compliance_results=compliance_results,
        new_media=new_media_item,
        updated_contents=updated_items,
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

