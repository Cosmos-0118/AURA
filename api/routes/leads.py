from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

try:
    from ..agents.lead_pipeline import add_suppression, lead_details, review_lead
    from ..agents.lead_intel import key_configured, load_lead_page, refresh_status, start_refresh_in_background
    from ..agents.lead_mail import LeadMailError, draft_for, send_for
    from ..db import get_connection
    from ..schemas import BrandId, Lead, LeadContact, LeadEvidence, LeadLocation, LeadReviewRequest, LeadSuppressionRequest
except ImportError:
    from agents.lead_pipeline import add_suppression, lead_details, review_lead
    from agents.lead_intel import key_configured, load_lead_page, refresh_status, start_refresh_in_background
    from agents.lead_mail import LeadMailError, draft_for, send_for
    from db import get_connection
    from schemas import BrandId, Lead, LeadContact, LeadEvidence, LeadLocation, LeadReviewRequest, LeadSuppressionRequest

router = APIRouter(prefix="/api/leads", tags=["leads"])


class LeadInsight(Lead):
    email: str | None = None
    requirements: str | None = None
    source_url: str | None = None
    source_title: str | None = None
    locations: list[LeadLocation] = Field(default_factory=list)
    contacts: list[LeadContact] = Field(default_factory=list)
    evidence: list[LeadEvidence] = Field(default_factory=list)
    score_history: list[dict] = Field(default_factory=list)


class LeadPage(BaseModel):
    items: list[LeadInsight]
    next_cursor: str | None = None
    has_more: bool
    limit: int


def _insight(row: dict) -> LeadInsight:
    return LeadInsight(
        id=str(row["id"]), brand_id=row["brand_id"], name=row["name"], url=row.get("url"),
        country=row.get("country"), fit_score=int(row.get("fit_score") or 0), why=row.get("why"),
        email=row.get("email") or row.get("public_email"), phone=row.get("phone"),
        requirements=row.get("requirements"), source_url=row.get("source_url") or "", source_title=row.get("source_title"),
        category=row.get("category") or "Unknown", location=row.get("location") or "Unknown",
        public_email=row.get("public_email") or row.get("email"), social_links=row.get("social_links") or [],
        description=row.get("description"), services=row.get("services") or [], source=row.get("source") or "unknown",
        status=row.get("status") or "new", external_place_id=row.get("external_place_id"),
        domain=row.get("domain"), operating_status=row.get("operating_status"),
        overture_confidence=row.get("overture_confidence"), source_release=row.get("source_release"),
        stage=row.get("stage") or "discovered", score_version=row.get("score_version"),
        score_breakdown=row.get("score_breakdown") or {}, review_status=row.get("review_status") or "pending",
        reviewed_by=row.get("reviewed_by"), reviewed_at=row.get("reviewed_at"), review_note=row.get("review_note"),
        outreach_status=row.get("outreach_status") or "not_approved",
        outreach_approved_by=row.get("outreach_approved_by"), outreach_approved_at=row.get("outreach_approved_at"),
        outreach_sent_at=row.get("outreach_sent_at"), contact_status=row.get("contact_status") or "unknown",
        location_count=int(row.get("location_count") or len(row.get("locations") or [])),
        locations=row.get("locations") or [], contacts=row.get("contacts") or [], evidence=row.get("evidence") or [],
        score_history=row.get("score_history") or [],
        evidence_count=int(row.get("evidence_count") or len(row.get("evidence") or [])),
        last_verified_at=row.get("last_verified_at"), created_at=row.get("created_at"), updated_at=row.get("updated_at"),
    )


@router.get("/status")
def lead_refresh_status() -> dict:
    return refresh_status()


@router.post("/refresh")
def lead_refresh() -> dict:
    return start_refresh_in_background()


class SendLeadEmail(BaseModel):
    lead_id: str = Field(min_length=1)
    subject: str | None = Field(default=None, max_length=998)
    body: str | None = Field(default=None, max_length=100000)


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
        return send_for(body.lead_id, subject=body.subject, body=body.body)
    except LeadMailError as exc:
        raise _mail_error(exc) from exc


@router.get("", response_model=LeadPage)
def list_leads(
    brand_id: BrandId | None = None,
    search: str | None = Query(default=None, min_length=2, max_length=100),
    contact: Literal["all", "email", "phone", "reachable"] = "all",
    sort: Literal["fit", "name"] = "fit",
    limit: int = Query(default=40, ge=1, le=100),
    cursor: str | None = Query(default=None, max_length=4096),
) -> LeadPage:
    if not key_configured():
        return LeadPage(items=[], next_cursor=None, has_more=False, limit=limit)
    try:
        page = load_lead_page(
            brand_id=brand_id,
            search=search,
            contact=contact,
            sort=sort,
            limit=limit,
            cursor=cursor,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return LeadPage(
        items=[_insight(row) for row in page["items"]],
        next_cursor=page["next_cursor"],
        has_more=page["has_more"],
        limit=page["limit"],
    )


@router.get("/{lead_id}", response_model=LeadInsight)
def lead_detail(lead_id: str) -> LeadInsight:
    row = lead_details(lead_id)
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _insight(row)


@router.post("/{lead_id}/review", response_model=LeadInsight)
def lead_review(lead_id: str, body: LeadReviewRequest) -> LeadInsight:
    try:
        row = review_lead(lead_id, body.decision, body.reviewer, body.note)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _insight(row)


@router.post("/suppressions")
def lead_suppress(body: LeadSuppressionRequest) -> dict:
    try:
        suppression_id = add_suppression(body.brand_id, body.domain, body.email, body.reason, body.actor)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"ok": True, "id": suppression_id}
