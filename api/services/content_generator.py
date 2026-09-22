"""AURA Content Generator using Groq API via OpenAI-compatible interface."""

import json
import os
from typing import Any

from openai import OpenAI

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
            "A luxury commercial marketing poster for Jade jewellery risk protection. "
            "The poster prominently features bold typography text \"JADE VAULT AUDIT\" in elegant gold serif letters across the top, "
            "and sub-headline text \"INSTITUTIONAL JEWELLERY SECURITY · SINGAPORE\" below it. "
            "In the center is an editorial photograph of a high-security titanium vault with sparkling diamonds on dark velvet. "
            "High-end graphic design poster layout, crisp typography hierarchy, award-winning luxury advertising poster."
        ),
        "video_generation_prompt": (
            "Cinematic vertical 9:16 shot of an armoured courier in elegant black uniform locking a biometric titanium transit case, "
            "moving steadily through a private gallery corridor, professional high-end lighting, seamless slow motion"
        ),
    },
    "doctorshield": {
        "campaign_title": "Navigating Medico-Legal Bounds and Council Inquiry Protocols",
        "core_message": "Empathetic, calm, peer-guided professional protection for medical practitioners.",
        "linkedin": {
            "title": "Three Things Clinicians Should Know About Council Inquiries",
            "content": (
                "Three things doctors should know when facing a medical inquiry:\n\n"
                "1. Early legal counsel preserves clinical documentation integrity and reduces procedural anxiety.\n"
                "2. Disciplinary committees scrutinize peer-reviewed standards of clinical practice.\n"
                "3. DoctorShield provides calm, experienced medico-legal guidance every step of the journey, ensuring your professional reputation is defended with diligence.\n\n"
                "Your clinical focus belongs with your patients. Let our dedicated legal specialists support your practice."
            ),
            "hashtags": ["#DoctorShield", "#MedicalIndemnity", "#ClinicalGovernance", "#DoctorWellbeing"],
        },
        "x": {
            "content": (
                "Facing a clinical dispute is emotionally taxing. Early medico-legal guidance is critical to protecting both practitioner and patient.\n\n"
                "Read DoctorShield's practical inquiry response guide: jaassure.com/doctorshield"
            ),
            "hashtags": ["#HealthcareLaw", "#MedicalIndemnity"],
        },
        "instagram": {
            "caption": (
                "Practicing medicine requires uncompromised focus. When legal or ethical questions arise, having experienced peer counsel brings peace of mind.\n\n"
                "DoctorShield by JA Assure stands beside medical practitioners with collegial indemnity and proactive risk guidance."
            ),
            "visual_concept": "Serene, professional photograph of a female physician in white coat consulting notes in a modern, sunlit clinic office, calm expressions, soft natural tones.",
            "hashtags": ["#DoctorShield", "#HealthcareProfessionals", "#ClinicManagement"],
        },
        "blog": {
            "title": "Telemedicine Consent & Medico-Legal Risk Management in ASEAN",
            "content": (
                "As remote consultations expand, practitioners must maintain documentation rigor matching physical consultations.\n\n"
                "This guide details three clinical governance safeguards for telemedicine record-keeping and statutory compliance."
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
            "captions": "Calm, experienced medical defense. DoctorShield by JA Assure.",
        },
        "image_generation_prompt": (
            "A professional commercial marketing poster for DoctorShield medical indemnity. "
            "The poster prominently features bold, clean typography text \"STAND PROTECTED\" in refined navy lettering at the top, "
            "with sub-headline text \"PEER-GUIDED MEDICO-LEGAL DEFENSE\" in crisp sans-serif below. "
            "In the center is an empathetic editorial photograph of a clinician in a modern sunlit clinic office. "
            "Minimalist graphic design poster layout, trustworthy medical branding poster."
        ),
        "video_generation_prompt": (
            "Cinematic vertical 9:16 slow push-in shot of a modern medical clinic consultation room, daylight through large windows, "
            "a stethoscope and medical reference books resting neatly on a dark wooden desk, calm peaceful atmosphere"
        ),
    },
    "jaguar": {
        "campaign_title": "ASEAN Bonded Logistics Telemetry & Chain-of-Custody Assurance",
        "core_message": "Digital telemetry tracking meets rapid underwriting dispatch for high-value cargo in transit.",
        "linkedin": {
            "title": "Cross-Border Cargo Chain of Custody in ASEAN",
            "content": (
                "In bonded transit between Singapore and Kuala Lumpur, handover checkpoints are where 68% of discrepancies occur.\n\n"
                "Jaguar Transit combines multi-sensor telemetry tracking with real-time underwriting endorsements to keep your high-value cargo protected door-to-door.\n\n"
                "From tamper-evident seal verification to expedited customs bonded corridor handling, our logistics desk provides the operational rigor required by modern supply chains.\n\n"
                "Request a corridor risk assessment with our freight underwriters."
            ),
            "hashtags": ["#LogisticsRisk", "#FreightSecurity", "#ASEANTrade", "#SupplyChainSafety"],
        },
        "x": {
            "content": (
                "High-value logistics is not about hope—it is about verifiable telemetry and bonded protocol enforcement.\n\n"
                "How is your cargo secured at border clearances? Learn about Jaguar Transit: jaassure.com/jaguar"
            ),
            "hashtags": ["#Logistics", "#CargoProtection"],
        },
        "instagram": {
            "caption": (
                "Precision freight demands precision protection. Jaguar Transit connects real-time IoT cargo sensors with instant underwriting binding across ASEAN transit corridors."
            ),
            "visual_concept": "High-contrast dynamic photograph of a high-tech logistics truck with illuminated digital tamper seals passing through a Singapore port bonded terminal at dusk.",
            "hashtags": ["#JaguarTransit", "#LogisticsTech", "#CargoSecurity"],
        },
        "blog": {
            "title": "Why Generic Marine Cargo Policies Fail at Overland Land Customs",
            "content": (
                "Traditional marine insurance clauses were written for maritime vessels, creating dangerous gaps at secondary land border clearance stations.\n\n"
                "Jaguar Transit addresses cross-dock delays and bonded corridor regulations directly."
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
            "captions": "Real-time telemetry cargo protection. Jaguar Transit by JA Assure.",
        },
        "image_generation_prompt": (
            "A high-impact commercial logistics marketing poster for Jaguar Transit. "
            "The poster prominently features bold industrial typography text \"CHAIN OF CUSTODY ASSURED\" in sharp electric blue letters across the top, "
            "with sub-headline text \"REAL-TIME TELEMETRY FREIGHT PROTECTION\" below. "
            "In the center is a high-tech container freight truck with glowing digital security seals at a twilight port terminal. "
            "Dynamic graphic poster design, editorial typography, supply chain advertising poster."
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

    return f"""You are AURA, an elite AI Marketing Operations agent for JA Assure (insurance & risk management group).
You are generating a complete, multi-platform B2B marketing campaign for the brand: {brand['name']} ({brand['tagline']}).

BRAND PERSONALITY:
{brand['personality']}

TARGET AUDIENCE:
{brand['audience']}

BRAND VOICE & TONE:
{brand['voice']}

COMPLIANCE REQUIREMENTS:
{brand['compliance']}
{lessons_text}

OUTPUT INSTRUCTIONS:
You MUST respond with a single, strictly valid JSON object. No Markdown code blocks, no preamble, no commentary.
The JSON must have this exact structure:
{{
  "campaign_title": "...",
  "core_message": "...",
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
  "image_generation_prompt": "MUST be a prompt for a commercial marketing poster with bold typography text embedded directly in the visual. Must explicitly include: 1) A primary bold headline text in quotes related to the campaign thesis (e.g. 'commercial advertising poster prominently featuring bold typography text \"HEADLINE\" across the top in elegant lettering'), 2) A secondary sub-headline text in quotes, 3) High-end graphic design poster layout with clear typography hierarchy, negative space, and premium brand aesthetics.",
  "video_generation_prompt": "..."
}}

IMPORTANT: The image_generation_prompt MUST always specify that the image is a commercial marketing poster featuring bold readable headline text in quotes related to the campaign thesis.
"""


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
Output ONLY JSON."""

    # Using Groq's high-speed reasoning / production model with automatic fallback
    preferred_model = os.environ.get("GROQ_MODEL", "openai/gpt-oss-20b")
    candidate_models = [preferred_model]
    for fallback in ["openai/gpt-oss-20b", "qwen/qwen3.8-27b", "llama-3.3-70b-versatile"]:
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
            )
            raw_content = response.choices[0].message.content or "{}"
            return json.loads(raw_content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Groq returned non-JSON response: {exc}") from exc
        except Exception as exc:
            last_exc = exc
            if "model_not_found" in str(exc) or "404" in str(exc):
                continue
            raise RuntimeError(f"Groq content generation failed: {exc}") from exc

    raise RuntimeError(f"Groq content generation failed: {last_exc}") from last_exc
