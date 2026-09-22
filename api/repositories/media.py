"""Campaign Media Repository and local filesystem helper."""

import os
from pathlib import Path
from typing import Any
from uuid import uuid4

try:
    from .events import log_event
except ImportError:
    from repositories.events import log_event

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STORAGE_BASE = PROJECT_ROOT / "storage"


def ensure_media_dir(campaign_id: str, media_type: str) -> Path:
    """Ensure directory storage/campaigns/{campaign_id}/{media_type}/ exists."""
    target_dir = STORAGE_BASE / "campaigns" / campaign_id / media_type
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def determine_next_media_path(
    campaign_id: str,
    media_type: str,
    stage: str = "original"
) -> tuple[Path, str, str]:
    """Determine the next safe versioned filename and relative path for image or video.

    Returns: (absolute_path, filename, relative_path)
    Example: storage/campaigns/{id}/image/poster_original_v1.png
             storage/campaigns/{id}/image/poster_final_v1.png
    """
    target_dir = ensure_media_dir(campaign_id, media_type)
    ext = ".png" if media_type == "image" else ".mp4"
    base_name = "poster" if media_type == "image" else "reel"

    v = 1
    while True:
        filename = f"{base_name}_{stage}_v{v}{ext}"
        candidate_path = target_dir / filename
        if not candidate_path.exists():
            break
        v += 1

    rel_path = f"storage/campaigns/{campaign_id}/{media_type}/{filename}"
    return candidate_path, filename, rel_path


def record_media_generating(
    db: Any,
    campaign_id: str,
    media_type: str,
    prompt: str,
    model: str,
    provider: str = "local",
    platform_content_id: str | None = None,
    media_id: str | None = None,
    media_stage: str = "original",
) -> str:
    """Insert or initialize a media record in 'generating' status."""
    mid = media_id or str(uuid4())
    dummy_path = f"storage/campaigns/{campaign_id}/{media_type}/pending"

    db.execute(
        """
        INSERT INTO campaign_media
            (id, campaign_id, platform_content_id, media_type, provider, model, prompt, local_path, status, media_stage, watermarked)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, 'generating', %s, 0)
        """,
        (mid, campaign_id, platform_content_id, media_type, provider, model, prompt, dummy_path, media_stage),
    )

    log_event(
        db,
        campaign_id=campaign_id,
        event_type=f"{media_type}_generation_started",
        description=f"Started {media_type} generation ({media_stage}) using {model}",
        metadata={"media_id": mid, "provider": provider, "model": model, "stage": media_stage},
    )
    return mid


def update_media_completed(
    db: Any,
    media_id: str,
    campaign_id: str,
    media_type: str,
    local_path: str,
    filename: str,
    mime_type: str,
    file_size: int,
    width: int | None = None,
    height: int | None = None,
    duration_seconds: float | None = None,
    media_stage: str = "original",
    watermarked: bool = False,
    logo_path: str | None = None,
    logo_position: str | None = None,
    logo_scale: float = 100.0,
    logo_opacity: float = 100.0,
    parent_media_id: str | None = None,
) -> dict[str, Any]:
    """Update a media record on successful file generation and storage."""
    db.execute(
        """
        UPDATE campaign_media
        SET
            local_path = %s,
            filename = %s,
            mime_type = %s,
            file_size = %s,
            width = %s,
            height = %s,
            duration_seconds = %s,
            status = 'completed',
            media_stage = %s,
            watermarked = %s,
            logo_path = %s,
            logo_position = %s,
            logo_scale = %s,
            logo_opacity = %s,
            parent_media_id = %s
        WHERE id = %s
        """,
        (
            local_path,
            filename,
            mime_type,
            file_size,
            width,
            height,
            duration_seconds,
            media_stage,
            1 if watermarked else 0,
            logo_path,
            logo_position,
            logo_scale,
            logo_opacity,
            parent_media_id,
            media_id,
        ),
    )

    event_type = f"{media_type}_watermark_applied" if watermarked else f"{media_type}_generation_completed"
    desc = (
        f"Applied watermark and saved final {media_type} to {local_path} ({file_size} bytes)"
        if watermarked
        else f"Saved {media_type} to {local_path} ({file_size} bytes)"
    )

    log_event(
        db,
        campaign_id=campaign_id,
        event_type=event_type,
        description=desc,
        metadata={
            "media_id": media_id,
            "local_path": local_path,
            "filename": filename,
            "file_size": file_size,
            "stage": media_stage,
            "watermarked": watermarked,
            "parent_media_id": parent_media_id,
        },
    )

    return get_media_by_id(db, media_id)


def record_watermarked_media(
    db: Any,
    campaign_id: str,
    media_type: str,
    prompt: str,
    local_path: str,
    filename: str,
    mime_type: str,
    file_size: int,
    parent_media_id: str | None = None,
    logo_path: str | None = None,
    logo_position: str | None = None,
    logo_scale: float = 100.0,
    logo_opacity: float = 100.0,
    model: str = "watermark-composer",
    provider: str = "local_composer",
) -> dict[str, Any]:
    """Insert a final watermarked media record linked to its original parent."""
    mid = str(uuid4())
    db.execute(
        """
        INSERT INTO campaign_media
            (id, campaign_id, media_type, provider, model, prompt, local_path, filename, mime_type, file_size, status, media_stage, watermarked, logo_path, logo_position, logo_scale, logo_opacity, parent_media_id)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'completed', 'final', 1, %s, %s, %s, %s, %s)
        """,
        (
            mid,
            campaign_id,
            media_type,
            provider,
            model,
            prompt,
            local_path,
            filename,
            mime_type,
            file_size,
            logo_path,
            logo_position,
            logo_scale,
            logo_opacity,
            parent_media_id,
        ),
    )

    log_event(
        db,
        campaign_id=campaign_id,
        event_type=f"{media_type}_watermark_applied",
        description=f"Applied brand watermark: created final {media_type} asset {filename}",
        metadata={
            "media_id": mid,
            "parent_media_id": parent_media_id,
            "local_path": local_path,
            "filename": filename,
            "stage": "final",
            "logo_position": logo_position,
            "logo_scale": logo_scale,
        },
    )

    return get_media_by_id(db, mid)


def get_media_by_id(db: Any, media_id: str) -> dict[str, Any] | None:
    """Retrieve media item by ID."""
    return db.execute("SELECT * FROM campaign_media WHERE id = %s", (media_id,)).fetchone()


def get_media_for_campaign(
    db: Any, campaign_id: str, media_type: str | None = None
) -> list[dict[str, Any]]:
    """Retrieve all media records for a campaign."""
    query = "SELECT * FROM campaign_media WHERE campaign_id = %s"
    params = [campaign_id]
    if media_type:
        query += " AND media_type = %s"
        params.append(media_type)
    query += " ORDER BY created_at ASC"
    return db.execute(query, tuple(params)).fetchall()
