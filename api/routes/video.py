"""Video generation and attachment routes for AURA."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any
import uuid

from fastapi import APIRouter, HTTPException, Query

try:
    from ..agents.video import generate_video
    from ..db import get_connection
    from ..rules.insurance_compliance import check_compliance
    from ..schemas import (
        VideoAttachRequest,
        VideoGenerateRequest,
        VideoGenerateResponse,
        VideoGenerationRecord,
        VideoSaveExportRequest,
    )
except ImportError:  # Supports `cd api && uv run uvicorn main:app`.
    from agents.video import generate_video  # type: ignore[no-redef]
    from db import get_connection  # type: ignore[no-redef]
    from rules.insurance_compliance import check_compliance  # type: ignore[no-redef]
    from schemas import (  # type: ignore[no-redef]
        VideoAttachRequest,
        VideoGenerateRequest,
        VideoGenerateResponse,
        VideoGenerationRecord,
        VideoSaveExportRequest,
    )

logger = logging.getLogger("aura.video")
router = APIRouter(prefix="/api/video", tags=["video"])

_INSERT_GENERATION = """
insert into video_generations
  (brand_id, asset_id, prompt, aspect_ratio, resolution, duration_secs,
   model, video_url, file_name, file_size, branded_video_url, branded_file_name,
   status, error_msg, request_id, id)
values
  (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

_MODEL = "minimax/h3-max-turbo/text-to-video"

# In-memory store to guarantee zero data-loss when running in mock mode or when DB is offline
_MEMORY_HISTORY: list[VideoGenerationRecord] = []


def _is_valid_uuid(val: str | None) -> bool:
    if not val:
        return False
    try:
        uuid.UUID(str(val))
        return True
    except (ValueError, AttributeError):
        return False


def _persist_generation(
    body: VideoGenerateRequest,
    response: VideoGenerateResponse,
) -> str:
    """Insert into video_generations (or memory fallback). Returns record ID."""
    rec_id = response.request_id or str(uuid.uuid4())
    db_record_id = rec_id if _is_valid_uuid(rec_id) else str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    # Safe asset_id: only pass to Postgres if it's a valid UUID
    safe_asset_id = body.asset_id if _is_valid_uuid(body.asset_id) else None

    # Safe brand_id: use explicit brand_id if provided
    safe_brand_id = body.brand_id or None

    # 1. Update in-memory fallback list
    memory_record = VideoGenerationRecord(
        id=db_record_id,
        brand_id=safe_brand_id,
        asset_id=safe_asset_id,
        prompt=body.prompt,
        aspect_ratio=body.aspect_ratio,
        resolution=body.resolution,
        duration_secs=body.duration,
        model=_MODEL,
        video_url=response.video.url if response.video else None,
        file_name=response.video.file_name if response.video else None,
        file_size=response.video.file_size if response.video else None,
        branded_video_url=None,
        branded_file_name=None,
        status=response.status,
        error_msg=response.error or None,
        request_id=response.request_id or None,
        created_at=now,
    )
    # Prepend newest
    _MEMORY_HISTORY.insert(0, memory_record)
    if len(_MEMORY_HISTORY) > 100:
        _MEMORY_HISTORY.pop()

    # 2. Persist to PostgreSQL if available
    try:
        with get_connection() as connection:
            connection.execute(
                _INSERT_GENERATION,
                (
                    safe_brand_id,
                    safe_asset_id,
                    body.prompt,
                    body.aspect_ratio,
                    body.resolution,
                    body.duration,
                    _MODEL,
                    response.video.url if response.video else None,
                    response.video.file_name if response.video else None,
                    response.video.file_size if response.video else None,
                    None,  # branded_video_url
                    None,  # branded_file_name
                    response.status,
                    response.error or None,
                    response.request_id or None,
                    db_record_id,
                ),
            )
    except Exception as exc:
        logger.warning("Could not persist video generation to database: %s", exc)

    return rec_id


@router.post("/generate", response_model=VideoGenerateResponse)
async def generate_video_endpoint(body: VideoGenerateRequest) -> VideoGenerateResponse:
    """Generate a 5-second video from text prompt using Fal.ai Minimax H3 Max Turbo."""
    # Video requests do not carry a brand field; the current gate is brand-neutral.
    compliance = check_compliance(body.prompt, "unknown", "video")
    if compliance.result == "FAIL":
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Video prompt failed the insurance compliance gate.",
                "rules": compliance.rules,
                "issues": [issue.model_dump() for issue in compliance.issues],
                "suggested_revision": compliance.suggested_revision,
            },
        )
    # Strict validation: Duration cannot exceed 5 seconds
    if body.duration > 5:
        raise HTTPException(
            status_code=422,
            detail="Duration constraint violation: video duration cannot exceed 5 seconds.",
        )

    # Run in thread pool to prevent blocking the async event loop during Fal.ai call
    response = await asyncio.to_thread(generate_video, body)

    # Persist every generation attempt (COMPLETED or FAILED) for history
    _persist_generation(body, response)

    # If an asset_id was linked and video generated successfully, update content_assets media_url
    if response.status == "COMPLETED" and response.video and _is_valid_uuid(body.asset_id):
        try:
            with get_connection() as connection:
                connection.execute(
                    "update content_assets set media_url = %s where id = %s",
                    (response.video.url, body.asset_id),
                )
        except Exception:
            pass

    return response


@router.post("/attach", response_model=dict[str, Any])
def attach_video_to_asset(body: VideoAttachRequest) -> dict[str, Any]:
    """Attach a generated video URL to an existing marketing asset."""
    if not _is_valid_uuid(body.asset_id):
        raise HTTPException(status_code=400, detail="Invalid asset UUID format")

    try:
        with get_connection() as connection:
            connection.execute(
                "update content_assets set media_url = %s where id = %s",
                (body.video_url, body.asset_id),
            )
            row = connection.execute(
                "select id, title, media_url from content_assets where id = %s",
                (body.asset_id,),
            ).fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="Asset not found")
            return {
                "ok": True,
                "asset_id": str(row["id"]),
                "media_url": row["media_url"],
            }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to attach video: {exc}")


@router.post("/export-record", response_model=dict[str, Any])
def save_video_export(body: VideoSaveExportRequest) -> dict[str, Any]:
    """Save an exported/branded video URL to an existing generation record."""
    # 1. Update in memory history if present
    found_in_memory = False
    for rec in _MEMORY_HISTORY:
        if rec.id == body.id or rec.request_id == body.id:
            rec.branded_video_url = body.branded_video_url
            rec.branded_file_name = body.branded_file_name
            found_in_memory = True
            break

    # 2. Update PostgreSQL database if available
    db_updated = False
    if _is_valid_uuid(body.id):
        try:
            with get_connection() as connection:
                connection.execute(
                    """
                    update video_generations
                    set branded_video_url = %s, branded_file_name = %s
                    where id = %s
                    """,
                    (body.branded_video_url, body.branded_file_name, body.id),
                )
                row = connection.execute(
                    "select id from video_generations where id = %s",
                    (body.id,),
                ).fetchone()
                if row:
                    db_updated = True
        except Exception as exc:
            logger.warning("Could not update branded video in DB: %s", exc)

    return {
        "ok": True,
        "id": body.id,
        "branded_video_url": body.branded_video_url,
        "db_updated": db_updated,
        "memory_updated": found_in_memory,
    }


@router.get("/history", response_model=list[VideoGenerationRecord])
def list_video_history(
    limit: int = Query(default=20, ge=1, le=100),
    brand_id: str | None = Query(default=None),
) -> list[VideoGenerationRecord]:
    """Return up to `limit` past video generations, newest first."""
    db_records: list[VideoGenerationRecord] = []
    try:
        filters = []
        params: list[Any] = []
        if brand_id and brand_id != "all":
            filters.append("brand_id = %s")
            params.append(brand_id)
        where = ("where " + " and ".join(filters)) if filters else ""
        params.append(limit)
        query = f"""
            select id, brand_id, asset_id, prompt, aspect_ratio, resolution,
                   duration_secs, model, video_url, file_name, file_size,
                   branded_video_url, branded_file_name,
                   status, error_msg, request_id, created_at
            from video_generations
            {where}
            order by created_at desc
            limit %s
        """
        with get_connection() as connection:
            rows = connection.execute(query, params).fetchall()
        db_records = [
            VideoGenerationRecord(
                id=str(row["id"]),
                brand_id=row["brand_id"],
                asset_id=str(row["asset_id"]) if row["asset_id"] else None,
                prompt=row["prompt"],
                aspect_ratio=row["aspect_ratio"],
                resolution=row["resolution"],
                duration_secs=row["duration_secs"],
                model=row["model"],
                video_url=row["video_url"],
                file_name=row["file_name"],
                file_size=row["file_size"],
                branded_video_url=row.get("branded_video_url"),
                branded_file_name=row.get("branded_file_name"),
                status=row["status"],
                error_msg=row["error_msg"],
                request_id=row["request_id"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
    except Exception as exc:
        logger.debug("DB query for video history bypassed: %s", exc)

    # Merge memory records that are not in DB results
    db_ids = {r.id for r in db_records}
    filtered_memory = [
        m for m in _MEMORY_HISTORY
        if m.id not in db_ids and (not brand_id or brand_id == "all" or m.brand_id == brand_id)
    ]

    combined = db_records + filtered_memory
    combined.sort(key=lambda r: r.created_at, reverse=True)
    return combined[:limit]


@router.get("/config")
def get_video_config() -> dict[str, Any]:
    """Return model constraints and presets for the frontend UI."""
    return {
        "model": "minimax/h3-max-turbo/text-to-video",
        "max_duration_seconds": 5,
        "default_aspect_ratio": "9:16",
        "supported_aspect_ratios": ["9:16", "16:9", "1:1", "4:3", "3:4", "21:9"],
        "supported_resolutions": ["768P", "1080P", "480P"],
        "prompt_presets": {
            "jade": (
                "A luxury handcrafted emerald ring resting on black velvet in a high-end jewellery boutique, "
                "subtle golden studio lighting, slow cinematic macro camera orbit, 8k realism."
            ),
            "doctorshield": (
                "A calm modern clinic consulting room with morning sunlight streaming through the window, "
                "a stethoscope resting on a clean wooden desk, reassuring professional healthcare atmosphere, smooth cinematic tracking."
            ),
            "jaguar": (
                "An armored security transit vehicle arriving at an airport tarmac vault at dusk, "
                "high-tech digital telemetry heads-up display overlay, cinematic tracking shot, precise security logistics."
            ),
        },
    }
