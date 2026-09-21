"""AURA Video Generator Service.
Generates vertical video using fal-client (minimax/h3-max-turbo) and saves locally to storage/campaigns/{campaign_id}/video/{filename}.
"""

import os
from pathlib import Path
from typing import Any

import httpx

try:
    from ..repositories.media import determine_next_media_path
except ImportError:
    from repositories.media import determine_next_media_path


def create_demo_video(target_path: Path) -> None:
    """Ensure a local video file exists for demo mode."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if not target_path.exists():
        with open(target_path, "wb") as f:
            # Minimal MP4 container box header bytes
            f.write(b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41\x00\x00\x00\x08free")


def generate_video(
    campaign_id: str,
    prompt: str,
    model: str | None = None,
    demo_mode: bool = False,
) -> dict[str, Any]:
    """Generate vertical Reel video and persist locally to storage/campaigns/{campaign_id}/video/{filename}."""
    target_path, filename, rel_path = determine_next_media_path(campaign_id, "video")
    chosen_model = model or os.environ.get("VIDEO_MODEL", "minimax/h3-max-turbo")

    if demo_mode:
        create_demo_video(target_path)
        file_size = target_path.stat().st_size if target_path.exists() else 1024
        return {
            "local_path": rel_path,
            "url": f"/{rel_path}",
            "filename": filename,
            "mime_type": "video/mp4",
            "file_size": file_size,
            "duration_seconds": 5.0,
            "provider": "demo_local",
            "model": chosen_model,
            "status": "completed",
        }

    fal_key = os.environ.get("FAL_KEY")
    if not fal_key:
        create_demo_video(target_path)
        file_size = target_path.stat().st_size if target_path.exists() else 1024
        return {
            "local_path": rel_path,
            "url": f"/{rel_path}",
            "filename": filename,
            "mime_type": "video/mp4",
            "file_size": file_size,
            "duration_seconds": 5.0,
            "provider": "local_fallback",
            "model": chosen_model,
            "status": "completed",
        }

    try:
        import fal_client

        result = fal_client.subscribe(
            chosen_model,
            arguments={
                "prompt": prompt,
                "prompt_expansion_mode": "disabled",
                "duration": 5,
                "resolution": "768P",
                "enable_safety_checker": True,
                "aspect_ratio": "9:16",
            },
            with_logs=True,
        )

        video_info = result.get("video", {})
        video_url = video_info.get("url")
        if not video_url:
            raise ValueError(f"FAL returned no video URL: {result}")

        with httpx.Client(timeout=60.0) as client:
            resp = client.get(video_url)
            resp.raise_for_status()
            target_path.parent.mkdir(parents=True, exist_ok=True)
            with open(target_path, "wb") as f:
                f.write(resp.content)

        file_size = target_path.stat().st_size
        return {
            "local_path": rel_path,
            "url": f"/{rel_path}",
            "filename": filename,
            "mime_type": "video/mp4",
            "file_size": file_size,
            "duration_seconds": 5.0,
            "provider": "fal",
            "model": chosen_model,
            "status": "completed",
        }
    except Exception as exc:
        raise RuntimeError(f"FAL video generation failed: {exc}") from exc
