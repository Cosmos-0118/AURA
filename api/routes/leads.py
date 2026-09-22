from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

try:
    from ..agents.lead_intel import key_configured, load_scraped_leads, refresh_status, start_refresh_in_background
    from ..agents.lead_mail import LeadMailError, draft_for, send_for
    from ..db import get_connection
    from ..schemas import BrandId, Lead
except ImportError:
    from agents.lead_intel import key_configured, load_scraped_leads, refresh_status, start_refresh_in_background
    from agents.lead_mail import LeadMailError, draft_for, send_for
    from db import get_connection
    from schemas import BrandId, Lead

router = APIRouter(prefix="/api/leads", tags=["leads"])


class LeadInsight(Lead):
    email: str | None = None
    phone: str | None = None
    requirements: str | None = None
    source_url: str | None = None
    source_title: str | None = None


def _insight(row: dict) -> LeadInsight:
    return LeadInsight(
        id=str(row["id"]),
        brand_id=row["brand_id"],
        name=row["name"],
        url=row.get("url"),
        country=row.get("country"),
        fit_score=row["fit_score"],
        why=row.get("why"),
        email=row.get("email"),
        phone=row.get("phone"),
        requirements=row.get("requirements"),
        source_url=row.get("source_url"),
        source_title=row.get("source_title"),
    )


@router.get("/status")
def lead_refresh_status() -> dict:
    return refresh_status()


@router.post("/refresh")
def lead_refresh() -> dict:
    return start_refresh_in_background()


class SendLeadEmail(BaseModel):
    lead_id: str = Field(min_length=1)


def _mail_error(exc: LeadMailError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=str(exc))


@router.get("/draft")
def lead_email_draft(lead_id: str) -> dict:
    try:
        return draft_for(lead_id)
    except LeadMailError as exc:
        raise _mail_error(exc) from exc


@router.post("/send")
def lead_email_send(body: SendLeadEmail) -> dict:
    try:
        return send_for(body.lead_id)
    except LeadMailError as exc:
        raise _mail_error(exc) from exc


@router.get("", response_model=list[LeadInsight])
def list_leads(brand_id: BrandId | None = None) -> list[LeadInsight]:
    if not key_configured():
        return []
    scraped = load_scraped_leads(brand_id)
    if scraped:
        return [_insight(row) for row in scraped]
    try:
        query = (
            "select id, brand_id, name, url, country, fit_score, why,"
            " email, phone, requirements, source_url, source_title from leads"
        )
        params: tuple[str, ...] = ()
        if brand_id:
            query += " where brand_id = %s"
            params = (brand_id,)
        query += " order by fit_score desc, name"
        with get_connection() as connection:
            rows = connection.execute(query, params).fetchall()
        return [_insight(row) for row in rows]
    except Exception:
        return []
