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
    query = "select id, brand_id, name, category, location, url, phone, public_email, social_links, description, services, source, source_url, status, fit_score, why, created_at, updated_at from leads"
    params: tuple[str, ...] = ()
    if brand_id:
        query += " where brand_id = %s"
        params = (brand_id,)
    query += " order by fit_score desc, name"
    
    # Check if we should use mocks (as per AGENTS.md)
    import os
    use_mocks = os.getenv("AURA_MOCK_AGENTS", "true").lower() == "true"
    if use_mocks:
        # Return mock data if DB is unavailable
        from datetime import datetime
        return [
            Lead(
                id="123e4567-e89b-12d3-a456-426614174000",
                brand_id=brand_id or "jade",
                name="ABC Jewellers",
                category="Jewellers",
                location="Chennai",
                url="https://example.com",
                phone="+91 9876543210",
                public_email="hello@abcjewellers.com",
                social_links=["https://instagram.com/abcjewellers"],
                description="Premium diamond and gold jewellery.",
                services=["Diamond jewellery", "Gold dealers"],
                source="Google Maps",
                source_url="https://maps.google.com/?q=abc+jewellers",
                status="new",
                fit_score=92,
                why="Target category, high online presence",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        ]
        
    with get_connection() as connection:
        rows = connection.execute(query, params).fetchall()
    return [Lead(**row) for row in rows]


@router.post("/search", response_model=list[Lead])
def search_leads(request: LeadSearchRequest) -> list[Lead]:
    import os
    from datetime import datetime
    use_mocks = os.getenv("AURA_MOCK_AGENTS", "true").lower() == "true"
    
    if use_mocks:
        return [
            Lead(
                id="123e4567-e89b-12d3-a456-426614174000",
                brand_id=request.brand_id,
                name="ABC Jewellers",
                category=request.category,
                location=request.location,
                url="https://example.com",
                phone="+91 9876543210",
                public_email="hello@abcjewellers.com",
                social_links=["https://instagram.com/abcjewellers"],
                description="Premium diamond and gold jewellery.",
                services=["Diamond jewellery", "Gold dealers"],
                source="Google Maps",
                source_url="https://maps.google.com/?q=abc+jewellers",
                status="new",
                fit_score=92,
                why="Target category, high online presence",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
        ]
        
    try:
        from ..agents.leads import discover_and_enrich_leads
    except ImportError:
        from agents.leads import discover_and_enrich_leads
        
    return discover_and_enrich_leads(request)


@router.post("/{lead_id}/outreach")
def generate_outreach(lead_id: str, request: LeadOutreachRequest) -> dict[str, str]:
    import os
    use_mocks = os.getenv("AURA_MOCK_AGENTS", "true").lower() == "true"
    
    if use_mocks:
        return {"status": "success", "message": "Draft created and sent to review"}
        
    try:
        from ..agents.leads import generate_personalized_outreach
    except ImportError:
        from agents.leads import generate_personalized_outreach
        
    # generate outreach creates the draft, runs compliance, and inserts into content_assets
    generate_personalized_outreach(lead_id, request.brand_id)
    return {"status": "success", "message": "Draft created and sent to review"}
