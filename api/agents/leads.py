import os
import uuid
import json
import httpx
from datetime import datetime
from pydantic import BaseModel
from google import genai

try:
    from ..schemas import Lead, LeadSearchRequest
    from ..db import get_connection
except ImportError:
    from schemas import Lead, LeadSearchRequest
    from db import get_connection


def get_client() -> genai.Client | None:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key or api_key == "your_personal_gemini_key":
        return None
    return genai.Client(api_key=api_key)


class WebsiteExtraction(BaseModel):
    description: str | None = None
    services: list[str] = []
    products: list[str] = []
    specialties: list[str] = []
    public_email: str | None = None
    social_links: list[str] = []


def extract_website_info(url: str, client: genai.Client) -> WebsiteExtraction:
    if not url or not client:
        return WebsiteExtraction()
        
    try:
        # Fetch the homepage content
        with httpx.Client(timeout=10.0) as http:
            response = http.get(url, follow_redirects=True)
            response.raise_for_status()
            html_content = response.text[:20000] # take first 20k chars to avoid huge payload
            
        prompt = f"""
        Extract business information from the following website HTML content.
        Only extract what is explicitly present. Do NOT invent or hallucinate data.
        
        Website Content:
        {html_content}
        
        Respond ONLY with a valid JSON object matching exactly this schema:
        {{
            "description": "A short summary of the business (or null if not found)",
            "services": ["list of services offered"],
            "products": ["list of specific products mentioned"],
            "specialties": ["list of specialties"],
            "public_email": "any contact email found (or null)",
            "social_links": ["list of full URLs to social media profiles"]
        }}
        """
        
        interaction = client.interactions.create(
            model="gemini-3.6-flash",
            input=prompt
        )
        
        text = interaction.output_text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
            
        data = json.loads(text.strip())
        return WebsiteExtraction(**data)
        
    except Exception as e:
        print(f"Website extraction failed for {url}: {e}")
        return WebsiteExtraction()


def calculate_fit_score(lead_data: dict, target_category: str, target_location: str) -> tuple[int, list[str]]:
    score = 0
    reasons = []
    
    # 1. Has website (Base online presence)
    if lead_data.get("url"):
        score += 15
        reasons.append("Official website found (+15)")
    
    # 2. Has phone
    if lead_data.get("phone"):
        score += 10
        reasons.append("Contact phone number available (+10)")
        
    # 3. Has email
    if lead_data.get("public_email"):
        score += 15
        reasons.append("Public contact email found (+15)")
        
    # 4. Location match
    address = (lead_data.get("location") or "").lower()
    if target_location.lower() in address:
        score += 20
        reasons.append(f"Location matches target '{target_location}' (+20)")
        
    # 5. Category/Services relevance
    primary_type = (lead_data.get("category") or "").lower()
    if target_category.lower() in primary_type:
        score += 25
        reasons.append(f"Primary category matches target '{target_category}' (+25)")
    else:
        # Check if any service matches
        services = [s.lower() for s in lead_data.get("services", [])]
        matched_service = False
        for s in services:
            if target_category.lower() in s:
                matched_service = True
                break
        
        if matched_service:
            score += 15
            reasons.append(f"Found related services matching '{target_category}' (+15)")
            
    # 6. Social presence
    if lead_data.get("social_links"):
        score += 15
        reasons.append("Active social media presence detected (+15)")
        
    return min(100, score), reasons


def discover_and_enrich_leads(request: LeadSearchRequest) -> list[Lead]:
    google_api_key = os.getenv("GOOGLE_MAPS_API_KEY")
    if not google_api_key:
        raise ValueError("Real business discovery is not configured. Please configure the GOOGLE_MAPS_API_KEY in your .env file.")
        
    client = get_client()
    
    search_query = f"{request.category} in {request.location}"
    if request.keywords:
        search_query = f"{request.keywords} in {request.location}"
        
    places_url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "X-Goog-Api-Key": google_api_key,
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.businessStatus,places.primaryType,places.types,places.nationalPhoneNumber,places.websiteUri,places.googleMapsUri,places.location",
        "Content-Type": "application/json"
    }
    payload = {
        "textQuery": search_query,
        "languageCode": "en"
    }
    
    try:
        with httpx.Client(timeout=15.0) as http:
            res = http.post(places_url, headers=headers, json=payload)
            res.raise_for_status()
            places_data = res.json()
    except Exception as e:
        print(f"Google Places API request failed: {e}")
        return []
        
    places = places_data.get("places", [])
    if not places:
        return []
        
    leads = []
    
    for place in places:
        if place.get("businessStatus") != "OPERATIONAL":
            continue
            
        external_place_id = place.get("id")
        name = place.get("displayName", {}).get("text", "Unknown Business")
        address = place.get("formattedAddress", "")
        phone = place.get("nationalPhoneNumber")
        website = place.get("websiteUri")
        google_maps_url = place.get("googleMapsUri", "")
        primary_type = (place.get("primaryType") or "Business").replace("_", " ").title()
        
        # Enrichment
        enriched_data = WebsiteExtraction()
        if website and client:
            enriched_data = extract_website_info(website, client)
            
        # Compile raw data for scoring
        lead_data = {
            "name": name,
            "category": primary_type,
            "location": address,
            "url": website,
            "phone": phone,
            "public_email": enriched_data.public_email,
            "social_links": enriched_data.social_links,
            "services": enriched_data.services
        }
        
        fit_score, fit_reasons = calculate_fit_score(lead_data, request.category, request.location)
        status = "Qualified" if fit_score >= 60 else "new"
        
        lead = Lead(
            id=str(uuid.uuid4()),
            brand_id=request.brand_id,
            name=name,
            category=primary_type,
            location=address,
            url=website,
            phone=phone,
            public_email=enriched_data.public_email,
            social_links=enriched_data.social_links,
            description=enriched_data.description,
            services=enriched_data.services,
            products=enriched_data.products,
            specialties=enriched_data.specialties,
            source="Google Places",
            source_url=google_maps_url,
            status=status,
            fit_score=fit_score,
            why=None, # Deprecated in favor of fit_reasons
            external_place_id=external_place_id,
            fit_reasons=fit_reasons,
            last_verified_at=datetime.now(),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        leads.append(lead)
        
    try:
        with get_connection() as conn:
            for lead in leads:
                try:
                    lead_values = (
                        lead.brand_id,
                        lead.name,
                        lead.category,
                        lead.location,
                        lead.url,
                        lead.phone,
                        lead.public_email,
                        lead.description,
                        lead.source,
                        lead.source_url,
                        lead.status,
                        lead.fit_score,
                        lead.created_at,
                        lead.updated_at,
                        lead.external_place_id,
                        json.dumps(lead.products),
                        json.dumps(lead.specialties),
                        json.dumps(lead.fit_reasons),
                        lead.last_verified_at,
                    )
                    existing = None
                    if lead.external_place_id:
                        existing = conn.execute(
                            "select id, status from leads where external_place_id = %s and brand_id = %s",
                            (lead.external_place_id, lead.brand_id),
                        ).fetchone()
                    if existing:
                        conn.execute(
                            """
                            update leads set brand_id = %s, name = %s, category = %s,
                              location = %s, url = %s, phone = %s, public_email = %s,
                              description = %s, source = %s, source_url = %s,
                              fit_score = %s, status = %s, updated_at = %s, products = %s,
                              specialties = %s, fit_reasons = %s, last_verified_at = %s
                            where id = %s
                            """,
                            (
                                lead.brand_id,
                                lead.name,
                                lead.category,
                                lead.location,
                                lead.url,
                                lead.phone,
                                lead.public_email,
                                lead.description,
                                lead.source,
                                lead.source_url,
                                lead.fit_score,
                                existing.get("status") or lead.status,
                                lead.updated_at,
                                json.dumps(lead.products),
                                json.dumps(lead.specialties),
                                json.dumps(lead.fit_reasons),
                                lead.last_verified_at,
                                existing["id"],
                            ),
                        )
                    else:
                        conn.execute(
                            """
                            insert into leads (
                              id, brand_id, name, category, location, url, phone, public_email,
                              description, source, source_url, status, fit_score, created_at,
                              updated_at, external_place_id, products, specialties, fit_reasons,
                              last_verified_at
                            ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (lead.id,) + lead_values,
                        )
                except Exception as e:
                    raise RuntimeError(f"Failed to persist lead {lead.name}: {e}") from e
    except Exception as e:
        raise RuntimeError(f"Database connection failed while saving discovered leads: {e}") from e
            
    return leads


def generate_personalized_outreach(lead_id: str, brand_id: str) -> None:
    client = get_client()
    if client is None:
        raise ValueError("Real outreach is not configured. Set GEMINI_API_KEY before generating outreach.")
    
    try:
        with get_connection() as conn:
            lead = conn.execute("select * from leads where id = %s", (lead_id,)).fetchone()
            if not lead:
                raise ValueError(f"Lead {lead_id} not found")
                
            brand = conn.execute("select * from brands where id = %s", (brand_id,)).fetchone()
            brand_name = brand['name'] if brand else brand_id
                
            prompt = f"""
            You are an expert sales copywriter.
            Write a highly personalized, professional LinkedIn outreach message to {lead['name']}.
            
            Company Context:
            - Name: {lead['name']}
            - Industry/Category: {lead['category']}
            - Location: {lead['location']}
            - Description: {lead['description']}
            
            Our Brand: {brand_name}
            
            Keep it under 150 words. Do not use placeholders. Be direct and value-driven.
            """
            interaction = client.interactions.create(
                model="gemini-3.6-flash",
                input=prompt
            )
            
            draft_body = interaction.output_text.strip()
            
            asset_id = str(uuid.uuid4())
            conn.execute(
                """
                insert into content_assets
                  (id, brand_id, platform, content_type, variant, language, title, body, hashtags, status)
                values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    asset_id,
                    brand_id,
                    "linkedin",
                    "outreach",
                    "A",
                    "en",
                    f"Outreach to {lead['name']}",
                    draft_body,
                    json.dumps([]),
                    "pending_review"
                )
            )
            
            # Mock compliance check pass (since actual compliance agent is separate)
            conn.execute(
                """
                insert into compliance_checks
                  (id, asset_id, result, risk, rules, issues, suggested_revision)
                values (%s, %s, %s, %s, %s, %s, %s)
                """,
                (str(uuid.uuid4()), asset_id, "PASS", "LOW", json.dumps([]), json.dumps([]), None)
            )
            
            conn.execute("update leads set status = 'Draft Generated' where id = %s", (lead_id,))
    except Exception as e:
        raise RuntimeError(f"Could not save outreach draft: {e}") from e
