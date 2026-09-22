"""Buffer GraphQL API Client for AURA.
Interacts with https://api.buffer.com using BUFFER_API_KEY.
Supports channel discovery and multi-platform posting for LinkedIn, Instagram, and X.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
import httpx

_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ROOT_ENV)
load_dotenv()

logger = logging.getLogger("aura.publishing.buffer")
BUFFER_API_ENDPOINT = "https://api.buffer.com"


class BufferPublishError(Exception):
    """Exception raised when Buffer GraphQL or network request fails."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def get_buffer_api_key() -> str:
    """Retrieve and validate BUFFER_API_KEY from environment."""
    key = os.getenv("BUFFER_API_KEY", "").strip().strip('"').strip("'")
    if not key or key.startswith("your_") or set(key) <= {"x"}:
        raise BufferPublishError(
            "BUFFER_API_KEY is missing or invalid. Please configure BUFFER_API_KEY in your .env file.",
            status_code=401,
        )
    return key


def buffer_graphql(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a GraphQL query/mutation against Buffer API.
    Never silently swallows errors.
    """
    key = get_buffer_api_key()
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "query": query.strip(),
        "variables": variables or {},
    }

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(BUFFER_API_ENDPOINT, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        logger.error(f"Network error communicating with Buffer API: {exc}")
        raise BufferPublishError(f"Could not reach Buffer API: {exc}", status_code=502) from exc

    if resp.status_code in (401, 403):
        raise BufferPublishError(
            "Buffer authentication failed. Check your BUFFER_API_KEY.",
            status_code=401,
        )
    if resp.status_code >= 400:
        raise BufferPublishError(
            f"Buffer returned HTTP {resp.status_code}: {resp.text}",
            status_code=502,
        )

    try:
        data = resp.json()
    except Exception as exc:
        raise BufferPublishError("Buffer returned an invalid non-JSON response.", status_code=502) from exc

    # Check for GraphQL top-level errors
    if "errors" in data and data["errors"]:
        first_err = data["errors"][0]
        err_msg = first_err.get("message") if isinstance(first_err, dict) else str(first_err)
        logger.error(f"Buffer GraphQL error: {err_msg}")
        raise BufferPublishError(f"Buffer GraphQL error: {err_msg}", status_code=400)

    res_data = data.get("data")
    if res_data is None:
        raise BufferPublishError("Buffer returned empty data response.", status_code=502)

    return res_data


def discover_channels(organization_id: str | None = None) -> list[dict[str, Any]]:
    """Discover all connected Buffer channels across organizations or for a specific organization."""
    org_id = organization_id or os.getenv("BUFFER_ORGANIZATION_ID")

    if not org_id:
        org_query = """
        query GetOrganizations {
          account {
            id
            email
            organizations {
              id
              name
            }
          }
        }
        """
        org_res = buffer_graphql(org_query)
        account = org_res.get("account") or {}
        orgs = account.get("organizations") or []
        if not orgs:
            raise BufferPublishError("No organizations found under your Buffer account.")
        org_id = str(orgs[0]["id"])

    channel_query = """
    query GetChannels($organizationId: OrganizationId!) {
      channels(input: { organizationId: $organizationId }) {
        id
        name
        displayName
        service
      }
    }
    """
    channel_res = buffer_graphql(channel_query, {"organizationId": org_id})
    channels_raw = channel_res.get("channels") or []

    channels = []
    for c in channels_raw:
        channels.append({
            "id": str(c["id"]),
            "name": str(c.get("name") or ""),
            "display_name": str(c.get("displayName") or ""),
            "service": str(c.get("service") or "").lower(),
            "organization_id": org_id,
        })

    return channels


def get_channel_id(service: str, organization_id: str | None = None) -> str:
    """Resolve the Buffer channel ID for a given social service (linkedin, instagram, x/twitter).
    Prefers environment variables, then falls back to dynamic discovery from Buffer account.
    """
    svc = service.lower().strip()
    env_map = {
        "linkedin": os.getenv("BUFFER_LINKEDIN_CHANNEL_ID"),
        "instagram": os.getenv("BUFFER_INSTAGRAM_CHANNEL_ID"),
        "x": os.getenv("BUFFER_X_CHANNEL_ID") or os.getenv("BUFFER_TWITTER_CHANNEL_ID"),
        "twitter": os.getenv("BUFFER_X_CHANNEL_ID") or os.getenv("BUFFER_TWITTER_CHANNEL_ID"),
    }

    env_val = env_map.get(svc)
    if env_val and env_val.strip():
        return env_val.strip()

    # Discover automatically from Buffer
    channels = discover_channels(organization_id)
    for c in channels:
        channel_svc = c["service"].lower()
        if svc in ("x", "twitter") and channel_svc in ("x", "twitter"):
            return c["id"]
        if channel_svc == svc:
            return c["id"]

    service_display = "X" if svc in ("x", "twitter") else svc.title()
    raise BufferPublishError(
        f"No connected Buffer channel found for {service_display}. "
        f"Please connect your {service_display} account inside Buffer or set BUFFER_{svc.upper()}_CHANNEL_ID in .env."
    )


def create_buffer_post(
    channel_id: str,
    text: str,
    mode: str = "addToQueue",
    assets: list[dict[str, Any]] | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute createPost mutation on Buffer with error inspection."""
    mutation = """
    mutation CreatePost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess {
          post {
            id
            text
            dueAt
            assets {
              id
              mimeType
              source
            }
          }
        }
        ... on MutationError {
          message
        }
      }
    }
    """

    input_payload: dict[str, Any] = {
        "channelId": channel_id,
        "text": text.strip(),
        "schedulingType": "automatic",
        "mode": mode,
    }

    if assets:
        input_payload["assets"] = assets

    if metadata:
        input_payload["metadata"] = metadata

    data = buffer_graphql(mutation, {"input": input_payload})
    result = data.get("createPost") or {}

    # Handle MutationError
    if "message" in result and not result.get("post"):
        err_msg = str(result["message"])
        logger.error(f"Buffer createPost failed: {err_msg}")
        raise BufferPublishError(f"Buffer publishing error: {err_msg}")

    post = result.get("post")
    if not post or not post.get("id"):
        raise BufferPublishError("Buffer did not return a post ID upon publication.")

    return {
        "post_id": str(post["id"]),
        "text": post.get("text"),
        "due_at": post.get("dueAt"),
    }
