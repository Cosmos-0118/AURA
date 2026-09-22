from fastapi import APIRouter

try:
    from ..db import get_connection
    from ..schemas import BrandId, Lead, LeadSearchRequest, LeadOutreachRequest
except ImportError:
    from db import get_connection
    from schemas import BrandId, Lead, LeadSearchRequest, LeadOutreachRequest

router = APIRouter(prefix="/api/leads", tags=["leads"])


@router.get("", response_model=list[Lead])
def list_leads(brand_id: BrandId | None = None) -> list[Lead]:
    query = """
    select id, brand_id, name, category, location, url, phone, public_email, 
           social_links, description, services, source, source_url, status, 
           fit_score, why, external_place_id, products, specialties, fit_reasons, last_verified_at,
           created_at, updated_at 
    from leads
    """
    params: tuple[str, ...] = ()
    if brand_id:
        query += " where brand_id = %s"
        params = (brand_id,)
    query += " order by fit_score desc, name"
    
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [Lead(**row) for row in rows]


@router.post("/search", response_model=list[Lead])
def search_leads(request: LeadSearchRequest) -> list[Lead]:
    try:
        from ..agents.leads import discover_and_enrich_leads
    except ImportError:
        from agents.leads import discover_and_enrich_leads
        
    return discover_and_enrich_leads(request)


@router.post("/{lead_id}/outreach")
def generate_outreach(lead_id: str, request: LeadOutreachRequest) -> dict[str, str]:
    try:
        from ..agents.leads import generate_personalized_outreach
    except ImportError:
        from agents.leads import generate_personalized_outreach
        
    # generate outreach creates the draft, runs compliance, and inserts into content_assets
    generate_personalized_outreach(lead_id, request.brand_id)
    return {"status": "success", "message": "Draft created and sent to review"}
