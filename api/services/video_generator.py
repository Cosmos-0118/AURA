"""AURA Video Generator Service.
Generates video using fal-client (e.g. minimax/h3-max-turbo) and saves locally to storage/campaigns/{campaign_id}/video.mp4.
"""

import os
from pathlib import Path
from typing import Any

import httpx

STORAGE_BASE = Path(__file__).resolve().parent.parent.parent / "storage"


def ensure_campaign_dir(campaign_id: str) -> Path:
    target_dir = STORAGE_BASE / "campaigns" / campaign_id
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def create_demo_video(target_path: Path) -> None:
    """Ensure a local video file exists for demo mode."""
    # Write a minimal valid mp4 container header so file exists locally
    if not target_path.exists():
        with open(target_path, "wb") as f:
            # Minimal MP4 ftyp box bytes
            f.write(b"\x00\x00\x00\x20ftypisom\x00\x00\x02\x00isomiso2mp41\x00\x00\x00\x08free")


def generate_video(
    campaign_id: str,
    prompt: str,
    model: str | None = None,
    demo_mode: bool = False,
) -> dict[str, Any]:
    """Generate vertical Reel video and persist locally."""
    target_dir = ensure_campaign_dir(campaign_id)
    target_path = target_dir / "video.mp4"

    chosen_model = model or os.environ.get("VIDEO_MODEL", "minimax/h3-max-turbo")

    if demo_mode:
        create_demo_video(target_path)
        return {
            "local_path": f"/storage/campaigns/{campaign_id}/video.mp4",
            "provider": "demo_local",
            "model": chosen_model,
            "status": "completed",
        }

    fal_key = os.environ.get("FAL_KEY")
    if not fal_key:
        # In live mode without FAL_KEY, raise error or return demo fallback
        create_demo_video(target_path)
        return {
            "local_path": f"/storage/campaigns/{campaign_id}/video.mp4",
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
            with open(target_path, "wb") as f:
                f.write(resp.content)

        return {
            "local_path": f"/storage/campaigns/{campaign_id}/video.mp4",
            "provider": "fal",
            "model": chosen_model,
            "status": "completed",
        }
    except Exception as exc:
        raise RuntimeError(f"FAL video generation failed: {exc}") from exc
