"""Lessons Repository for continuous feedback learning."""

from typing import Any
from uuid import uuid4


def list_lessons(
    db: Any,
    brand_id: str | None = None,
    platform: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Retrieve active lessons for a brand and/or platform to inject as negative guidance."""
    query = "SELECT * FROM lessons"
    params = []
    clauses = []

    if brand_id:
        clauses.append("(brand_id = %s OR brand_id IS NULL)")
        params.append(brand_id)
    if platform:
        clauses.append("(platform = %s OR platform IS NULL)")
        params.append(platform)

    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    query += " ORDER BY created_at DESC LIMIT %s"
    params.append(limit)

    return db.execute(query, tuple(params)).fetchall()


def create_lesson(
    db: Any,
    brand_id: str | None,
    platform: str | None,
    tag: str,
    note: str,
    original_content: str | None = None,
    corrected_content: str | None = None,
    source_campaign_id: str | None = None,
    lesson_id: str | None = None,
) -> str:
    """Record a new learned lesson from reviewer feedback."""
    lid = lesson_id or str(uuid4())
    db.execute(
        """
        INSERT INTO lessons
            (id, brand_id, platform, tag, note, original_content, corrected_content, source_campaign_id)
        VALUES
            (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (lid, brand_id, platform, tag, note, original_content, corrected_content, source_campaign_id),
    )
    return lid
