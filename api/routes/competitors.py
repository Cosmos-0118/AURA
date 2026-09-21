from fastapi import APIRouter, HTTPException

try:
    from ..db import get_connection
    from ..schemas import BrandId, Competitor, Snapshot
except ImportError:
    from db import get_connection
    from schemas import BrandId, Competitor, Snapshot

router = APIRouter(prefix="/api/competitors", tags=["competitors"])


@router.get("", response_model=list[Competitor])
def list_competitors(brand_id: BrandId | None = None) -> list[Competitor]:
    query = "select id, brand_id, name, url from competitors"
    params: tuple[str, ...] = ()
    if brand_id:
        query += " where brand_id = %s"
        params = (brand_id,)
    query += " order by name"
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [Competitor(id=str(row["id"]), brand_id=row["brand_id"], name=row["name"], url=row["url"]) for row in rows]


@router.post("/{competitor_id}/scan", response_model=Snapshot)
def scan_competitor(competitor_id: str) -> Snapshot:
    raise HTTPException(status_code=501, detail="not in this sprint")
