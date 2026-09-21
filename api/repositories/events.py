"""Campaign Events Repository for audit logging."""

import json
from typing import Any
from uuid import uuid4


def log_event(
    db: Any,
    campaign_id: str,
    event_type: str,
    description: str | None = None,
    metadata: dict[str, Any] | list[Any] | None = None,
) -> str:
    """Log an audit event for a campaign."""
    event_id = str(uuid4())
    metadata_json = json.dumps(metadata) if metadata is not None else None
    db.execute(
        """
        INSERT INTO campaign_events
            (id, campaign_id, event_type, description, metadata)
        VALUES
            (%s, %s, %s, %s, %s)
        """,
        (event_id, campaign_id, event_type, description, metadata_json),
    )
    return event_id


def list_events_for_campaign(db: Any, campaign_id: str) -> list[dict[str, Any]]:
    """Retrieve audit history for a campaign."""
    rows = db.execute(
        """
        SELECT id, campaign_id, event_type, description, metadata, created_at
        FROM campaign_events
        WHERE campaign_id = %s
        ORDER BY created_at ASC
        """,
        (campaign_id,),
    ).fetchall()

    for r in rows:
        if isinstance(r.get("metadata"), str):
            try:
                r["metadata"] = json.loads(r["metadata"])
            except Exception:
                pass
    return rows
