"""In-process competitor intelligence runtime for the AURA API.

The existing collector package remains the source of the monitoring and
classification logic. AURA owns its service instance and points the package's
SQLite store at the shared AURA database so the dashboard and collectors use
one local data store and one HTTP process.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from contextlib import closing
from functools import lru_cache
from pathlib import Path
import sys
import threading
import time
from typing import Any

try:
    from ..db import SQLITE_DB_PATH
except ImportError:  # Supports `cd api && uv run uvicorn main:app`.
    from db import SQLITE_DB_PATH  # type: ignore[no-redef]

logger = logging.getLogger("aura.competitor_intelligence")

_MODULE_ROOT = Path(__file__).resolve().parents[2] / "competitor-intelligence"
if str(_MODULE_ROOT) not in sys.path:
    sys.path.insert(0, str(_MODULE_ROOT))

from competitor_intelligence.service import IntelligenceService  # noqa: E402
from competitor_intelligence.store import Store  # noqa: E402


def _migrate_legacy_sqlite(source: Path, target: Path) -> int:
    """Import rows from the former standalone database into AURA's store.

    The import is deliberately idempotent and column-aware so it can handle
    databases created by older collector versions without overwriting rows
    already present in the AURA database.
    """

    if not source.exists():
        return 0
    try:
        if source.resolve() == target.resolve():
            return 0
    except OSError:
        return 0

    imported = 0
    tables = ("organizations", "competitors", "snapshots", "events", "source_cursors")
    with closing(sqlite3.connect(source)) as legacy, closing(sqlite3.connect(target)) as current:
        legacy.row_factory = sqlite3.Row
        current.execute("PRAGMA foreign_keys = ON")
        for table in tables:
            source_columns = {
                row[1]
                for row in legacy.execute(f"PRAGMA table_info({table})").fetchall()
            }
            target_columns = {
                row[1]
                for row in current.execute(f"PRAGMA table_info({table})").fetchall()
            }
            columns = [column for column in source_columns if column in target_columns]
            if not columns:
                continue
            column_sql = ", ".join(f'"{column}"' for column in columns)
            placeholders = ", ".join("?" for _ in columns)
            statement = f'INSERT OR IGNORE INTO "{table}" ({column_sql}) VALUES ({placeholders})'
            for row in legacy.execute(f'SELECT {column_sql} FROM "{table}"').fetchall():
                try:
                    cursor = current.execute(statement, tuple(row[column] for column in columns))
                except sqlite3.IntegrityError:
                    logger.warning("Skipped legacy %s row with missing dependencies", table)
                    continue
                imported += max(cursor.rowcount, 0)
        current.commit()
    if imported:
        logger.info("Imported %s rows from legacy competitor database %s", imported, source)
    return imported


@lru_cache(maxsize=1)
def get_intelligence_service() -> IntelligenceService:
    """Return the process-wide service backed by AURA's SQLite database."""

    if os.getenv("DB_ENGINE", "auto").lower() == "mysql":
        raise RuntimeError(
            "Competitor intelligence currently requires AURA's SQLite store; set DB_ENGINE=sqlite or auto."
        )
    configured_path = os.getenv("AURA_INTELLIGENCE_DB")
    database_path = Path(configured_path).expanduser() if configured_path else SQLITE_DB_PATH
    store = Store(database_path)
    legacy_path = Path(
        os.getenv("AURA_INTELLIGENCE_LEGACY_DB", str(_MODULE_ROOT / "data" / "intelligence.db"))
    ).expanduser()
    _migrate_legacy_sqlite(legacy_path, database_path)
    return IntelligenceService(store)


_worker_lock = threading.Lock()
_worker_thread: threading.Thread | None = None
_init_lock = threading.Lock()
_initialized = False


def _scan_interval() -> int:
    try:
        return max(60, int(os.getenv("AURA_COMPETITOR_SCAN_INTERVAL", "900")))
    except ValueError:
        return 900


def _run_worker() -> None:
    service = get_intelligence_service()
    while True:
        try:
            try:
                service.sync_changedetection()
            except Exception:
                logger.info("Changedetection sync unavailable", exc_info=True)

            for watch in service.due_watches():
                result = service.scan_watch(watch)
                if result.status == "error":
                    logger.warning("Competitor watch %s failed: %s", watch.id, result.error)

            try:
                service.poll_feeds()
            except Exception:
                logger.info("Competitor feed polling unavailable", exc_info=True)
        except Exception:
            logger.exception("Competitor intelligence worker iteration failed")
        time.sleep(_scan_interval())


def initialize_competitor_intelligence(*, force: bool = False) -> dict[str, Any]:
    """Ensure the shared store and competitor registry are loaded before serving UI.

    The dashboard used to race the first request against lazy singleton creation.
    Always warming the registry at startup (and again on demand) keeps the first
    paint from rendering an empty shell that only fills after a manual refresh.
    """

    global _initialized
    with _init_lock:
        if _initialized and not force:
            return competitor_readiness()
        service = get_intelligence_service()
        service.sync_registry()
        competitors = service.competitors()
        watches = service.watches()
        _initialized = True
        readiness = {
            "ready": True,
            "competitors": len(competitors),
            "watches": len(watches),
            "events": service.summary().get("total", 0),
        }
        logger.info(
            "Competitor intelligence ready (%s competitors, %s watches)",
            readiness["competitors"],
            readiness["watches"],
        )
        return readiness


def competitor_readiness() -> dict[str, Any]:
    """Return whether the registry has been loaded into AURA's store."""

    if not _initialized:
        return {"ready": False, "competitors": 0, "watches": 0, "events": 0}
    try:
        service = get_intelligence_service()
        summary = service.store.summary()
        return {
            "ready": True,
            "competitors": int(summary.get("relationships") or 0),
            "watches": len(service.watches()),
            "events": int(summary.get("total") or 0),
        }
    except Exception as exc:
        return {
            "ready": False,
            "competitors": 0,
            "watches": 0,
            "events": 0,
            "error": str(exc),
        }


def start_competitor_refresh() -> None:
    """Initialize the registry, then start the collector worker when enabled.

    Tests skip the network worker. Disabling refresh still warms the registry so
    `/api/competitors/dashboard` is not empty on the first request.
    """

    if os.getenv("PYTEST_CURRENT_TEST"):
        return

    try:
        initialize_competitor_intelligence()
    except Exception:
        logger.exception("Competitor intelligence failed to initialize on startup")
        return

    if os.getenv("AURA_COMPETITOR_REFRESH", "true").lower() in {"0", "false", "no"}:
        return

    global _worker_thread
    with _worker_lock:
        if _worker_thread is not None and _worker_thread.is_alive():
            return
        _worker_thread = threading.Thread(
            target=_run_worker,
            name="aura-competitor-refresh",
            daemon=True,
        )
        _worker_thread.start()


def reset_intelligence_service_cache() -> None:
    """Reset the singleton for isolated tests and local database switches."""

    global _worker_thread, _initialized
    get_intelligence_service.cache_clear()
    with _worker_lock:
        _worker_thread = None
    with _init_lock:
        _initialized = False


def service_payload(service: IntelligenceService) -> dict[str, Any]:
    """Build the complete native dashboard payload used by the web client."""

    initialize_competitor_intelligence()
    service.sync_registry()
    return {
        "summary": service.summary(),
        "competitors": [item.to_dict() for item in service.competitors()],
        "monitors": service.monitor_status(),
        "watches": service.watch_status(),
        "events": service.events(),
        "source_health": service.source_health(),
        "ready": True,
    }
