"""Buffer GraphQL client for listing channels and publishing posts.

Social accounts are connected inside Buffer. This module only uses
BUFFER_API_KEY from the environment and never stores channel passwords.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

import httpx
from dotenv import load_dotenv
from pydantic import BaseModel, Field

_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ROOT_ENV)
load_dotenv()

BUFFER_ENDPOINT = "https://api.buffer.com"
ShareMode = Literal["shareNow", "addToQueue", "shareNext", "customScheduled"]
InstagramType = Literal["post", "story", "reel"]

_ORG_QUERY = """
query GetOrganizations {
  account {
    organizations {
      id
      name
    }
  }
}
"""

_CHANNELS_QUERY = """
query GetChannels($organizationId: OrganizationId!) {
  channels(input: { organizationId: $organizationId }) {
    id
    name
    displayName
    service
    avatar
    isQueuePaused
  }
}
"""

_CREATE_POST = """
mutation CreatePost($input: CreatePostInput!) {
  createPost(input: $input) {
    __typename
    ... on PostActionSuccess {
      post {
        id
        dueAt
        text
      }
    }
    ... on MutationError {
      message
    }
  }
}
"""


class BufferError(Exception):
    """Buffer rejected the request or returned an unusable payload."""

    def __init__(self, message: str, status_code: int = 502) -> None:
        super().__init__(message)
        self.status_code = status_code


class BufferChannel(BaseModel):
    id: str
    name: str
    display_name: str = ""
    service: str
    avatar: str = ""
    is_queue_paused: bool = False
    organization_id: str
    organization_name: str


class BufferStatus(BaseModel):
    configured: bool
    endpoint: str = BUFFER_ENDPOINT


class BufferPublishRequest(BaseModel):
    channel_id: str = Field(min_length=1)
    text: str = Field(min_length=1)
    mode: ShareMode = "shareNow"
    due_at: str | None = None
    image_url: str | None = None
    video_url: str | None = None
    instagram_type: InstagramType | None = None


class BufferPublishResult(BaseModel):
    ok: bool
    post_id: str | None = None
    due_at: str | None = None
    message: str


def api_key() -> str:
    value = os.getenv("BUFFER_API_KEY", "").strip().strip('"').strip("'")
    if not value or value.startswith("your_") or set(value) <= {"x"}:
        return ""
    return value


def key_configured() -> bool:
    return bool(api_key())


def _headers() -> dict[str, str]:
    key = api_key()
    if not key:
        raise BufferError(
            "BUFFER_API_KEY is missing. Add it to the project .env, then restart the API.",
            status_code=400,
        )
    return {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }


def _graphql(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    try:
        response = httpx.post(
            BUFFER_ENDPOINT,
            headers=_headers(),
            json={"query": query, "variables": variables or {}},
            timeout=30.0,
        )
    except httpx.HTTPError as exc:
        raise BufferError(f"Could not reach Buffer: {exc}") from exc

    if response.status_code in {401, 403}:
        raise BufferError(
            "Buffer rejected the API key. Create a new key in Buffer → Settings → API.",
            status_code=401,
        )
    if response.status_code >= 400:
        raise BufferError(f"Buffer returned HTTP {response.status_code}.", status_code=502)

    try:
        payload = response.json()
    except ValueError as exc:
        raise BufferError("Buffer returned a non-JSON response.") from exc

    errors = payload.get("errors") or []
    if errors:
        message = errors[0].get("message") if isinstance(errors[0], dict) else str(errors[0])
        raise BufferError(message or "Buffer GraphQL error.")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise BufferError("Buffer returned an empty data payload.")
    return data


def list_channels() -> list[BufferChannel]:
    org_data = _graphql(_ORG_QUERY)
    account = org_data.get("account") or {}
    organizations = account.get("organizations") or []
    channels: list[BufferChannel] = []
    for org in organizations:
        org_id = str(org.get("id") or "")
        org_name = str(org.get("name") or "")
        if not org_id:
            continue
        channel_data = _graphql(_CHANNELS_QUERY, {"organizationId": org_id})
        for channel in channel_data.get("channels") or []:
            channels.append(
                BufferChannel(
                    id=str(channel.get("id") or ""),
                    name=str(channel.get("name") or ""),
                    display_name=str(channel.get("displayName") or ""),
                    service=str(channel.get("service") or ""),
                    avatar=str(channel.get("avatar") or ""),
                    is_queue_paused=bool(channel.get("isQueuePaused")),
                    organization_id=org_id,
                    organization_name=org_name,
                )
            )
    return channels


def _build_input(req: BufferPublishRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "text": req.text.strip(),
        "channelId": req.channel_id,
        "schedulingType": "automatic",
        "mode": req.mode,
        "aiAssisted": True,
    }
    assets: list[dict[str, Any]] = []
    if req.image_url and req.image_url.strip():
        assets.append({"image": {"url": req.image_url.strip()}})
    if req.video_url and req.video_url.strip():
        assets.append({"video": {"url": req.video_url.strip()}})
    if assets:
        payload["assets"] = assets
    if req.mode == "customScheduled":
        if not req.due_at:
            raise BufferError("A due_at timestamp is required for customScheduled.", status_code=422)
        payload["dueAt"] = req.due_at
    if req.instagram_type:
        payload["metadata"] = {
            "instagram": {
                "type": req.instagram_type,
                "shouldShareToFeed": req.instagram_type != "story",
            }
        }
    return payload


def publish_post(req: BufferPublishRequest) -> BufferPublishResult:
    data = _graphql(_CREATE_POST, {"input": _build_input(req)})
    result = data.get("createPost") or {}
    if result.get("message") and not result.get("post"):
        raise BufferError(str(result["message"]), status_code=400)
    post = result.get("post") or {}
    post_id = post.get("id")
    if not post_id:
        raise BufferError("Buffer did not return a post id.")
    when = "published immediately" if req.mode == "shareNow" else f"queued with mode {req.mode}"
    return BufferPublishResult(
        ok=True,
        post_id=str(post_id),
        due_at=post.get("dueAt"),
        message=f"Buffer accepted the post ({when}).",
    )
