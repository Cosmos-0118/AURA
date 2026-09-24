"""Compatibility facade for AURA's Overture-backed lead pipeline."""

from __future__ import annotations

import threading

try:
    from . import lead_pipeline
except ImportError:
    import lead_pipeline  # type: ignore[no-redef]

def key_configured() -> bool:
    """Overture Places is a public dataset and needs no API key."""
    return True


def refresh_status() -> dict:
    return lead_pipeline.get_status()


def load_lead_page(
    *,
    brand_id: str | None = None,
    search: str | None = None,
    contact: str = "all",
    sort: str = "fit",
    limit: int = 40,
    cursor: str | None = None,
) -> dict:
    """Load one bounded keyset page from the lead database."""
    return lead_pipeline.list_lead_page(
        brand_id=brand_id, search=search, contact=contact, sort=sort, limit=limit, cursor=cursor
    )


def refresh_leads(*, claim: bool = True) -> dict:
    del claim  # Pipeline-level lock protects manual and scheduled refreshes alike.
    return lead_pipeline.refresh()


def start_daily_refresh() -> None:
    """Start the pipeline's retry-aware discovery and enrichment workers."""
    lead_pipeline.start_scheduler()


def start_refresh_in_background() -> dict:
    state = refresh_status()
    if state.get("refreshing"):
        return state
    thread = threading.Thread(
        target=lead_pipeline._manual_refresh_task,
        name="aura-lead-refresh-once",
        daemon=True,
    )
    thread.start()
    return refresh_status()
