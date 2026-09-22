from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Callable
from contextlib import closing
from pathlib import Path
from typing import Any

from .models import ChangeEvent, Competitor, Snapshot


class Store:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _init_db(self) -> None:
        with closing(self._connect()) as connection, connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS competitors (
                    id TEXT PRIMARY KEY,
                    brand_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    niche TEXT NOT NULL,
                    countries TEXT NOT NULL,
                    url TEXT NOT NULL,
                    priority TEXT NOT NULL DEFAULT 'medium',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS snapshots (
                    id TEXT PRIMARY KEY,
                    competitor_id TEXT NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
                    content_hash TEXT NOT NULL,
                    content TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_key TEXT NOT NULL DEFAULT '',
                    source_url TEXT,
                    market TEXT,
                    change_summary TEXT,
                    scraped_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_snapshots_competitor_time
                    ON snapshots(competitor_id, scraped_at DESC);
                CREATE TABLE IF NOT EXISTS events (
                    id TEXT PRIMARY KEY,
                    competitor_id TEXT NOT NULL REFERENCES competitors(id) ON DELETE CASCADE,
                    brand_id TEXT NOT NULL,
                    country TEXT,
                    change_type TEXT NOT NULL,
                    impact TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_url TEXT,
                    summary TEXT NOT NULL,
                    previous_value TEXT,
                    current_value TEXT,
                    why_it_matters TEXT NOT NULL,
                    recommended_action TEXT NOT NULL,
                    evidence TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    event_key TEXT,
                    detected_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_detected
                    ON events(detected_at DESC);
                """
            )
            connection.execute("BEGIN IMMEDIATE")
            self._ensure_column(connection, "snapshots", "source_key", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "snapshots", "source_url", "TEXT")
            self._ensure_column(connection, "snapshots", "market", "TEXT")
            self._ensure_column(connection, "events", "source_url", "TEXT")
            self._ensure_column(connection, "events", "event_key", "TEXT")
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_snapshots_stream_time
                    ON snapshots(competitor_id, source_key, scraped_at DESC)
                """
            )
            connection.execute(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_events_dedup
                    ON events(competitor_id, event_key)
                """
            )
            self._migrate_snapshot_streams(connection)
            connection.commit()

    @staticmethod
    def _ensure_column(
        connection: sqlite3.Connection, table: str, column: str, definition: str
    ) -> None:
        cursor = connection.execute(f"PRAGMA table_info({table})")
        try:
            columns = {row[1] for row in cursor}
        finally:
            cursor.close()
        if column not in columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def upsert_competitor(self, competitor: Competitor) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO competitors(id, brand_id, name, niche, countries, url, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    brand_id = excluded.brand_id,
                    name = excluded.name,
                    niche = excluded.niche,
                    countries = excluded.countries,
                    url = excluded.url,
                    priority = excluded.priority
                """,
                (
                    competitor.id,
                    competitor.brand_id,
                    competitor.name,
                    competitor.niche,
                    json.dumps(competitor.countries),
                    competitor.url,
                    competitor.priority,
                ),
            )

    def list_competitors(self) -> list[Competitor]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute("SELECT * FROM competitors ORDER BY priority, name").fetchall()
        return [self._competitor_from_row(row) for row in rows]

    def get_competitor(self, competitor_id: str) -> Competitor | None:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                "SELECT * FROM competitors WHERE id = ?", (competitor_id,)
            ).fetchone()
        return self._competitor_from_row(row) if row else None

    def find_competitor_by_url(self, url: str) -> Competitor | None:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute("SELECT * FROM competitors").fetchall()
        wanted = self.canonical_url(url)
        row = next((candidate for candidate in rows if self.canonical_url(candidate["url"]) == wanted), None)
        return self._competitor_from_row(row) if row else None

    @staticmethod
    def canonical_url(url: str) -> str:
        from urllib.parse import urlsplit, urlunsplit

        parsed = urlsplit(url.strip())
        path = parsed.path.rstrip("/") or "/"
        return urlunsplit((parsed.scheme.lower(), parsed.netloc.lower(), path, parsed.query, ""))

    def _migrate_snapshot_streams(self, connection: sqlite3.Connection) -> None:
        rows = connection.execute(
            """
            SELECT s.id, s.source, s.source_url, s.source_key, c.url AS competitor_url
            FROM snapshots s
            LEFT JOIN competitors c ON c.id = s.competitor_id
            WHERE s.source_key IS NULL OR s.source_key = ''
            """
        ).fetchall()
        for row in rows:
            identity = row["source_url"] or row["competitor_url"] or "legacy"
            if row["source"] in {"website", "changedetection"}:
                identity = self.canonical_url(identity)
            source_key = f"{row['source']}:{identity}"
            connection.execute(
                "UPDATE snapshots SET source_key = ? WHERE id = ?",
                (source_key, row["id"]),
            )

    def latest_snapshot(self, competitor_id: str, source_key: str | None = None) -> Snapshot | None:
        with closing(self._connect()) as connection, connection:
            if source_key:
                row = connection.execute(
                    """
                    SELECT * FROM snapshots
                    WHERE competitor_id = ? AND source_key = ?
                    ORDER BY scraped_at DESC
                    LIMIT 1
                    """,
                    (competitor_id, source_key),
                ).fetchone()
            else:
                row = connection.execute(
                    """
                    SELECT * FROM snapshots
                    WHERE competitor_id = ?
                    ORDER BY scraped_at DESC
                    LIMIT 1
                    """,
                    (competitor_id,),
                ).fetchone()
        return self._snapshot_from_row(row) if row else None

    def add_snapshot(self, snapshot: Snapshot) -> None:
        with closing(self._connect()) as connection, connection:
            latest = connection.execute(
                """
                SELECT id, content_hash FROM snapshots
                WHERE competitor_id = ? AND source_key = ?
                ORDER BY scraped_at DESC
                LIMIT 1
                """,
                (snapshot.competitor_id, snapshot.source_key),
            ).fetchone()
            if latest and latest["content_hash"] == snapshot.content_hash:
                connection.execute(
                    """
                    UPDATE snapshots
                    SET source_url = ?, market = ?, change_summary = ?, scraped_at = ?
                    WHERE id = ?
                    """,
                    (
                        snapshot.source_url,
                        snapshot.market,
                        snapshot.change_summary,
                        snapshot.scraped_at,
                        latest["id"],
                    ),
                )
                return
            connection.execute(
                """
                INSERT INTO snapshots(id, competitor_id, content_hash, content, source,
                                      source_key, source_url, market, change_summary, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.id,
                    snapshot.competitor_id,
                    snapshot.content_hash,
                    snapshot.content,
                    snapshot.source,
                    snapshot.source_key,
                    snapshot.source_url,
                    snapshot.market,
                    snapshot.change_summary,
                    snapshot.scraped_at,
                ),
            )

    def record_scan(
        self,
        snapshot: Snapshot,
        event_factory: Callable[[Snapshot | None], ChangeEvent | None],
    ) -> tuple[Snapshot | None, bool, str | None]:
        """Compare and persist one source stream in a single SQLite transaction."""
        with closing(self._connect()) as connection, connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT * FROM snapshots
                WHERE competitor_id = ? AND source_key = ?
                ORDER BY scraped_at DESC
                LIMIT 1
                """,
                (snapshot.competitor_id, snapshot.source_key),
            ).fetchone()
            previous = self._snapshot_from_row(row) if row else None
            if previous and previous.content_hash == snapshot.content_hash:
                connection.execute(
                    """
                    UPDATE snapshots
                    SET source_url = ?, market = ?, change_summary = ?, scraped_at = ?
                    WHERE id = ?
                    """,
                    (
                        snapshot.source_url,
                        snapshot.market,
                        snapshot.change_summary,
                        snapshot.scraped_at,
                        previous.id,
                    ),
                )
                connection.commit()
                return previous, False, None

            event = event_factory(previous)
            event_id = None
            if event:
                event_key = self._deduplicated_event_key(connection, event, snapshot, previous)
                connection.execute(
                    """
                    INSERT OR IGNORE INTO events(
                        id, competitor_id, brand_id, country, change_type, impact, source,
                        source_url, summary, previous_value, current_value, why_it_matters,
                        recommended_action, evidence, confidence, event_key, detected_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    self._event_values(event, event_key),
                )
                event_id = event.id if connection.execute("SELECT changes()").fetchone()[0] else None
                if event_id is None:
                    duplicate = connection.execute(
                        "SELECT id FROM events WHERE competitor_id = ? AND event_key = ?",
                        (event.competitor_id, event_key),
                    ).fetchone()
                    event_id = duplicate["id"] if duplicate else None
            connection.execute(
                """
                INSERT INTO snapshots(id, competitor_id, content_hash, content, source,
                                      source_key, source_url, market, change_summary, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.id,
                    snapshot.competitor_id,
                    snapshot.content_hash,
                    snapshot.content,
                    snapshot.source,
                    snapshot.source_key,
                    snapshot.source_url,
                    snapshot.market,
                    snapshot.change_summary,
                    snapshot.scraped_at,
                ),
            )
            connection.commit()
            return previous, event is not None, event_id

    def add_event(self, event: ChangeEvent) -> None:
        with closing(self._connect()) as connection, connection:
            connection.execute(
                """
                INSERT INTO events(
                    id, competitor_id, brand_id, country, change_type, impact, source,
                    source_url, summary, previous_value, current_value, why_it_matters,
                    recommended_action, evidence, confidence, event_key, detected_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                self._event_values(event, None),
            )

    @classmethod
    def _event_base_key(
        cls, event: ChangeEvent, snapshot: Snapshot, previous: Snapshot | None
    ) -> str:
        source_url = cls.canonical_url(event.source_url or snapshot.source_url or snapshot.source_key)
        previous_hash = previous.content_hash if previous else "baseline"
        return f"{event.competitor_id}:{source_url}:{previous_hash}:{snapshot.content_hash}"

    @classmethod
    def _deduplicated_event_key(
        cls,
        connection: sqlite3.Connection,
        event: ChangeEvent,
        snapshot: Snapshot,
        previous: Snapshot | None,
    ) -> str:
        source_url = cls.canonical_url(event.source_url or snapshot.source_url or snapshot.source_key)
        base_key = cls._event_base_key(event, snapshot, previous)
        rows = connection.execute(
            """
            SELECT event_key, detected_at
            FROM events
            WHERE competitor_id = ? AND source_url = ? AND event_key IS NOT NULL
            ORDER BY detected_at DESC
            """,
            (event.competitor_id, source_url),
        ).fetchall()
        candidates = [row for row in rows if row["event_key"].startswith(f"{base_key}:")]
        if not candidates:
            return f"{base_key}:1"

        latest = candidates[0]
        intervening = connection.execute(
            """
            SELECT 1 FROM snapshots
            WHERE competitor_id = ? AND source_url = ?
              AND content_hash != ? AND scraped_at > ?
            LIMIT 1
            """,
            (event.competitor_id, source_url, snapshot.content_hash, latest["detected_at"]),
        ).fetchone()
        if not intervening:
            return latest["event_key"]

        occurrences = []
        for row in candidates:
            try:
                occurrences.append(int(row["event_key"].rsplit(":", 1)[1]))
            except (ValueError, IndexError):
                continue
        return f"{base_key}:{max(occurrences, default=0) + 1}"

    @staticmethod
    def _event_values(event: ChangeEvent, event_key: str | None) -> tuple[Any, ...]:
        return (
            event.id,
            event.competitor_id,
            event.brand_id,
            event.country,
            event.change_type,
            event.impact,
            event.source,
            event.source_url,
            event.summary,
            event.previous_value,
            event.current_value,
            event.why_it_matters,
            event.recommended_action,
            event.evidence,
            event.confidence,
            event_key,
            event.detected_at,
        )

    def list_events(self, filters: dict[str, str] | None = None, limit: int = 200) -> list[ChangeEvent]:
        filters = filters or {}
        clauses: list[str] = []
        values: list[Any] = []
        for field in ("brand_id", "country", "impact", "change_type", "source"):
            value = filters.get(field)
            if value:
                clauses.append(f"{field} = ?")
                values.append(value)
        search = filters.get("search", "").strip()
        if search:
            clauses.append("(e.competitor_id LIKE ? OR c.name LIKE ? OR e.summary LIKE ? OR e.evidence LIKE ?)")
            wildcard = f"%{search}%"
            values.extend([wildcard, wildcard, wildcard, wildcard])
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        values.append(max(1, min(limit, 500)))
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                f"SELECT e.* FROM events e JOIN competitors c ON c.id = e.competitor_id {where} ORDER BY e.detected_at DESC LIMIT ?", values
            ).fetchall()
        return [self._event_from_row(row) for row in rows]

    def monitor_status(self) -> list[dict[str, Any]]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                """
                SELECT
                    c.id AS competitor_id,
                    c.name AS competitor_name,
                    c.brand_id,
                    c.priority,
                    s.source,
                    s.source_url,
                    s.market,
                    s.source_key,
                    s.scraped_at AS last_checked,
                    s.content_hash AS latest_hash,
                    s.change_summary,
                    (SELECT COUNT(*) FROM snapshots sx WHERE sx.competitor_id = c.id AND sx.source_key = s.source_key) AS snapshots,
                    (SELECT COUNT(DISTINCT sx.content_hash) FROM snapshots sx WHERE sx.competitor_id = c.id AND sx.source_key = s.source_key) AS versions,
                    CASE WHEN s.id IS NULL THEN 'not_checked' ELSE 'active' END AS status
                FROM competitors c
                LEFT JOIN snapshots s ON s.id = (
                    SELECT sx.id FROM snapshots sx
                    WHERE sx.competitor_id = c.id
                    ORDER BY sx.scraped_at DESC
                    LIMIT 1
                )
                ORDER BY c.priority, c.name
                """
            ).fetchall()
        return [dict(row) for row in rows]

    def source_competitor_counts(self) -> dict[str, int]:
        with closing(self._connect()) as connection, connection:
            rows = connection.execute(
                "SELECT source, COUNT(DISTINCT competitor_id) AS competitors FROM snapshots GROUP BY source"
            ).fetchall()
        return {row["source"]: row["competitors"] for row in rows}

    def summary(self) -> dict[str, int]:
        with closing(self._connect()) as connection, connection:
            row = connection.execute(
                """
                SELECT
                    COUNT(*) AS total,
                    SUM(CASE WHEN impact = 'high' THEN 1 ELSE 0 END) AS high,
                    SUM(CASE WHEN impact = 'medium' THEN 1 ELSE 0 END) AS medium,
                    SUM(CASE WHEN impact = 'low' THEN 1 ELSE 0 END) AS low,
                    COUNT(DISTINCT competitor_id) AS competitors
                FROM events
                """
            ).fetchone()
            watchlist = connection.execute("SELECT COUNT(*) AS count FROM competitors").fetchone()["count"]
        return {
            "total": row["total"] or 0,
            "high": row["high"] or 0,
            "medium": row["medium"] or 0,
            "low": row["low"] or 0,
            "competitors": watchlist or 0,
        }

    def _competitor_from_row(self, row: sqlite3.Row) -> Competitor:
        return Competitor(
            id=row["id"],
            brand_id=row["brand_id"],
            name=row["name"],
            niche=row["niche"],
            countries=json.loads(row["countries"]),
            url=row["url"],
            priority=row["priority"],
        )

    def _snapshot_from_row(self, row: sqlite3.Row) -> Snapshot:
        return Snapshot(
            id=row["id"],
            competitor_id=row["competitor_id"],
            content_hash=row["content_hash"],
            content=row["content"],
            source=row["source"],
            source_key=row["source_key"],
            source_url=row["source_url"],
            market=row["market"],
            scraped_at=row["scraped_at"],
            change_summary=row["change_summary"],
        )

    def _event_from_row(self, row: sqlite3.Row) -> ChangeEvent:
        return ChangeEvent(
            id=row["id"],
            competitor_id=row["competitor_id"],
            brand_id=row["brand_id"],
            country=row["country"],
            change_type=row["change_type"],
            impact=row["impact"],
            source=row["source"],
            source_url=row["source_url"],
            summary=row["summary"],
            previous_value=row["previous_value"],
            current_value=row["current_value"],
            why_it_matters=row["why_it_matters"],
            recommended_action=row["recommended_action"],
            evidence=row["evidence"],
            confidence=row["confidence"],
            detected_at=row["detected_at"],
        )


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex}"
