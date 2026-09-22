"""Video generation and attachment routes for AURA."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException, Query

try:
    from ..agents.video import generate_video
    from ..db import get_connection
    from ..schemas import (
        VideoAttachRequest,
        VideoGenerateRequest,
        VideoGenerateResponse,
        VideoGenerationRecord,
    )
except ImportError:  # Supports `cd api && uv run uvicorn main:app`.
    from agents.video import generate_video  # type: ignore[no-redef]
    from db import get_connection  # type: ignore[no-redef]
    from schemas import (  # type: ignore[no-redef]
        VideoAttachRequest,
        VideoGenerateRequest,
        VideoGenerateResponse,
        VideoGenerationRecord,
    )

router = APIRouter(prefix="/api/video", tags=["video"])

_INSERT_GENERATION = """
insert into video_generations
  (brand_id, asset_id, prompt, aspect_ratio, resolution, duration_secs,
   model, video_url, file_name, file_size, status, error_msg, request_id)
values
  (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
returning id, created_at
"""

_MODEL = "minimax/h3-max-turbo/text-to-video"


def _persist_generation(
    body: VideoGenerateRequest,
    response: VideoGenerateResponse,
) -> None:
    """Best-effort insert into video_generations. Never raises."""
    try:
        with get_connection() as connection:
            connection.execute(
                _INSERT_GENERATION,
                (
                    body.asset_id or None,   # brand_id — not in request; use asset_id as proxy or None
                    body.asset_id or None,
                    body.prompt,
                    body.aspect_ratio,
                    body.resolution,
                    body.duration,
                    _MODEL,
                    response.video.url if response.video else None,
                    response.video.file_name if response.video else None,
                    response.video.file_size if response.video else None,
                    response.status,
                    response.error or None,
                    response.request_id or None,
                ),
            )
    except Exception:
        # DB unavailable or table missing (dev/mock mode) — silently skip
        pass


@router.post("/generate", response_model=VideoGenerateResponse)
async def generate_video_endpoint(body: VideoGenerateRequest) -> VideoGenerateResponse:
    """Generate a 5-second video from text prompt using Fal.ai Minimax H3 Max Turbo."""
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
    if response.status == "COMPLETED" and response.video and body.asset_id:
        try:
            with get_connection() as connection:
                connection.execute(
                    "update content_assets set media_url = %s where id = %s",
                    (response.video.url, body.asset_id),
                )
        except Exception:
            # Don't fail video generation if DB is temporarily unreachable in dev/mock mode
            pass

    return response


@router.post("/attach", response_model=dict[str, Any])
def attach_video_to_asset(body: VideoAttachRequest) -> dict[str, Any]:
    """Attach a generated video URL to an existing marketing asset."""
    try:
        with get_connection() as connection:
            row = connection.execute(
                "update content_assets set media_url = %s where id = %s returning id, title, media_url",
                (body.video_url, body.asset_id),
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


@router.get("/history", response_model=list[VideoGenerationRecord])
def list_video_history(
    limit: int = Query(default=20, ge=1, le=100),
    brand_id: str | None = Query(default=None),
) -> list[VideoGenerationRecord]:
    """Return up to `limit` past video generations, newest first.

    Returns an empty list gracefully when the DB is unavailable (dev/mock mode)
    or the video_generations table does not yet exist.
    """
    try:
        filters = []
        params: list[Any] = []
        if brand_id:
            filters.append("brand_id = %s")
            params.append(brand_id)
        where = ("where " + " and ".join(filters)) if filters else ""
        params.append(limit)
        query = f"""
            select id, brand_id, asset_id, prompt, aspect_ratio, resolution,
                   duration_secs, model, video_url, file_name, file_size,
                   status, error_msg, request_id, created_at
            from video_generations
            {where}
            order by created_at desc
            limit %s
        """
        with get_connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [
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
                status=row["status"],
                error_msg=row["error_msg"],
                request_id=row["request_id"],
                created_at=row["created_at"],
            )
            for row in rows
        ]
    except Exception:
        # DB unavailable or table missing — return empty list so UI degrades gracefully
        return []


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
