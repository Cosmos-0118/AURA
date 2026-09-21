from fastapi import APIRouter, HTTPException

try:
    from ..db import get_connection
    from ..schemas import Brand, BrandId
except ImportError:
    from db import get_connection
    from schemas import Brand, BrandId

router = APIRouter(prefix="/api/brands", tags=["brands"])


def _brand(row: dict) -> Brand:
    return Brand(
        id=row["id"],
        name=row["name"],
        tone=row["tone"],
        audience=row["audience"],
        do_list=row["do_list"],
        dont_list=row["dont_list"],
    )


@router.get("", response_model=list[Brand])
def list_brands() -> list[Brand]:
    with get_connection() as connection:
        rows = connection.execute(
            "select id, name, tone, audience, do_list, dont_list from brands order by id"
        ).fetchall()
    return [_brand(row) for row in rows]


@router.get("/{brand_id}", response_model=Brand)
def get_brand(brand_id: BrandId) -> Brand:
    with get_connection() as connection:
        row = connection.execute(
            "select id, name, tone, audience, do_list, dont_list from brands where id = %s",
            (brand_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Brand not found")
    return _brand(row)
