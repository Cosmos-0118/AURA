"""Repository for campaign_publications table tracking multi-platform publish actions."""

from typing import Any
from uuid import uuid4

try:
    from .events import log_event
except ImportError:
    from repositories.events import log_event


def record_publication_started(
    db: Any,
    campaign_id: str,
    platform: str,
    media_id: str | None = None,
    published_content: str | None = None,
    publication_id: str | None = None,
) -> dict[str, Any]:
    """Record an in-progress publication attempt for a specific platform."""
    pub_id = publication_id or str(uuid4())

    existing = db.execute(
        "SELECT id FROM campaign_publications WHERE campaign_id = %s AND platform = %s",
        (campaign_id, platform),
    ).fetchone()

    if existing:
        db.execute(
            """
            UPDATE campaign_publications
            SET status = 'publishing', media_id = %s, published_content = %s, error_message = NULL, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (media_id, published_content, existing["id"]),
        )
        pub_id = str(existing["id"])
    else:
        db.execute(
            """
            INSERT INTO campaign_publications
                (id, campaign_id, platform, status, media_id, published_content)
            VALUES
                (%s, %s, %s, 'publishing', %s, %s)
            """,
            (pub_id, campaign_id, platform, media_id, published_content),
        )

    log_event(
        db,
        campaign_id=campaign_id,
        event_type="publication_started",
        description=f"Initiated publication dispatch to {platform.upper()}",
        metadata={"platform": platform, "media_id": media_id},
    )

    return db.execute("SELECT * FROM campaign_publications WHERE id = %s", (pub_id,)).fetchone()


def record_publication_success(
    db: Any,
    campaign_id: str,
    platform: str,
    external_post_id: str,
    external_post_url: str,
    media_id: str | None = None,
    published_content: str | None = None,
) -> dict[str, Any]:
    """Mark publication attempt as successful with external post URL and ID."""
    existing = db.execute(
        "SELECT id FROM campaign_publications WHERE campaign_id = %s AND platform = %s",
        (campaign_id, platform),
    ).fetchone()

    pub_id = str(existing["id"]) if existing else str(uuid4())

    if existing:
        db.execute(
            """
            UPDATE campaign_publications
            SET
                status = 'published',
                external_post_id = %s,
                external_post_url = %s,
                published_at = CURRENT_TIMESTAMP,
                error_message = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (external_post_id, external_post_url, pub_id),
        )
    else:
        db.execute(
            """
            INSERT INTO campaign_publications
                (id, campaign_id, platform, status, external_post_id, external_post_url, media_id, published_content, published_at)
            VALUES
                (%s, %s, %s, 'published', %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """,
            (pub_id, campaign_id, platform, external_post_id, external_post_url, media_id, published_content),
        )

    log_event(
        db,
        campaign_id=campaign_id,
        event_type="published",
        description=f"Successfully published to {platform.upper()}",
        metadata={
            "platform": platform,
            "external_post_id": external_post_id,
            "external_post_url": external_post_url,
        },
    )

    return db.execute("SELECT * FROM campaign_publications WHERE id = %s", (pub_id,)).fetchone()


def record_publication_failed(
    db: Any,
    campaign_id: str,
    platform: str,
    error_message: str,
) -> dict[str, Any]:
    """Mark publication attempt as failed."""
    existing = db.execute(
        "SELECT id FROM campaign_publications WHERE campaign_id = %s AND platform = %s",
        (campaign_id, platform),
    ).fetchone()

    pub_id = str(existing["id"]) if existing else str(uuid4())

    if existing:
        db.execute(
            """
            UPDATE campaign_publications
            SET status = 'failed', error_message = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (error_message, pub_id),
        )
    else:
        db.execute(
            """
            INSERT INTO campaign_publications
                (id, campaign_id, platform, status, error_message)
            VALUES
                (%s, %s, %s, 'failed', %s)
            """,
            (pub_id, campaign_id, platform, error_message),
        )

    log_event(
        db,
        campaign_id=campaign_id,
        event_type="publication_failed",
        description=f"Publication to {platform.upper()} failed: {error_message}",
        metadata={"platform": platform, "error": error_message},
    )

    return db.execute("SELECT * FROM campaign_publications WHERE id = %s", (pub_id,)).fetchone()


def get_campaign_publications(db: Any, campaign_id: str) -> list[dict[str, Any]]:
    """Fetch all publication records for a given campaign."""
    rows = db.execute(
        "SELECT * FROM campaign_publications WHERE campaign_id = %s ORDER BY created_at ASC",
        (campaign_id,),
    ).fetchall()
    return rows or []
