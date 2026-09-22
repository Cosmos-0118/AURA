"""LinkedIn (and Instagram) prompt templates for all three AURA brands.

Brand voices (frozen — matches the AURA brand and API contracts):
  jade          — Precise, premium, B2B specialist
                  Themes: jewellery, craft, inventory, discretion
                  Never: guaranteed, 100% covered, cheapest

  doctorshield  — Calm, educational, colleague-to-colleague
                  Themes: clinics, patients, time, paperwork
                  Never: guaranteed, always covered, claim guaranteed

  jaguar        — Operational, technology-led
                  Themes: transit, custody, speed, security
                  Never: zero risk, guaranteed

Variant A = direct headline-driven copy.
Variant B = storytelling, question-led copy.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    try:
        from ...schemas import ContentRequest
    except ImportError:
        pass  # only needed for type hints

# ---------------------------------------------------------------------------
# Brand voice definitions
# ---------------------------------------------------------------------------

BRAND_VOICES: dict[str, dict] = {
    "jade": {
        "name": "Jade Risk Management",
        "audience": "jewellery retailers, dealers, and auction houses",
        "tone": ["Precise", "premium", "discreet", "B2B specialist"],
        "themes": ["jewellery", "craft", "inventory", "discretion", "valuation"],
        "dont": ["guaranteed", "100% covered", "cheapest", "zero risk"],
        "linkedin_hashtags": ["JadeRisk", "JewelleryRisk", "RiskManagement", "InsurTech"],
        "instagram_hashtags": ["JadeRisk", "Jewellery", "RiskManagement"],
    },
    "doctorshield": {
        "name": "DoctorShield",
        "audience": "medical practitioners, clinic owners, and healthcare administrators",
        "tone": ["Calm", "educational", "colleague-to-colleague", "supportive"],
        "themes": ["clinics", "patients", "time", "paperwork", "indemnity", "practice management"],
        "dont": ["guaranteed", "always covered", "claim guaranteed", "zero risk"],
        "linkedin_hashtags": ["DoctorShield", "MedicalIndemnity", "HealthcareProfessionals", "GPLife"],
        "instagram_hashtags": ["DoctorShield", "MedPractice", "HealthcareHQ"],
    },
    "jaguar": {
        "name": "Jaguar Logistics Insurance",
        "audience": "logistics managers, freight forwarders, and supply chain directors",
        "tone": ["Operational", "technology-led", "precise", "efficiency-focused"],
        "themes": ["transit", "custody", "speed", "security", "cargo", "supply chain"],
        "dont": ["guaranteed", "zero risk", "100% covered"],
        "linkedin_hashtags": ["JaguarLogistics", "CargoInsurance", "SupplyChain", "FreightTech"],
        "instagram_hashtags": ["JaguarLogistics", "Logistics", "FreightTech"],
    },
}


# ---------------------------------------------------------------------------
# Deterministic template renderers
# ---------------------------------------------------------------------------


def _lesson_sentence(lessons: list[str]) -> str:
    """Return a brief 'guided by feedback' sentence when lessons exist."""
    if not lessons:
        return ""
    # Incorporate the spirit of lessons without pasting them verbatim
    count = len(lessons)
    noun = "insight" if count == 1 else "insights"
    return (
        f" This perspective is shaped by {count} reviewer {noun}, "
        "ensuring it reflects what resonates with your audience."
    )


def render_jade(
    topic: str,
    country: str,
    goal: str,
    lessons: list[str],
    variant: str,
) -> dict:
    """Render a Jade Risk Management LinkedIn post."""
    lesson_text = _lesson_sentence(lessons)

    if variant == "A":
        # Direct, headline-driven
        title = f"Protecting {topic}: A Specialist Perspective"
        body = (
            f"In the {country} jewellery market, {topic.lower()} is rarely a straightforward question. "
            f"Every piece holds craft value, provenance, and market sensitivity that standard policies seldom capture.\n\n"
            f"At Jade Risk Management, we work alongside dealers, retailers, and auction houses to build "
            f"coverage that reflects the true complexity of your inventory — not a generic bracket.\n\n"
            f"{goal} calls for a specialist conversation, not an off-the-shelf answer."
            f"{lesson_text}"
        )
        hashtags = ["JadeRisk", "JewelleryRisk", "RiskManagement", "SpecialistCoverage"]
    else:
        # Storytelling, question-led
        title = f"Is Your {topic} Strategy as Refined as Your Inventory?"
        body = (
            f"A jewellery retailer in {country} recently asked: 'What's the real cost of underestimating inventory risk?'\n\n"
            f"The answer isn't a number — it's the gap between what a policy says and what a specialist understands. "
            f"Every stone, setting, and provenance record carries its own risk profile.\n\n"
            f"Jade Risk Management was built for exactly this: discreet, precise protection for businesses "
            f"where craft and commerce intersect. When {goal} is on the table, the details matter."
            f"{lesson_text}"
        )
        hashtags = ["JadeRisk", "JewelleryBusiness", "DiscreetProtection", "CraftAndRisk"]

    return {"title": title, "body": body, "hashtags": hashtags}


def render_doctorshield(
    topic: str,
    country: str,
    goal: str,
    lessons: list[str],
    variant: str,
) -> dict:
    """Render a DoctorShield LinkedIn post."""
    lesson_text = _lesson_sentence(lessons)

    if variant == "A":
        # Direct, educational
        title = f"{topic}: What Every {country} Practitioner Should Know"
        body = (
            f"Medical practice in {country} comes with increasing administrative complexity — "
            f"and {topic.lower()} sits at the centre of it.\n\n"
            f"DoctorShield was designed with practitioners in mind: "
            f"clear indemnity cover that fits around your patients, your clinic, and your working day. "
            f"Not more paperwork — less.\n\n"
            f"If {goal} is your priority right now, the right starting point is a clear-eyed "
            f"review of your current exposure — no jargon, no pressure."
            f"{lesson_text}"
        )
        hashtags = ["DoctorShield", "MedicalIndemnity", "GPLife", "HealthcareProfessionals"]
    else:
        # Storytelling, question-led
        title = f"When Did You Last Review Your Indemnity Cover?"
        body = (
            f"A colleague in {country} told us: 'I assumed my cover kept pace with my practice. It hadn't.'\n\n"
            f"It's an easy assumption to make. Between seeing patients, managing {topic.lower()}, "
            f"and keeping the clinic running, indemnity reviews quietly slip down the list.\n\n"
            f"DoctorShield exists to close that gap — calmly, clearly, without disrupting your schedule. "
            f"{goal} starts with a conversation that fits around your day, not the other way around."
            f"{lesson_text}"
        )
        hashtags = ["DoctorShield", "MedicalPractice", "IndemnityReview", "PractitionerFirst"]

    return {"title": title, "body": body, "hashtags": hashtags}


def render_jaguar(
    topic: str,
    country: str,
    goal: str,
    lessons: list[str],
    variant: str,
) -> dict:
    """Render a Jaguar Logistics Insurance LinkedIn post."""
    lesson_text = _lesson_sentence(lessons)

    if variant == "A":
        # Operational, direct
        title = f"Securing {topic} Across {country}: An Operational Perspective"
        body = (
            f"In high-velocity logistics networks, {topic.lower()} is where exposure concentrates. "
            f"Transit windows, custody handovers, and documentation gaps are the points that matter.\n\n"
            f"Jaguar's technology-led approach maps your cargo flows and identifies where your current "
            f"coverage may not keep pace with operational reality. "
            f"Speed and security don't have to trade off against each other.\n\n"
            f"For supply chain teams focused on {goal}, the right insurance structure is an operational asset — "
            f"not a cost centre."
            f"{lesson_text}"
        )
        hashtags = ["JaguarLogistics", "CargoInsurance", "SupplyChain", "FreightTech"]
    else:
        # Storytelling, question-led
        title = f"Where Does Custody Risk Actually Live in Your Supply Chain?"
        body = (
            f"A freight forwarder in {country} mapped their cargo flows for the first time last quarter. "
            f"What they found changed how they thought about {topic.lower()}.\n\n"
            f"Custody gaps aren't always obvious — they accumulate across handover points, "
            f"transit corridors, and documentation cycles. By the time the exposure surfaces, it's rarely convenient.\n\n"
            f"Jaguar was built to surface those gaps before they surface themselves. "
            f"When {goal} is the brief, operational intelligence is where we start."
            f"{lesson_text}"
        )
        hashtags = ["JaguarLogistics", "FreightForwarding", "CargoRisk", "LogisticsTech"]

    return {"title": title, "body": body, "hashtags": hashtags}


# ---------------------------------------------------------------------------
# Instagram template renderers (stretch — Phase 5)
# ---------------------------------------------------------------------------


def render_jade_instagram(
    topic: str,
    country: str,
    goal: str,
    lessons: list[str],
    variant: str,
) -> dict:
    """Short Instagram caption for Jade Risk Management."""
    lesson_text = " Refined through reviewer feedback." if lessons else ""

    if variant == "A":
        body = (
            f"Jewellery risk in {country} deserves specialist attention. "
            f"{topic} — covered with precision, not approximation.{lesson_text}"
        )
        hashtags = ["JadeRisk", "Jewellery", "RiskManagement", "PremiumProtection"]
    else:
        body = (
            f"Every piece tells a story. Your coverage should too. "
            f"{goal} starts with a specialist, not a spreadsheet.{lesson_text}"
        )
        hashtags = ["JadeRisk", "JewelleryBusiness", "CraftProtection", "SpecialistRisk"]

    return {"title": None, "body": body, "hashtags": hashtags}


def render_doctorshield_instagram(
    topic: str,
    country: str,
    goal: str,
    lessons: list[str],
    variant: str,
) -> dict:
    """Short Instagram caption for DoctorShield."""
    lesson_text = " Shaped by real practitioner feedback." if lessons else ""

    if variant == "A":
        body = (
            f"Your patients come first. So should your indemnity cover. "
            f"{topic} in {country} — clear protection for busy practitioners.{lesson_text}"
        )
        hashtags = ["DoctorShield", "MedPractice", "HealthcareHQ", "IndemnitySimplified"]
    else:
        body = (
            f"When was your last indemnity review? "
            f"{goal} starts with a calm, clear conversation — around your schedule.{lesson_text}"
        )
        hashtags = ["DoctorShield", "GPLife", "PractitionerFirst", "MedicalIndemnity"]

    return {"title": None, "body": body, "hashtags": hashtags}


def render_jaguar_instagram(
    topic: str,
    country: str,
    goal: str,
    lessons: list[str],
    variant: str,
) -> dict:
    """Short Instagram caption for Jaguar Logistics Insurance."""
    lesson_text = " Tuned by operational insights." if lessons else ""

    if variant == "A":
        body = (
            f"Cargo moves fast. Your coverage should keep pace. "
            f"{topic} across {country} — secured with precision.{lesson_text}"
        )
        hashtags = ["JaguarLogistics", "Logistics", "FreightTech", "CargoSecured"]
    else:
        body = (
            f"Where does custody risk sit in your supply chain? "
            f"{goal} starts with mapping the gaps, not guessing.{lesson_text}"
        )
        hashtags = ["JaguarLogistics", "SupplyChain", "FreightForwarding", "CargoRisk"]

    return {"title": None, "body": body, "hashtags": hashtags}


# ---------------------------------------------------------------------------
# Unified dispatcher
# ---------------------------------------------------------------------------

_LINKEDIN_RENDERERS = {
    "jade": render_jade,
    "doctorshield": render_doctorshield,
    "jaguar": render_jaguar,
}

_INSTAGRAM_RENDERERS = {
    "jade": render_jade_instagram,
    "doctorshield": render_doctorshield_instagram,
    "jaguar": render_jaguar_instagram,
}


def render_brand(
    brand_id: str,
    topic: str,
    country: str,
    goal: str,
    lessons: list[str],
    variant: str,
    platform: str = "linkedin",
) -> dict:
    """Dispatch to the correct brand + platform renderer.

    Returns ``{"title": ..., "body": ..., "hashtags": [...]}``.
    Falls back to a generic template for unknown brands.
    """
    renderers = _LINKEDIN_RENDERERS if platform == "linkedin" else _INSTAGRAM_RENDERERS

    fn = renderers.get(brand_id)
    if fn is None:
        # Generic fallback — unknown brand, still valid Pydantic-safe output
        content_type_label = "post" if platform == "linkedin" else "caption"
        return {
            "title": f"{topic}: A Specialist View" if platform == "linkedin" else None,
            "body": (
                f"For {country}, {topic.lower()} demands thoughtful risk management. "
                f"{goal} starts with a specialist conversation."
            ),
            "hashtags": ["RiskManagement", "InsurTech"],
        }

    return fn(
        topic=topic,
        country=country,
        goal=goal,
        lessons=lessons,
        variant=variant,
    )


# ---------------------------------------------------------------------------
# Gemini prompt builder
# ---------------------------------------------------------------------------


def build_gemini_prompt(req: "ContentRequest", platform: str, variant: str) -> str:
    """Build the full prompt string to send to Gemini.

    The model is instructed to respond with a single JSON object matching
    the GeneratedAsset fields (platform, content_type, variant, title, body, hashtags).
    """
    voice = BRAND_VOICES.get(req.brand_id, {})
    tone_str = ", ".join(voice.get("tone", ["professional"]))
    themes_str = ", ".join(voice.get("themes", []))
    dont_str = ", ".join(voice.get("dont", []))
    brand_name = voice.get("name", req.brand_id)
    audience = voice.get("audience", "business professionals")

    content_type = "post" if platform == "linkedin" else "caption"
    variant_style = (
        "Direct and headline-driven. Lead with a bold, clear value statement."
        if variant == "A"
        else "Storytelling and question-led. Open with a relatable scenario or question."
    )

    lesson_block = ""
    if req.lessons:
        formatted = "\n".join(f"- {l}" for l in req.lessons)
        lesson_block = (
            f"\n\nPrevious reviewer feedback to incorporate:\n{formatted}"
            f"\nLet these guide tone and emphasis without quoting them directly."
        )

    system_part = (
        f"You are a B2B content specialist writing for {brand_name}.\n"
        f"Audience: {audience}\n"
        f"Tone: {tone_str}\n"
        f"Key themes: {themes_str}\n"
        f"Never use these words or phrases: {dont_str}\n"
        f"Variant style: {variant_style}"
        f"{lesson_block}"
    )

    user_part = (
        f"Write a {platform} {content_type} (variant {variant}) about: {req.topic}\n"
        f"Country context: {req.country}\n"
        f"Campaign goal: {req.goal}\n\n"
        f"Respond ONLY with a JSON object with these exact fields:\n"
        f'{{"platform": "{platform}", "content_type": "{content_type}", '
        f'"variant": "{variant}", "title": "string or null", '
        f'"body": "string (min 50 chars)", '
        f'"hashtags": ["list", "of", "strings", "no", "hash", "prefix"]}}'
    )

    return f"{system_part}\n\n---\n\n{user_part}"
