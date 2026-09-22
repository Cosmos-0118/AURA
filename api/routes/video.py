"""Video generation and attachment routes for AURA."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, HTTPException

try:
    from ..agents.video import generate_video
    from ..db import get_connection
    from ..rules.insurance_compliance import check_compliance
    from ..schemas import (
        Asset,
        VideoAttachRequest,
        VideoGenerateRequest,
        VideoGenerateResponse,
    )
except ImportError:  # Supports `cd api && uv run uvicorn main:app`.
    from agents.video import generate_video  # type: ignore[no-redef]
    from db import get_connection  # type: ignore[no-redef]
    from rules.insurance_compliance import check_compliance  # type: ignore[no-redef]
    from schemas import (  # type: ignore[no-redef]
        Asset,
        VideoAttachRequest,
        VideoGenerateRequest,
        VideoGenerateResponse,
    )

router = APIRouter(prefix="/api/video", tags=["video"])


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
