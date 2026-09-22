"""AURA Public Media URL Builder & Pre-Flight Reachability Validator.
Ensures media generated locally under storage/ is converted to publicly accessible HTTPS
URLs for Buffer's GraphQL API and verified prior to publishing.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import load_dotenv
import httpx

_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ROOT_ENV)
load_dotenv()

logger = logging.getLogger("aura.media.url")


class MediaConfigurationError(ValueError):
    """Raised when MEDIA_PUBLIC_BASE_URL is missing, misconfigured, or uses localhost."""
    pass


class MediaUnreachableError(RuntimeError):
    """Raised when the public media URL cannot be reached externally or returns an error."""
    pass


def get_configured_media_base_url() -> str:
    """Retrieve and validate MEDIA_PUBLIC_BASE_URL from the environment."""
    base_url = os.getenv("MEDIA_PUBLIC_BASE_URL", "").strip().rstrip("/")
    if not base_url:
        raise MediaConfigurationError(
            "MEDIA_PUBLIC_BASE_URL is not configured. Buffer requires a publicly accessible HTTPS media URL."
        )

    parsed = urlparse(base_url)
    hostname = (parsed.hostname or "").lower()

    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or any(
        sub in base_url.lower() for sub in ("localhost", "127.0.0.1", "0.0.0.0", "::1")
    ):
        raise MediaConfigurationError("Public media URL cannot use localhost or 127.0.0.1.")

    if parsed.scheme not in ("http", "https"):
        raise MediaConfigurationError(
            f"MEDIA_PUBLIC_BASE_URL has an invalid scheme '{parsed.scheme}'. Must be http or https."
        )

    return base_url


def build_public_media_url(relative_path: str, base_url: str | None = None) -> str:
    """Convert a stored relative media path into a public /media/... URL.

    Requirements:
    1. Reads MEDIA_PUBLIC_BASE_URL from environment/config.
    2. Normalizes leading/trailing slashes.
    3. Converts stored relative media path into a public /media/... URL.
    4. Never exposes absolute local filesystem paths.
    5. Never returns file://.
    6. Never returns localhost or 127.0.0.1 as a Buffer media URL.
    7. Returns HTTPS URL when MEDIA_PUBLIC_BASE_URL is HTTPS.
    8. Raises a clear backend configuration error if MEDIA_PUBLIC_BASE_URL is missing.

    Examples:
        storage/campaigns/123/image/final_v1.png -> https://abc.ngrok-free.app/media/campaigns/123/image/final_v1.png
        campaigns/123/image/final_v1.png         -> https://abc.ngrok-free.app/media/campaigns/123/image/final_v1.png
    """
    resolved_base = base_url.strip().rstrip("/") if base_url else get_configured_media_base_url()

    # Re-verify resolved_base against localhost if passed explicitly
    if any(h in resolved_base.lower() for h in ("localhost", "127.0.0.1", "0.0.0.0", "::1")):
        raise MediaConfigurationError("Public media URL cannot use localhost or 127.0.0.1.")

    if not relative_path or not str(relative_path).strip():
        raise ValueError("Media path cannot be empty.")

    clean = str(relative_path).strip().replace("\\", "/")

    # Strip file:// prefix if present
    if clean.startswith("file://"):
        clean = clean[len("file://"):]

    # Remove absolute local filesystem path prefixes (never expose local folders/usernames)
    if "storage/campaigns/" in clean:
        clean = clean[clean.index("storage/campaigns/"):]
    elif "campaigns/" in clean:
        clean = clean[clean.index("campaigns/"):]

    # Normalize away storage/ or media/ prefix to obtain subpath under /media/
    if clean.startswith("/storage/"):
        clean = clean[len("/storage/"):]
    elif clean.startswith("storage/"):
        clean = clean[len("storage/"):]
    elif clean.startswith("/media/"):
        clean = clean[len("/media/"):]
    elif clean.startswith("media/"):
        clean = clean[len("media/"):]

    clean = clean.lstrip("/")

    # Security check: forbid directory traversal
    if ".." in clean or clean.startswith("/"):
        raise ValueError("Invalid media path: path traversal is not permitted.")

    public_url = f"{resolved_base}/media/{clean}"

    # Final sanity checks
    if any(h in public_url.lower() for h in ("localhost", "127.0.0.1", "file://")):
        raise MediaConfigurationError("Public media URL cannot use localhost or 127.0.0.1.")

    return public_url


def _validate_parsed_url(url: str) -> None:
    """Check url scheme, hostname, and ensure it is not localhost or private."""
    if not url or not isinstance(url, str):
        raise MediaConfigurationError("Media URL must be a valid non-empty string.")

    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        raise MediaConfigurationError("Public media URL must use HTTP or HTTPS.")

    hostname = (parsed.hostname or "").lower()
    if not hostname:
        raise MediaConfigurationError("Public media URL has no valid hostname.")

    if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1") or any(
        sub in url.lower() for sub in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "file://")
    ):
        raise MediaConfigurationError("Public media URL cannot use localhost or 127.0.0.1.")


async def validate_public_media_url(url: str, timeout: float = 10.0) -> bool:
    """Asynchronously verify that the generated public media URL is accessible.
    Issues a HEAD request (falling back to a small range GET if HEAD is not supported).
    """
    _validate_parsed_url(url)

    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            resp = await client.head(url)
            if resp.status_code in (405, 501):
                # HEAD not allowed on static endpoint, fallback to partial GET
                resp = await client.get(url, headers={"Range": "bytes=0-1024"})

            if resp.status_code >= 400:
                logger.error(f"Public media URL {url} returned HTTP {resp.status_code}")
                raise MediaUnreachableError(
                    f"Buffer cannot access the media URL (HTTP {resp.status_code}). "
                    "Check MEDIA_PUBLIC_BASE_URL and your public tunnel/domain."
                )
    except httpx.HTTPError as exc:
        logger.error(f"Failed to reach public media URL {url}: {exc}")
        raise MediaUnreachableError(
            "Buffer cannot access the media URL. Check MEDIA_PUBLIC_BASE_URL and your public tunnel/domain."
        ) from exc

    return True


def validate_public_media_url_sync(url: str, timeout: float = 10.0) -> bool:
    """Synchronously verify that the generated public media URL is accessible."""
    _validate_parsed_url(url)

    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.head(url)
            if resp.status_code in (405, 501):
                resp = client.get(url, headers={"Range": "bytes=0-1024"})

            if resp.status_code >= 400:
                logger.error(f"Public media URL {url} returned HTTP {resp.status_code}")
                raise MediaUnreachableError(
                    f"Buffer cannot access the media URL (HTTP {resp.status_code}). "
                    "Check MEDIA_PUBLIC_BASE_URL and your public tunnel/domain."
                )
    except httpx.HTTPError as exc:
        logger.error(f"Failed to reach public media URL {url}: {exc}")
        raise MediaUnreachableError(
            "Buffer cannot access the media URL. Check MEDIA_PUBLIC_BASE_URL and your public tunnel/domain."
        ) from exc

    return True


def get_media_config() -> dict[str, Any]:
    """Safe diagnostic information about public media configuration."""
    raw_base = os.getenv("MEDIA_PUBLIC_BASE_URL", "").strip().rstrip("/")
    is_configured = False
    base_url = None

    if raw_base:
        parsed = urlparse(raw_base)
        hostname = (parsed.hostname or "").lower()
        if (
            parsed.scheme in ("http", "https")
            and hostname not in ("localhost", "127.0.0.1", "0.0.0.0", "::1")
            and not any(h in raw_base.lower() for h in ("localhost", "127.0.0.1", "0.0.0.0", "::1"))
        ):
            is_configured = True
            base_url = raw_base

    return {
        "configured": is_configured,
        "base_url": base_url,
        "media_endpoint_available": True,
    }
