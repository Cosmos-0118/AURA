from __future__ import annotations

import json
import sqlite3
import uuid
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
        with self._connect() as connection:
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
                    summary TEXT NOT NULL,
                    previous_value TEXT,
                    current_value TEXT,
                    why_it_matters TEXT NOT NULL,
                    recommended_action TEXT NOT NULL,
                    evidence TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    detected_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_detected
                    ON events(detected_at DESC);
                """
            )

    def upsert_competitor(self, competitor: Competitor) -> None:
        with self._connect() as connection:
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
        with self._connect() as connection:
            rows = connection.execute("SELECT * FROM competitors ORDER BY priority, name").fetchall()
        return [self._competitor_from_row(row) for row in rows]

    def get_competitor(self, competitor_id: str) -> Competitor | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM competitors WHERE id = ?", (competitor_id,)
            ).fetchone()
        return self._competitor_from_row(row) if row else None

    def find_competitor_by_url(self, url: str) -> Competitor | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM competitors WHERE url = ?", (url,)
            ).fetchone()
        return self._competitor_from_row(row) if row else None

    def latest_snapshot(self, competitor_id: str) -> Snapshot | None:
        with self._connect() as connection:
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
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO snapshots(id, competitor_id, content_hash, content, source,
                                      change_summary, scraped_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    snapshot.id,
                    snapshot.competitor_id,
                    snapshot.content_hash,
                    snapshot.content,
                    snapshot.source,
                    snapshot.change_summary,
                    snapshot.scraped_at,
                ),
            )

    def add_event(self, event: ChangeEvent) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO events(
                    id, competitor_id, brand_id, country, change_type, impact, source,
                    summary, previous_value, current_value, why_it_matters,
                    recommended_action, evidence, confidence, detected_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.id,
                    event.competitor_id,
                    event.brand_id,
                    event.country,
                    event.change_type,
                    event.impact,
                    event.source,
                    event.summary,
                    event.previous_value,
                    event.current_value,
                    event.why_it_matters,
                    event.recommended_action,
                    event.evidence,
                    event.confidence,
                    event.detected_at,
                ),
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
        with self._connect() as connection:
            rows = connection.execute(
                f"SELECT e.* FROM events e JOIN competitors c ON c.id = e.competitor_id {where} ORDER BY e.detected_at DESC LIMIT ?", values
            ).fetchall()
        return [self._event_from_row(row) for row in rows]

    def summary(self) -> dict[str, int]:
        with self._connect() as connection:
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
