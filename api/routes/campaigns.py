from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, HTTPException
from psycopg.types.json import Json

try:
    from ..db import get_connection
    from ..graph import run_pipeline
    from ..schemas import BrandId, Campaign, CampaignCreate
except ImportError:
    from db import get_connection
    from graph import run_pipeline
    from schemas import BrandId, Campaign, CampaignCreate

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


def _campaign(row: dict) -> Campaign:
    return Campaign(**{**row, "id": str(row["id"])})


@router.post("", response_model=Campaign)
def create_campaign(body: CampaignCreate, background_tasks: BackgroundTasks) -> Campaign:
    campaign_id = str(uuid4())
    with get_connection() as connection:
        row = connection.execute(
            """
            insert into campaigns
              (id, brand_id, topic, country, goal, platforms, language, status)
            values (%s, %s, %s, %s, %s, %s, %s, 'running')
            returning *
            """,
            (
                campaign_id,
                body.brand_id,
                body.topic,
                body.country,
                body.goal,
                Json(body.platforms),
                body.language,
            ),
        ).fetchone()
    background_tasks.add_task(run_pipeline, campaign_id)
    return _campaign(row)


@router.get("", response_model=list[Campaign])
def list_campaigns(brand_id: BrandId | None = None) -> list[Campaign]:
    query = "select * from campaigns"
    params: tuple[str, ...] = ()
    if brand_id:
        query += " where brand_id = %s"
        params = (brand_id,)
    query += " order by created_at desc"
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [_campaign(row) for row in rows]


@router.get("/{campaign_id}", response_model=Campaign)
def get_campaign(campaign_id: str) -> Campaign:
    with get_connection() as connection:
        row = connection.execute(
            "select * from campaigns where id = %s", (campaign_id,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return _campaign(row)
