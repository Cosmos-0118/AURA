"""Compatibility facade for AURA's Overture-backed lead pipeline."""

from __future__ import annotations

import logging
import os
import threading
import time

try:
    from . import lead_pipeline
except ImportError:
    import lead_pipeline  # type: ignore[no-redef]

logger = logging.getLogger("aura.lead_intel")
REFRESH_HOURS = int(os.getenv("LEAD_REFRESH_HOURS", "720"))
_START_LOCK = threading.Lock()
_STARTED = False


def key_configured() -> bool:
    """Overture Places is a public dataset and needs no API key."""
    return True


def refresh_status() -> dict:
    return lead_pipeline.get_status()


def load_scraped_leads(brand_id: str | None = None) -> list[dict]:
    """Legacy name retained for API callers; lead rows now come from the database."""
    return lead_pipeline.list_leads(brand_id)


def refresh_leads(*, claim: bool = True) -> dict:
    del claim  # Pipeline-level lock protects manual and scheduled refreshes alike.
    return lead_pipeline.refresh()


def _is_stale() -> bool:
    return lead_pipeline._is_stale()


def run_daily_loop() -> None:
    """Resume persisted jobs hourly and discover the latest release monthly."""
    while True:
        try:
            lead_pipeline.resume_pending_jobs()
            if _is_stale():
                refresh_leads()
        except Exception:
            logger.exception("Lead pipeline scheduler failed")
        time.sleep(60 * 60)


def start_daily_refresh() -> None:
    global _STARTED
    if os.getenv("AURA_LEAD_REFRESH", "true").lower() in {"0", "false", "no"}:
        return
    if os.getenv("PYTEST_CURRENT_TEST"):
        return
    with _START_LOCK:
        if _STARTED:
            return
        _STARTED = True
    threading.Thread(target=run_daily_loop, name="aura-lead-refresh", daemon=True).start()


def start_refresh_in_background() -> dict:
    state = refresh_status()
    if state.get("refreshing"):
        return state
    thread = threading.Thread(target=refresh_leads, name="aura-lead-refresh-once", daemon=True)
    thread.start()
    return refresh_status()
