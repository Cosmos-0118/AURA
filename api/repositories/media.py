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


def determine_next_media_path(campaign_id: str, media_type: str) -> tuple[Path, str, str]:
    """Determine the next safe versioned filename and relative path for image or video.

    Returns: (absolute_path, filename, relative_path)
    Example relative path: storage/campaigns/{id}/image/instagram-image.png
    """
    target_dir = ensure_media_dir(campaign_id, media_type)
    ext = ".png" if media_type == "image" else ".mp4"
    base_name = "instagram-image" if media_type == "image" else "reel-video"

    # Check for existing versions
    v = 1
    while True:
        suffix = "" if v == 1 else f"-v{v}"
        filename = f"{base_name}{suffix}{ext}"
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
) -> str:
    """Insert or initialize a media record in 'generating' status."""
    mid = media_id or str(uuid4())
    dummy_path = f"storage/campaigns/{campaign_id}/{media_type}/pending"

    db.execute(
        """
        INSERT INTO campaign_media
            (id, campaign_id, platform_content_id, media_type, provider, model, prompt, local_path, status)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s, 'generating')
        """,
        (mid, campaign_id, platform_content_id, media_type, provider, model, prompt, dummy_path),
    )

    log_event(
        db,
        campaign_id=campaign_id,
        event_type=f"{media_type}_generation_started",
        description=f"Started {media_type} generation using {model}",
        metadata={"media_id": mid, "provider": provider, "model": model},
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
            status = 'completed'
        WHERE id = %s
        """,
        (local_path, filename, mime_type, file_size, width, height, duration_seconds, media_id),
    )

    log_event(
        db,
        campaign_id=campaign_id,
        event_type=f"{media_type}_generation_completed",
        description=f"Saved {media_type} to {local_path} ({file_size} bytes)",
        metadata={"media_id": media_id, "local_path": local_path, "filename": filename, "file_size": file_size},
    )

    return get_media_by_id(db, media_id)


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
