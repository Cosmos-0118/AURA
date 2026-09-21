from fastapi import APIRouter

try:
    from ..db import get_connection
    from ..schemas import BrandId, Lesson
except ImportError:
    from db import get_connection
    from schemas import BrandId, Lesson

router = APIRouter(prefix="/api/lessons", tags=["lessons"])


@router.get("", response_model=list[Lesson])
def list_lessons(brand_id: BrandId | None = None) -> list[Lesson]:
    query = "select id, brand_id, platform, reason_tag, note, original_body, edited_body, created_at from lessons"
    params: tuple[str, ...] = ()
    if brand_id:
        query += " where brand_id = %s"
        params = (brand_id,)
    query += " order by created_at desc"
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [
        Lesson(
            id=str(row["id"]),
            brand_id=row["brand_id"],
            platform=row["platform"],
            reason_tag=row["reason_tag"],
            note=row["note"],
            original_body=row["original_body"],
            edited_body=row["edited_body"],
            created_at=row["created_at"],
        )
        for row in rows
    ]
