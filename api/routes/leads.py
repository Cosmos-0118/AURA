from fastapi import APIRouter

try:
    from ..db import get_connection
    from ..schemas import BrandId, Lead
except ImportError:
    from db import get_connection
    from schemas import BrandId, Lead

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.get("", response_model=list[Lead])
def list_leads(brand_id: BrandId | None = None) -> list[Lead]:
    query = "select id, brand_id, name, url, country, fit_score, why from leads"
    params: tuple[str, ...] = ()
    if brand_id:
        query += " where brand_id = %s"
        params = (brand_id,)
    query += " order by fit_score desc, name"
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [
        Lead(
            id=str(row["id"]),
            brand_id=row["brand_id"],
            name=row["name"],
            url=row["url"],
            country=row["country"],
            fit_score=row["fit_score"],
            why=row["why"],
        )
        for row in rows
    ]
