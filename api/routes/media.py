"""FastAPI Media Diagnostics & Configuration Route.
Safely exposes public media configuration status for AURA Buffer publishing diagnostics.
Never exposes API keys, secrets, or internal filesystem paths.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

try:
    from ..media.url import get_media_config
except ImportError:
    from media.url import get_media_config

router = APIRouter(prefix="/api/media", tags=["media"])


class MediaConfigResponse(BaseModel):
    configured: bool
    base_url: str | None = None
    media_endpoint_available: bool = True


@router.get("/config", response_model=MediaConfigResponse)
def get_media_configuration_route() -> MediaConfigResponse:
    """Safe diagnostic endpoint returning public media URL configuration state."""
    config = get_media_config()
    return MediaConfigResponse(
        configured=config["configured"],
        base_url=config["base_url"],
        media_endpoint_available=config.get("media_endpoint_available", True),
    )
