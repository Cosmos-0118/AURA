"""Buffer channel listing and publish routes."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

try:
    from ..agents.buffer import (
        BufferError,
        BufferPublishRequest,
        BufferPublishResult,
        BufferStatus,
        key_configured,
        list_channels,
        publish_post,
    )
except ImportError:
    from agents.buffer import (  # type: ignore[no-redef]
        BufferError,
        BufferPublishRequest,
        BufferPublishResult,
        BufferStatus,
        key_configured,
        list_channels,
        publish_post,
    )

router = APIRouter(prefix="/api/buffer", tags=["buffer"])


def _http(exc: BufferError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/status", response_model=BufferStatus)
def buffer_status() -> BufferStatus:
    return BufferStatus(configured=key_configured())


@router.get("/channels")
def buffer_channels() -> dict:
    try:
        channels = list_channels()
    except BufferError as exc:
        raise _http(exc) from exc
    return {"channels": [channel.model_dump() for channel in channels]}


@router.post("/publish", response_model=BufferPublishResult)
def buffer_publish(body: BufferPublishRequest) -> BufferPublishResult:
    try:
        return publish_post(body)
    except BufferError as exc:
        raise _http(exc) from exc
