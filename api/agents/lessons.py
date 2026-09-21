"""Database-backed reviewer lessons used to improve later generations."""

from __future__ import annotations

try:
    from ..db import get_connection
except ImportError:  # Supports `cd api && uv run ...`.
    from db import get_connection


def get_relevant_lessons(brand_id: str, platform: str, limit: int = 5) -> list[str]:
    """Return newest relevant lesson notes, preferring the requested platform."""

    if limit <= 0:
        return []

    try:
        with get_connection() as connection:
            rows = connection.execute(
                """
                select note
                from lessons
                where brand_id = %s and (platform = %s or platform is null)
                order by case when platform = %s then 0 else 1 end, created_at desc
                limit %s
                """,
                (brand_id, platform, platform, limit),
            ).fetchall()
        return [row["note"] for row in rows]
    except Exception:
        # Lesson retrieval is advisory; generation must continue if the DB is
        # unavailable or the lessons table is temporarily inaccessible.
        return []


def record_lesson(
    asset_id: str,
    reason_tag: str,
    note: str,
    original: str,
    edited: str | None,
    brand_id: str,
    platform: str | None = None,
) -> None:
    """Persist a reviewer correction using a parameterized insert.

    Write errors intentionally propagate so the owning route can surface its
    fallback/error handling instead of silently claiming that learning worked.
    """

    safe_reason_tag = reason_tag or "OTHER"
    safe_note = note or reason_tag or "Reviewer correction"
    with get_connection() as connection:
        connection.execute(
            """
            insert into lessons
              (brand_id, platform, reason_tag, note, original_body, edited_body, asset_id)
            values (%s, %s, %s, %s, %s, %s, %s)
            """,
            (brand_id, platform, safe_reason_tag, safe_note, original, edited, asset_id),
        )
