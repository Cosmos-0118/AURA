"""Fal.ai Text-to-Video Agent for AURA.

Uses Fal.ai `minimax/h3-max-turbo/text-to-video` model.
Enforces strict 5-second maximum duration limit.
Falls back safely to mock video if key is absent or AURA_MOCK_AGENTS=true.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Callable

try:
    from ..schemas import (
        VideoFile,
        VideoGenerateRequest,
        VideoGenerateResponse,
    )
except ImportError:  # Supports `cd api && uv run uvicorn main:app`.
    from schemas import (  # type: ignore[no-redef]
        VideoFile,
        VideoGenerateRequest,
        VideoGenerateResponse,
    )

logger = logging.getLogger("aura.agents.video")

_DEFAULT_MODEL = "minimax/h3-max-turbo/text-to-video"
_MOCK_SAMPLE_VIDEO = (
    "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
)


def _get_fal_key() -> str | None:
    key = os.getenv("FAL_KEY") or os.getenv("FAL_AI_API_KEY")
    if key and key.strip() and key != "your_fal_api_key_here":
        os.environ["FAL_KEY"] = key.strip()
        return key.strip()
    return None


def _get_model_name() -> str:
    return os.getenv("VIDEO_MODEL", _DEFAULT_MODEL)


def _is_mock_enabled() -> bool:
    mock_flag = os.getenv("AURA_MOCK_AGENTS", "false").lower() == "true"
    has_key = _get_fal_key() is not None
    return mock_flag and not has_key


def generate_video(
    req: VideoGenerateRequest,
    on_log: Callable[[str], None] | None = None,
) -> VideoGenerateResponse:
    """Generate a video using Fal.ai Minimax H3 Max Turbo.

    Enforces STRICT 5-second maximum constraint.
    """
    # Hard clamp to ensure max 5 seconds, zero microseconds beyond 5s
    safe_duration = min(max(int(req.duration), 1), 5)
    model_name = _get_model_name()
    fal_key = _get_fal_key()

    # Fallback to mock if key is missing or mock is explicitly forced without a key
    if not fal_key or _is_mock_enabled():
        logger.info("Using mock video generation (key missing or mock enabled)")
        msg1 = f"[Mock] Queued video request for model: {model_name}"
        msg2 = f"[Mock] Generating 5s {req.aspect_ratio} video for prompt: '{req.prompt[:60]}...'"
        msg3 = "[Mock] Completed rendering video asset."
        if on_log:
            on_log(msg1)
            on_log(msg2)
            on_log(msg3)
        return VideoGenerateResponse(
            status="COMPLETED",
            request_id="mock-video-req-001",
            video=VideoFile(
                file_name="aura_demo_5s_reel.mp4",
                url=_MOCK_SAMPLE_VIDEO,
                content_type="video/mp4",
                file_size=3145728,
            ),
            expanded_prompt=req.prompt,
            asset_id=req.asset_id,
            logs=[msg1, msg2, msg3],
        )

    # Real Fal.ai generation via fal-client
    try:
        import fal_client

        collected_logs: list[str] = []

        def _on_queue_update(update: Any) -> None:
            if isinstance(update, fal_client.InProgress):
                for entry in getattr(update, "logs", []):
                    msg = entry.get("message") if isinstance(entry, dict) else str(entry)
                    if msg:
                        collected_logs.append(msg)
                        if on_log:
                            on_log(msg)

        arguments = {
            "prompt": req.prompt,
            "duration": safe_duration,  # strictly <= 5 seconds
            "aspect_ratio": req.aspect_ratio,
            "resolution": req.resolution,
            "prompt_expansion_mode": req.prompt_expansion_mode,
            "enable_safety_checker": True,
        }

        logger.info("Submitting video generation to Fal.ai: %s", arguments)
        result = fal_client.subscribe(
            model_name,
            arguments=arguments,
            with_logs=True,
            on_queue_update=_on_queue_update,
        )

        logger.info("Fal.ai returned result: %s", result)
        video_data = result.get("video") if isinstance(result, dict) else None
        if not video_data or not isinstance(video_data, dict) or not video_data.get("url"):
            error_msg = f"Fal.ai returned unexpected format: {result}"
            return VideoGenerateResponse(
                status="FAILED",
                error=error_msg,
                asset_id=req.asset_id,
                logs=collected_logs,
            )

        return VideoGenerateResponse(
            status="COMPLETED",
            video=VideoFile(
                file_name=video_data.get("file_name"),
                url=video_data["url"],
                content_type=video_data.get("content_type", "video/mp4"),
                file_size=video_data.get("file_size"),
            ),
            expanded_prompt=result.get("expanded_prompt"),
            asset_id=req.asset_id,
            logs=collected_logs,
        )

    except Exception as exc:
        logger.exception("Error during Fal.ai video generation: %s", exc)
        return VideoGenerateResponse(
            status="FAILED",
            error=str(exc),
            asset_id=req.asset_id,
            logs=[f"Execution failed: {exc}"],
        )
