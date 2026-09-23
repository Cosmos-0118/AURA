"""AURA Content Generator using Groq API via OpenAI-compatible interface."""

import json
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ROOT_ENV)
load_dotenv()

BRAND_KNOWLEDGE = {
    "jade": {
        "name": "Jade",
        "tagline": "Specialist Jewellery & Fine Art Risk Protection",
        "personality": "Authoritative, Premium, Specialist, Intelligent, B2B, Risk-aware, Never overly salesy",
        "audience": "Jewellers, fine-art businesses, luxury asset businesses, and high-value asset owners.",
        "voice": "Restrained, institutional, sophisticated, risk-education-focused.",
        "compliance": "Strict claim wording. NEVER guarantee complete protection, zero loss, or foolproof vault security. Frame as risk understanding and underwriting partnership.",
    },
    "doctorshield": {
        "name": "DoctorShield",
        "tagline": "Medical Indemnity & Professional Protection",
        "personality": "Reassuring, Educational, Professional, Trustworthy, Human, Calm",
        "audience": "Doctors, clinics, medical practitioners, and healthcare businesses.",
        "voice": "Calm, empathetic, collegial, reassuring bedside manner.",
        "compliance": "Strict adherence to medical ethics and council guidelines. No fear-based marketing, no claims of lawsuit immunity, no medical advice claims.",
    },
    "jaguar": {
        "name": "Jaguar Transit",
        "tagline": "High-Value Valuables & Cargo in Transit Protection",
        "personality": "Secure, Operational, Fast, Precise, Reliable",
        "audience": "Couriers, logistics companies, high-value goods businesses, and SMEs.",
        "voice": "Precise, confident, direct, operational checklist focus.",
        "compliance": "Clear boundary between shipper and carrier liability. No absolute guarantees against transit theft. Realistic customs protocol explanations.",
    },
}

DEMO_CAMPAIGNS: dict[str, dict[str, Any]] = {
    "jade": {
        "campaign_title": "Mitigating High-Value Transit & Vault Risk for Modern Jewellers",
        "core_message": "Protecting high-value jewellery begins long before a claim is made through multi-custody underwriting.",
        "linkedin": {
            "title": "Understanding Vault & Transit Risk Profiles in Southeast Asia",
            "content": (
                "Protecting high-value jewellery begins long before a claim is made.\n\n"
                "Every jewellery business carries risk. The question is whether that risk has been properly "
                "understood, categorized, and systematically mitigated across showroom handling, private viewing, and transit.\n\n"
                "Our underwriters work alongside master jewellers across Southeast Asia to audit physical vault architecture "
                "and multi-custody redundancies.\n\n"
                "Speak with our high-value asset specialists to review your institutional risk schedule."
            ),
            "hashtags": ["#JewelleryInsurance", "#RiskManagement", "#FineArtProtection", "#JAAssureJade"],
        },
        "x": {
            "content": (
                "High-value inventory risk isn't just about vault thickness—it's about protocol redundancy at handover points.\n\n"
                "How does your atelier manage off-site client viewings? Read our underwriting brief: jaassure.com/jade"
            ),
            "hashtags": ["#JewelleryRisk", "#LuxurySecurity"],
        },
        "instagram": {
            "caption": (
                "Behind every exquisite collection lies an uncompromised chain of custody.\n\n"
                "At Jade by JA Assure, our specialist underwriters design bespoke protection for fine art and jewellery "
                "businesses that demand institutional rigor.\n\n"
                "Swipe to explore the 4 vulnerabilities luxury ateliers encounter during peak exhibition seasons."
            ),
            "visual_concept": "Editorial macro photograph of a master gemmologist inspecting a rare Colombian emerald inside a brushed steel vault, warm ambient lighting with dark green accents.",
            "hashtags": ["#JadeInsurance", "#FineJewellery", "#Gemmology", "#VaultSecurity"],
        },
        "blog": {
            "title": "Consignment & Exhibition Risk: An Underwriter Perspective for ASEAN Jewellers",
            "content": (
                "Executive Summary: Why High-Value Retail Demands Institutional Governance\n\n"
                "When fine jewellery leaves permanent vault custody for international exhibitions or private collector viewings, "
                "traditional commercial policies often exhibit critical coverage gaps.\n\n"
                "Section 1: The Anatomy of Custody Handover Vulnerabilities\n"
                "Historical loss analysis demonstrates that over 60% of claim disputes arise from mismatched transit schedules. "
                "When courier handoffs lack dual-signoff protocols, operators bear uninsurable exposures.\n\n"
                "Section 2: The Jade Underwriting Framework\n"
                "At JA Assure, our approach combines specialized underwriting with proactive risk mitigation advisory, "
                "ensuring that your balance sheet remains insulated against volatility.\n\n"
                "Conclusion: Schedule an institutional exposure review with our specialist committee."
            ),
        },
        "reel": {
            "title": "45-Second Audit: The Blind Spots in Jewellery Transit",
            "hook": "Most jewellers only discover their insurance exclusions after an exhibition transit loss.",
            "duration": "45s",
            "scenes": [
                {"scene": 1, "visual": "Close-up of a locked Pelican transit case with tamper seal", "duration": "0-10s"},
                {"scene": 2, "visual": "Showroom floor private viewing room handover", "duration": "10-25s"},
                {"scene": 3, "visual": "Underwriter reviewing policy schedules on digital tablet", "duration": "25-35s"},
                {"scene": 4, "visual": "Jade logo with consultation call to action", "duration": "35-45s"},
            ],
            "voiceover": (
                "Standard commercial insurance often excludes off-premises viewings and multi-carrier handovers. "
                "Jade structures bespoke jewellers block protection built around how you actually operate."
            ),
            "captions": "Don't let policy exclusions blindside your atelier. Speak with Jade by JA Assure.",
        },
        "image_generation_prompt": (
            'Commercial advertising poster with bold typography text overlay for Jade by JA Assure. '
            'Large prominent headline text overlay across the top reads: "JADE VAULT AUDIT 2026". '
            'Secondary sub-headline text overlay reads: "OCT 15 | MARINA BAY SINGAPORE". '
            'Third line text reads: "COMPLIMENTARY EXECUTIVE BRIEFING". '
            'High-contrast luxury graphic design poster layout with clean typography text overlay on an editorial photograph of a high-security titanium vault with sparkling emeralds and diamond necklaces.'
        ),
        "video_generation_prompt": (
            "Cinematic vertical 9:16 shot of an armoured courier in elegant black uniform locking a biometric titanium transit case, "
            "moving steadily through a private gallery corridor, professional high-end lighting, seamless slow motion"
        ),
    },
    "doctorshield": {
        "campaign_title": "Navigating Medico-Legal Bounds and Council Inquiry Protocols",
        "core_message": "Empathetic, calm, peer-guided professional protection for medical practitioners.",
        "campaign_facts": {
            "event_name": "Medical Council Inquiry Protocols Workshop",
            "date": "Sep 24, 2026",
            "time": "10:00 AM - 4:00 PM SGT",
            "location": "Suntec Singapore Convention Centre",
            "price": "Free Admission for Registered Clinicians",
            "cta": "Register for Collegial Inquiry Guidance",
            "brand": "DoctorShield by JA Assure",
        },
        "linkedin": {
            "title": "Three Things Clinicians Should Know About Council Inquiries",
            "content": (
                "Three things doctors should know when facing a medical inquiry:\n\n"
                "1. Early legal counsel preserves clinical documentation integrity and reduces procedural anxiety.\n"
                "2. Disciplinary committees scrutinize peer-reviewed standards of clinical practice.\n"
                "3. DoctorShield provides calm, experienced medico-legal guidance every step of the journey, ensuring your professional reputation is defended with diligence.\n\n"
                "Join us on Sep 24 from 10:00 AM to 4:00 PM for a free, in-person workshop on Medical Council inquiry protocols at Suntec Singapore.\n\n"
                "Your clinical focus belongs with your patients. Let our dedicated legal specialists support your practice."
            ),
            "hashtags": ["#DoctorShield", "#MedicalIndemnity", "#ClinicalGovernance", "#DoctorWellbeing"],
        },
        "x": {
            "content": (
                "Facing a clinical dispute is emotionally taxing. Early medico-legal guidance is critical.\n\n"
                "Free in-person workshop: Medical Council Inquiry Protocols on Sep 24 at Suntec Singapore.\n\n"
                "Register now: jaassure.com/doctorshield"
            ),
            "hashtags": ["#HealthcareLaw", "#MedicalIndemnity"],
        },
        "instagram": {
            "caption": (
                "Practicing medicine requires uncompromised focus. When legal or ethical questions arise, having experienced peer counsel brings peace of mind.\n\n"
                "DoctorShield by JA Assure invites clinicians to our free in-person workshop on Medical Council Inquiry Protocols, Sep 24 at Suntec Singapore."
            ),
            "visual_concept": "Serene, professional photograph of a female physician in white coat consulting notes in a modern, sunlit clinic office, calm expressions, soft natural tones.",
            "hashtags": ["#DoctorShield", "#HealthcareProfessionals", "#ClinicManagement"],
        },
        "blog": {
            "title": "Telemedicine Consent & Medico-Legal Risk Management in ASEAN",
            "content": (
                "As remote consultations expand, practitioners must maintain documentation rigor matching physical consultations.\n\n"
                "This guide details three clinical governance safeguards for telemedicine record-keeping and statutory compliance.\n\n"
                "Upcoming Event: Medical Council Inquiry Protocols Workshop on Sep 24 at Suntec Singapore (Free Admission)."
            ),
        },
        "reel": {
            "title": "What to Do When You Receive a Formal Inquiry Notice",
            "hook": "A formal patient complaint does not mean your clinical career is derailed.",
            "duration": "45s",
            "scenes": [
                {"scene": 1, "visual": "Doctor reading formal letter with calm focus", "duration": "0-12s"},
                {"scene": 2, "visual": "Senior medico-legal counsel reviewing patient notes together", "duration": "12-30s"},
                {"scene": 3, "visual": "Confident consultation room environment", "duration": "30-45s"},
            ],
            "voiceover": "Early advice preserves documentation integrity. DoctorShield provides dedicated peer legal defense.",
            "captions": "Sep 24 Workshop · Suntec Singapore. DoctorShield by JA Assure.",
        },
        "image_generation_prompt": (
            'A professional event poster for DoctorShield by JA Assure featuring the title "Medical Council Inquiry Protocols Workshop", '
            'date "Sep 24 | 10 AM - 4 PM", location "Suntec Singapore", admission "Free Admission for Clinicians", '
            'clean modern typography, corporate healthcare aesthetic, warm natural lighting, high-contrast graphic design poster layout, crisp legible text overlay.'
        ),
        "video_generation_prompt": (
            "Cinematic vertical 9:16 shot of a composed senior physician and legal counsel discussing case documentation in a modern conference room, "
            "warm natural lighting, slow dolly zoom, reassuring medical atmosphere, 4k"
        ),
    },
    "jaguar": {
        "campaign_title": "Cross-Border Telemetry & Chain of Custody Freight Underwriting",
        "core_message": "Operational, sensor-driven telemetry freight assurance across ASEAN land borders.",
        "campaign_facts": {
            "event_name": "Cross-Border Transit Telemetry Masterclass",
            "date": "Nov 12, 2026",
            "time": "9:30 AM - 1:00 PM SGT",
            "location": "Changi Logistics Centre, Singapore",
            "price": "Complimentary Industry Session",
            "cta": "Book Logistics Fleet Underwriting Review",
            "brand": "Jaguar Transit by JA Assure",
        },
        "linkedin": {
            "title": "Closing the 48-Hour Cross-Dock Handover Exposure Window",
            "content": (
                "When cargo moves across borders, traditional marine policies leave critical gaps during customs inspections.\n\n"
                "Jaguar Transit integrates active IoT telemetry with insurance underwriting to provide unbroken chain-of-custody verification.\n\n"
                "Join our Cross-Border Transit Telemetry Masterclass on Nov 12 at Changi Logistics Centre, Singapore.\n\n"
                "Book your logistics fleet underwriting review with Jaguar Transit by JA Assure."
            ),
            "hashtags": ["#LogisticsRisk", "#SupplyChainSecurity", "#CargoInsurance", "#JaguarTransit"],
        },
        "x": {
            "content": (
                "Where does your cargo risk peak? 68% of discrepancies happen at secondary customs handovers.\n\n"
                "Attend the Transit Telemetry Masterclass: Nov 12 at Changi Logistics Centre: jaassure.com/jaguar"
            ),
            "hashtags": ["#FreightSecurity", "#CargoTech"],
        },
        "instagram": {
            "caption": (
                "Real-time sensor telemetry meets institutional freight underwriting.\n\n"
                "Jaguar Transit ensures every sealed container is tracked and defended across Southeast Asia's critical bonded transit corridors.\n\n"
                "Masterclass on Nov 12 at Changi Logistics Centre. Register via bio."
            ),
            "visual_concept": "Moody twilight photography of an articulated commercial container truck with glowing digital electronic seals parked at a secure customs bonded interchange.",
            "hashtags": ["#JaguarTransit", "#LogisticsOperations", "#FleetManagement"],
        },
        "blog": {
            "title": "Cross-Dock Delay Liability & Telemetry-Backed Cargo Underwriting",
            "content": (
                "Traditional marine insurance clauses were written for maritime vessels, creating dangerous gaps at secondary land border clearance stations.\n\n"
                "Jaguar Transit addresses cross-dock delays and bonded corridor regulations directly.\n\n"
                "Industry Briefing: Cross-Border Transit Telemetry Masterclass, Nov 12 at Changi Logistics Centre (Complimentary)."
            ),
        },
        "reel": {
            "title": "The 3 Checkpoints Where Cargo Discrepancies Happen",
            "hook": "68% of cross-border cargo loss occurs during customs bonded handover.",
            "duration": "40s",
            "scenes": [
                {"scene": 1, "visual": "Container truck at bonded border gate", "duration": "0-10s"},
                {"scene": 2, "visual": "Electronic seal scanned via handheld RFID terminal", "duration": "10-25s"},
                {"scene": 3, "visual": "Jaguar telemetry map dashboard displaying green status", "duration": "25-40s"},
            ],
            "voiceover": "Jaguar Transit embeds real-time sensor tracking into your insurance endorsement.",
            "captions": "Nov 12 Masterclass · Changi Logistics Centre. Jaguar Transit by JA Assure.",
        },
        "image_generation_prompt": (
            'Commercial advertising poster with bold typography text overlay for Jaguar Transit by JA Assure. '
            'Large prominent headline text overlay across the top reads: "TRANSIT TELEMETRY MASTERCLASS". '
            'Secondary sub-headline text overlay reads: "NOV 12 | CHANGI LOGISTICS CENTRE". '
            'Third line text reads: "REAL-TIME TELEMETRY FREIGHT ENDORSEMENT". '
            'High-contrast industrial graphic design poster layout with bold text overlay on a modern telemetry container freight truck with glowing digital security seals at dusk.'
        ),
        "video_generation_prompt": (
            "Cinematic vertical 9:16 tracking shot alongside a sleek commercial freight truck driving across a modern cable-stayed bridge at night, "
            "city skyline lights in background, smooth camera movement, 4k"
        ),
    },
}


def build_system_prompt(brand_id: str, lessons: list[dict[str, Any]]) -> str:
    brand = BRAND_KNOWLEDGE.get(brand_id, BRAND_KNOWLEDGE["jade"])

    lessons_text = ""
    if lessons:
        negative_rules = []
        for l in lessons:
            tag = l.get("tag") or l.get("reason_tag", "GUIDELINE")
            note = l.get("note", "")
            negative_rules.append(f"- {tag}: {note}")
        lessons_text = (
            "\n\nCRITICAL PREVIOUS HUMAN CORRECTIONS (DO NOT REPEAT THESE MISTAKES):\n"
            + "\n".join(negative_rules)
            + "\n\nEnforce these corrections strictly across all platforms."
        )

    return f"""You are AURA, an AI marketing campaign generator for JA Assure.
Generate a complete marketing campaign based on the provided campaign configuration.

BRAND: {brand['name']} ({brand['tagline']})
BRAND PERSONALITY: {brand['personality']}
TARGET AUDIENCE: {brand['audience']}
BRAND VOICE & TONE: {brand['voice']}
COMPLIANCE REQUIREMENTS: {brand['compliance']}
{lessons_text}

IMPORTANT - CAMPAIGN CONSISTENCY DIRECTIVES:
The generated campaign content and generated visual prompt MUST be consistent with each other.
The LinkedIn, Instagram, X, Reel, Blog, and Media outputs are part of ONE campaign. Do not invent conflicting dates, times, event names, offers, claims, locations, or CTAs between platforms.

If the campaign content contains a specific factual event detail such as:
- Event name
- Date
- Time
- Location
- Registration deadline
- Price/free admission
- Workshop title
- Offer
- CTA
- Website or registration instruction
then the image_generation_prompt SHOULD incorporate those details into the visual composition when appropriate.

For example, if the campaign says:
"Join us on Sep 24 from 10 am to 4 pm for a free, in-person workshop on Medical Council inquiry protocols at Suntec Singapore"
then the image prompt should be:
"A professional event poster for DoctorShield by JA Assure featuring the title \\"Medical Council Inquiry Protocols Workshop\\", date \\"Sep 24, 10 AM - 4 PM\\", location \\"Suntec Singapore\\", admission \\"Free Admission\\", clean modern typography, corporate healthcare aesthetic, warm natural lighting, high-resolution graphic design poster layout."

DO NOT generate an image prompt that contradicts the campaign text.
DO NOT generate an image prompt with a different event date or a generic photo if the campaign is promoting a specific dated event.
DO NOT leave out essential event details if the campaign is structured as an invitation or event announcement.

STRICT RULES FOR IMAGE TEXT:
1. When generating an image prompt, design it as an event poster, promotional banner, or marketing graphic with intentional typography overlay.
2. Put exact text in quotes in the prompt.
3. Keep the text short and punchy so the text-to-image model can render it cleanly.
4. Include at most 3-4 text elements:
   - Event Title or Main Headline (e.g., "Medical Council Inquiry Workshop")
   - Date / Time (e.g., "Sep 24 | 10 AM - 4 PM")
   - Location or Format (e.g., "Suntec Singapore" or "In-Person Workshop")
   - Subtitle or Brand / Admission (e.g., "DoctorShield by JA Assure" or "Free Admission")
5. Explicitly specify:
   - Placement (e.g., "headline centered at the top", "date and location in a clean lower banner")
   - Font style (e.g., "clean modern sans-serif typography", "bold corporate lettering")
   - Legibility (e.g., "high contrast between text and background", "crisp readable lettering", "no gibberish text")
6. Do NOT overload the image with paragraphs of text. Only key headlines, dates, and locations.
7. Background visual must complement the theme (e.g. professional healthcare setting for DoctorShield, high-security luxury vault for Jade, telemetry cargo freight for Jaguar Transit).
8. The visual style must match the brand aesthetic.
9. Always specify clean graphic design poster layout with professional typography.
10. The image prompt must directly reflect the content generated in the LinkedIn/Instagram/Blog/Reel posts.

OUTPUT INSTRUCTIONS:
You MUST respond with a single, strictly valid JSON object. No Markdown code blocks, no preamble, no commentary.
The JSON must have this exact structure:
{{
  "campaign_title": "...",
  "core_message": "...",
  "campaign_facts": {{
    "event_name": "...",
    "date": "...",
    "time": "...",
    "location": "...",
    "price": "...",
    "cta": "...",
    "brand": "{brand['name']}"
  }},
  "linkedin": {{
    "title": "...",
    "content": "...",
    "hashtags": ["#tag1", "#tag2"]
  }},
  "x": {{
    "content": "...",
    "hashtags": ["#tag1", "#tag2"]
  }},
  "instagram": {{
    "caption": "...",
    "visual_concept": "...",
    "hashtags": ["#tag1", "#tag2"]
  }},
  "blog": {{
    "title": "...",
    "content": "..."
  }},
  "reel": {{
    "title": "...",
    "hook": "...",
    "script": "...",
    "scenes": [
      {{"scene": 1, "visual": "...", "duration": "..."}}
    ],
    "voiceover": "...",
    "captions": "..."
  }},
  "image_generation_prompt": "A professional event poster for {brand['name']} by JA Assure featuring the title \\"[Exact Headline/Title in Quotes]\\", date/time \\"[Date/Time in Quotes]\\", location \\"[Location in Quotes]\\", [Visual Scene Description], clean modern typography, high contrast between text and background, crisp readable lettering, corporate aesthetic graphic design poster layout.",
  "video_generation_prompt": "..."
}}
"""


def _normalize_campaign_facts(pkg: dict[str, Any], brand_id: str, thesis: str) -> dict[str, Any]:
    facts = pkg.get("campaign_facts")
    if not isinstance(facts, dict):
        facts = {}
    brand_name = BRAND_KNOWLEDGE.get(brand_id, {}).get("name", brand_id.capitalize())
    return {
        "event_name": facts.get("event_name") or pkg.get("campaign_title") or thesis or f"{brand_name} Briefing 2026",
        "date": facts.get("date") or "Q4 2026",
        "time": facts.get("time") or "2:00 PM - 5:00 PM SGT",
        "location": facts.get("location") or "Singapore Financial District",
        "price": facts.get("price") or "Complimentary Admission",
        "cta": facts.get("cta") or "Register for Advisory Consultation",
        "brand": facts.get("brand") or f"{brand_name} by JA Assure",
    }


def generate_campaign_content(
    brand_id: str,
    objective: str,
    language: str,
    platforms: list[str],
    thesis: str,
    target_audience: str | None = None,
    lessons: list[dict[str, Any]] | None = None,
    demo_mode: bool = False,
) -> dict[str, Any]:
    """Generate structured campaign content using Groq or Demo mode."""
    if demo_mode:
        demo = DEMO_CAMPAIGNS.get(brand_id, DEMO_CAMPAIGNS["jade"])
        res = json.loads(json.dumps(demo))
        if thesis:
            res["campaign_title"] = thesis[:80]
        if "campaign_facts" not in res or not isinstance(res.get("campaign_facts"), dict):
            res["campaign_facts"] = _normalize_campaign_facts(res, brand_id, thesis)
        return res

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY environment variable is not set. Please configure it or use DEMO_MODE=true.")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.groq.com/openai/v1",
    )

    system_prompt = build_system_prompt(brand_id, lessons or [])
    user_prompt = f"""Generate a campaign package with these parameters:
- Brand: {brand_id}
- Objective: {objective}
- Language: {language}
- Target Platforms: {', '.join(platforms)}
- Campaign Thesis: {thesis}
- Target Audience Focus: {target_audience or 'Default brand audience'}

Generate full, high-quality content for each requested platform, plus detailed image_generation_prompt and video_generation_prompt.
Ensure strict factual alignment between the copy and the image poster prompt.
Output ONLY JSON."""

    # Using Groq's high-speed reasoning / production model with automatic fallback
    preferred_model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
    candidate_models = [preferred_model]
    for fallback in ["openai/gpt-oss-20b", "openai/gpt-oss-120b", "qwen/qwen3.8-27b", "llama-3.3-70b-versatile"]:
        if fallback not in candidate_models:
            candidate_models.append(fallback)

    last_exc = None
    for m in candidate_models:
        try:
            response = client.chat.completions.create(
                model=m,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.7,
                response_format={"type": "json_object"},
                max_tokens=4096,
            )
            raw_content = response.choices[0].message.content or "{}"
            parsed = json.loads(raw_content)
            if "campaign_facts" not in parsed or not isinstance(parsed.get("campaign_facts"), dict):
                parsed["campaign_facts"] = _normalize_campaign_facts(parsed, brand_id, thesis)
            if not parsed.get("image_generation_prompt"):
                facts = parsed.get("campaign_facts", {})
                event_name = facts.get("event_name") or parsed.get("campaign_title") or thesis[:60] or "Executive Briefing"
                date = facts.get("date", "2026")
                loc = facts.get("location", "Singapore")
                bname = BRAND_KNOWLEDGE.get(brand_id, {}).get("name", brand_id.upper())
                parsed["image_generation_prompt"] = (
                    f'Commercial advertising poster with bold typography text overlay for {bname} by JA Assure. '
                    f'Large prominent headline text overlay across the top reads: "{str(event_name).upper()}". '
                    f'Secondary sub-headline text overlay reads: "{str(date).upper()} | {str(loc).upper()}". '
                    f'High-contrast graphic design poster layout with clean typography text overlay, corporate aesthetic.'
                )
            if not parsed.get("video_generation_prompt"):
                bname = BRAND_KNOWLEDGE.get(brand_id, {}).get("name", brand_id.title())
                parsed["video_generation_prompt"] = (
                    f"Cinematic vertical 9:16 corporate documentary footage illustrating {bname} by JA Assure, professional lighting, modern architecture, 4k 60fps."
                )
            return parsed
        except Exception as exc:
            last_exc = exc
            continue

    raise RuntimeError(f"Groq content generation failed on all candidate models: {last_exc}") from last_exc
