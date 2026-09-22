"""AURA Platform Publishing Service.
Orchestrates campaign publication to LinkedIn, Instagram, and X via Buffer GraphQL API.
Enforces approval validation, final watermarked media usage, public media URL generation,
pre-flight reachability validation, and duplicate publishing protection.
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv

from .buffer import BufferPublishError, create_buffer_post, get_channel_id

try:
    from ..media.url import (
        MediaConfigurationError,
        MediaUnreachableError,
        build_public_media_url,
        validate_public_media_url_sync,
    )
    from ..repositories.events import log_event
except ImportError:
    from media.url import (
        MediaConfigurationError,
        MediaUnreachableError,
        build_public_media_url,
        validate_public_media_url_sync,
    )
    from repositories.events import log_event

_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ROOT_ENV)
load_dotenv()

logger = logging.getLogger("aura.publishing.service")


def get_public_media_url(local_path: str, media_type: str = "image") -> str:
    """Convert local media storage path to a publicly accessible URL for Buffer.
    Delegates to api.media.url.build_public_media_url with strict validation.
    """
    try:
        return build_public_media_url(local_path)
    except (MediaConfigurationError, ValueError) as exc:
        raise BufferPublishError(str(exc)) from exc


def publish_to_platform(db: Any, campaign_id: str, platform: str) -> dict[str, Any]:
    """Publish approved campaign content and final watermarked media to a specific platform via Buffer.
    Supported platforms: linkedin, instagram, x
    """
    plat = platform.lower().strip()
    if plat in ("twitter", "x"):
        plat = "x"
    elif plat not in ("linkedin", "instagram"):
        raise ValueError(f"Unsupported publishing platform '{platform}'. Supported: linkedin, instagram, x.")

    # 1. Validate Campaign exists and is APPROVED
    c_row = db.execute("SELECT * FROM campaigns WHERE id = %s", (campaign_id,)).fetchone()
    if not c_row:
        raise ValueError(f"Campaign '{campaign_id}' not found.")

    c_status = (c_row.get("status") or "").lower()
    if c_status not in ("approved", "published"):
        raise ValueError(
            f"Campaign must be approved before publishing. Current status is '{c_status}'."
        )

    # 2. Duplicate Publish Protection
    existing = db.execute(
        """
        SELECT * FROM campaign_publications
        WHERE campaign_id = %s AND platform = %s AND status = 'published'
        ORDER BY created_at DESC LIMIT 1
        """,
        (campaign_id, plat),
    ).fetchone()

    if existing:
        post_id = existing.get("buffer_post_id") or existing.get("external_post_id")
        return {
            "success": False,
            "already_published": True,
            "campaign_id": campaign_id,
            "publication_id": str(existing["id"]),
            "post_id": post_id,
            "platform": plat,
            "status": "published",
            "external_post_id": post_id,
            "external_post_url": existing.get("external_post_url") or "https://publish.buffer.com",
            "message": f"Already published to {plat.upper() if plat == 'x' else plat.title()}.",
            "published_at": str(existing.get("published_at") or existing.get("created_at")),
        }

    # 3. Load Approved Platform Copy (exact saved copy, no regeneration)
    content_row = db.execute(
        """
        SELECT * FROM campaign_platform_content
        WHERE campaign_id = %s AND platform = %s AND (is_current = 1 OR is_current IS NULL)
        ORDER BY version DESC, created_at DESC LIMIT 1
        """,
        (campaign_id, plat),
    ).fetchone()

    if not content_row:
        content_row = db.execute(
            """
            SELECT * FROM campaign_platform_content
            WHERE campaign_id = %s AND platform = %s
            ORDER BY created_at DESC LIMIT 1
            """,
            (campaign_id, plat),
        ).fetchone()

    if not content_row or not content_row.get("content"):
        raise ValueError(f"No approved content found for platform '{plat}'.")

    text = content_row["content"].strip()

    # Append hashtags if stored separately and not already embedded
    hashtags_raw = content_row.get("hashtags")
    tags = []
    if isinstance(hashtags_raw, str):
        try:
            tags = json.loads(hashtags_raw)
        except Exception:
            tags = [t.strip() for t in hashtags_raw.split() if t.strip()]
    elif isinstance(hashtags_raw, list):
        tags = hashtags_raw

    missing_tags = []
    for t in tags:
        clean_tag = t if t.startswith("#") else f"#{t}"
        if clean_tag not in text:
            missing_tags.append(clean_tag)
    if missing_tags:
        text = f"{text}\n\n{' '.join(missing_tags)}"

    # 4. Load Approved Final Watermarked Media (NEVER original AI media)
    media_row = db.execute(
        """
        SELECT * FROM campaign_media
        WHERE campaign_id = %s
          AND media_stage = 'final'
          AND status = 'completed'
          AND (watermarked = 1 OR watermarked IS TRUE)
        ORDER BY created_at DESC LIMIT 1
        """,
        (campaign_id,),
    ).fetchone()

    if not media_row or not media_row.get("local_path"):
        raise BufferPublishError("Final watermarked media is not ready.")

    media_id = str(media_row["id"])
    media_type = media_row.get("media_type", "image")

    # 5. Build and Pre-Flight Validate Public Media URL
    try:
        pub_url = build_public_media_url(media_row["local_path"])
    except MediaConfigurationError as exc:
        raise BufferPublishError(str(exc)) from exc
    except Exception as exc:
        raise BufferPublishError(f"Failed to build public media URL: {exc}") from exc

    # Reachability pre-flight verification (unless explicitly skipped in testing)
    skip_reachability = os.getenv("SKIP_MEDIA_URL_REACHABILITY_CHECK", "false").lower() in ("true", "1", "yes")
    if not skip_reachability:
        try:
            validate_public_media_url_sync(pub_url)
        except MediaUnreachableError as exc:
            raise BufferPublishError(str(exc)) from exc
        except Exception as exc:
            raise BufferPublishError(
                "Buffer cannot access the media URL. Check MEDIA_PUBLIC_BASE_URL and your public tunnel/domain."
            ) from exc

    # 6. Format Buffer Assets Payload
    assets: list[dict[str, Any]] = []
    if media_type == "image":
        assets.append({"image": {"url": pub_url}})
    elif media_type == "video":
        assets.append({"video": {"url": pub_url, "metadata": {"thumbnailOffset": 2000}}})

    # 7. Build Platform Metadata (e.g. Instagram Reels vs Post)
    metadata: dict[str, Any] | None = None
    if plat == "instagram":
        ig_type = "reel" if media_type == "video" else "post"
        metadata = {
            "instagram": {
                "type": ig_type,
                "shouldShareToFeed": True,
            }
        }

    # 8. Resolve Buffer Channel ID
    channel_id = get_channel_id(plat)

    # 9. Record Publication Started
    pub_id = str(uuid4())
    try:
        db.execute(
            """
            INSERT INTO campaign_publications
            (id, campaign_id, platform, provider, status, published_content, media_id)
            VALUES (%s, %s, %s, 'buffer', 'publishing', %s, %s)
            """,
            (pub_id, campaign_id, plat, text, media_id),
        )
    except Exception:
        db.execute(
            """
            INSERT INTO campaign_publications
            (id, campaign_id, platform, status, published_content, media_id)
            VALUES (%s, %s, %s, 'publishing', %s, %s)
            """,
            (pub_id, campaign_id, plat, text, media_id),
        )

    # 10. Dispatch Post to Buffer GraphQL API
    publish_mode = os.getenv("BUFFER_PUBLISH_MODE", "addToQueue")

    try:
        buffer_result = create_buffer_post(
            channel_id=channel_id,
            text=text,
            mode=publish_mode,
            assets=assets if assets else None,
            metadata=metadata,
        )
        post_id = buffer_result["post_id"]
        external_url = "https://publish.buffer.com"

        # Update publication record to published
        try:
            db.execute(
                """
                UPDATE campaign_publications
                SET status = 'published',
                    buffer_post_id = %s,
                    external_post_id = %s,
                    external_post_url = %s,
                    published_at = %s,
                    error_message = NULL
                WHERE id = %s
                """,
                (post_id, post_id, external_url, datetime.now(timezone.utc), pub_id),
            )
        except Exception:
            db.execute(
                """
                UPDATE campaign_publications
                SET status = 'published',
                    external_post_id = %s,
                    external_post_url = %s,
                    published_at = %s,
                    error_message = NULL
                WHERE id = %s
                """,
                (post_id, external_url, datetime.now(timezone.utc), pub_id),
            )

        # Mark campaign as published
        db.execute(
            "UPDATE campaigns SET status = 'published' WHERE id = %s",
            (campaign_id,),
        )

        # Audit Event Logging
        log_event(
            db,
            campaign_id=campaign_id,
            event_type="published",
            description=f"Published to {plat.upper() if plat == 'x' else plat.title()} via Buffer (Post ID: {post_id})",
            metadata={
                "platform": plat,
                "provider": "buffer",
                "buffer_post_id": post_id,
                "media_id": media_id,
                "media_url": pub_url,
                "mode": publish_mode,
            },
        )

        return {
            "success": True,
            "campaign_id": campaign_id,
            "publication_id": pub_id,
            "post_id": post_id,
            "external_post_id": post_id,
            "platform": plat,
            "status": "published",
            "external_post_url": external_url,
            "message": f"Successfully published to {plat.upper() if plat == 'x' else plat.title()} via Buffer!",
            "published_at": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as exc:
        err_msg = str(exc)
        logger.error(f"Publishing to {plat} failed: {err_msg}")

        # Update publication record to failed
        try:
            db.execute(
                """
                UPDATE campaign_publications
                SET status = 'failed',
                    error_message = %s
                WHERE id = %s
                """,
                (err_msg, pub_id),
            )
        except Exception:
            pass

        # Audit Event Logging
        try:
            log_event(
                db,
                campaign_id=campaign_id,
                event_type="publication_failed",
                description=f"Publishing to {plat.upper() if plat == 'x' else plat.title()} failed: {err_msg}",
                metadata={
                    "platform": plat,
                    "provider": "buffer",
                    "error": err_msg,
                },
            )
        except Exception:
            pass

        raise
