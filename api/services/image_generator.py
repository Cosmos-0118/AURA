"""AURA Image Generator Service.
Generates images and saves them locally to storage/campaigns/{campaign_id}/image/{filename}.
"""

import logging
import os
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("aura.image_generator")

try:
    from ..repositories.media import determine_next_media_path
except ImportError:
    from repositories.media import determine_next_media_path


def extract_poster_headline(prompt: str) -> tuple[str, str]:
    """Extract or synthesize headline and subheadline text for the poster."""
    import re

    quotes = re.findall(r'"([^"]+)"', prompt)
    if quotes:
        headline = quotes[0].upper()
        subheadline = quotes[1] if len(quotes) > 1 else "COMMERCIAL OPERATIONS DESK"
    else:
        lower = prompt.lower()
        if any(w in lower for w in ["jewel", "vault", "diamond", "jade", "gem"]):
            headline = "COME TO JADE · VAULT AUDIT"
            subheadline = "INSTITUTIONAL JEWELLERY SECURITY · SINGAPORE"
        elif any(w in lower for w in ["doctor", "clinic", "medico", "patient", "shield"]):
            headline = "STAND PROTECTED WITH DOCTORSHIELD"
            subheadline = "PEER-GUIDED MEDICO-LEGAL DEFENSE"
        elif any(w in lower for w in ["logistics", "cargo", "transit", "truck", "jaguar", "freight"]):
            headline = "CHAIN OF CUSTODY ASSURED · JAGUAR TRANSIT"
            subheadline = "REAL-TIME TELEMETRY FREIGHT PROTECTION"
        else:
            words = prompt.replace(":", " ").replace("-", " ").replace(",", " ").split()
            headline = " ".join(words[:4]).upper() if words else "CAMPAIGN POSTER"
            subheadline = "SPECIALIST MARKETING OPERATIONS · JA ASSURE"

    return headline[:40], subheadline[:70]


def ensure_poster_text_overlay(prompt: str) -> str:
    """Ensure prompt explicitly commands bold typography text overlay.
    
    Guarantees prominent text overlay like 'COME TO JADE · VAULT AUDIT' or 'STAND PROTECTED'.
    """
    lower = prompt.lower()
    if "text overlay" in lower and ('"' in prompt or "'" in prompt):
        return prompt

    headline, subheadline = extract_poster_headline(prompt)
    return (
        f'Commercial advertising poster with bold typography text overlay. '
        f'Large prominent headline text overlay across the top reads: "{headline}". '
        f'Secondary sub-headline text overlay reads: "{subheadline}". '
        f'High-contrast graphic design poster layout with legible typography text overlay on top of: {prompt}'
    )


def resolve_fal_model(model_name: str) -> str:
    """Map model name to actual working FAL model endpoint."""
    lower = model_name.lower()
    if "nano-banana" in lower:
        return "fal-ai/nano-banana-2"
    return model_name


def create_demo_image(target_path: Path, prompt: str, rel_path: str) -> None:
    """Create a high-resolution, visually striking SVG marketing poster with typography."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    headline, subheadline = extract_poster_headline(prompt)

    svg_content = f"""<svg width="1200" height="800" viewBox="0 0 1200 800" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="posterBg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#070c14"/>
      <stop offset="40%" stop-color="#0d1b2a"/>
      <stop offset="80%" stop-color="#1b263b"/>
      <stop offset="100%" stop-color="#0a1128"/>
    </linearGradient>
    <linearGradient id="goldGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#f59e0b"/>
      <stop offset="50%" stop-color="#fbbf24"/>
      <stop offset="100%" stop-color="#fef08a"/>
    </linearGradient>
    <linearGradient id="emeraldGrad" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#10b981"/>
      <stop offset="100%" stop-color="#06b6d4"/>
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur" />
      <feComposite in="SourceGraphic" in2="blur" operator="over" />
    </filter>
  </defs>

  <!-- Background Poster Canvas -->
  <rect width="1200" height="800" fill="url(#posterBg)"/>

  <!-- Decorative Outer Poster Border -->
  <rect x="40" y="40" width="1120" height="720" rx="20" fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="2"/>
  <rect x="50" y="50" width="1100" height="700" rx="14" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="1"/>

  <!-- Top Brand Kicker -->
  <rect x="90" y="85" width="8" height="24" fill="url(#emeraldGrad)" rx="4"/>
  <text x="112" y="103" fill="#10b981" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="15" font-weight="800" letter-spacing="4">JA ASSURE · MARKETING OPERATIONS POSTER</text>

  <!-- Poster Big Bold Headline Text Overlay -->
  <text x="90" y="210" fill="url(#goldGrad)" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="52" font-weight="900" letter-spacing="1.5" filter="url(#glow)">
    {headline}
  </text>

  <!-- Poster Subheadline Text Overlay -->
  <text x="90" y="260" fill="#94a3b8" font-family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif" font-size="20" font-weight="600" letter-spacing="2">
    {subheadline.upper()}
  </text>

  <!-- Decorative Accent Divider -->
  <line x1="90" y1="285" x2="450" y2="285" stroke="url(#goldGrad)" stroke-width="4" stroke-linecap="round"/>

  <!-- Visual Artwork Container Mockup -->
  <rect x="90" y="320" width="1020" height="310" rx="14" fill="rgba(0,0,0,0.45)" stroke="rgba(255,255,255,0.1)" stroke-width="1.5"/>

  <!-- Visual Grid Pattern inside card -->
  <circle cx="220" cy="475" r="90" fill="none" stroke="rgba(16,185,129,0.15)" stroke-width="2"/>
  <circle cx="220" cy="475" r="50" fill="none" stroke="rgba(245,158,11,0.2)" stroke-width="2"/>
  <circle cx="220" cy="475" r="20" fill="url(#emeraldGrad)"/>

  <!-- Graphic Badge inside artwork -->
  <rect x="360" y="360" width="160" height="30" rx="6" fill="rgba(16,185,129,0.15)" stroke="rgba(16,185,129,0.4)" stroke-width="1"/>
  <text x="375" y="380" fill="#10b981" font-family="monospace" font-size="12" font-weight="700">★ VERIFIED ASSET</text>

  <!-- Creative Prompt Spec in visual box -->
  <foreignObject x="360" y="410" width="710" height="190">
    <p xmlns="http://www.w3.org/1999/xhtml" style="color: #cbd5e1; font-family: monospace; font-size: 15px; line-height: 1.6; margin: 0;">
      {prompt[:320]}...
    </p>
  </foreignObject>

  <!-- Poster Footer Elements -->
  <text x="90" y="695" fill="#64748b" font-family="monospace" font-size="13">ASSET PATH: {rel_path}</text>
  <text x="1110" y="695" text-anchor="end" fill="#10b981" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="13" font-weight="700">✓ COMPLIANCE &amp; UNDERWRITING CERTIFIED</text>
</svg>"""
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(svg_content)


def find_logo_path(logo_filename: str) -> Path | None:
    """Locate brand or group logo in web/public/logo, public/logo, or storage/logo."""
    project_root = Path(__file__).resolve().parent.parent.parent
    variants = [logo_filename, logo_filename.lower(), logo_filename.capitalize()]
    for fn in variants:
        candidate_paths = [
            project_root / "web" / "public" / "logo" / fn,
            project_root / "public" / "logo" / fn,
            project_root / "web" / "public" / fn,
            project_root / "storage" / "logo" / fn,
        ]
        for p in candidate_paths:
            if p.exists() and p.is_file():
                return p
    return None


def apply_watermark_logos(image_path: Path, brand_id: str | None = None) -> None:
    """Overlay ja.png on bottom-left and {brand_id}.png on bottom-right using Pillow."""
    if not image_path.exists() or image_path.suffix.lower() == ".svg":
        return

    try:
        from PIL import Image

        with Image.open(image_path) as base_img:
            base_img = base_img.convert("RGBA")
            w, h = base_img.size

            target_h = max(40, int(h * 0.08))
            padding_x = max(24, int(w * 0.04))
            padding_y = max(24, int(h * 0.04))

            # 1. JA Assure Logo on Bottom-Left
            ja_path = find_logo_path("ja.png")
            if ja_path:
                try:
                    with Image.open(ja_path) as ja_img:
                        ja_rgba = ja_img.convert("RGBA")
                        scale = target_h / float(ja_rgba.height)
                        target_w = int(ja_rgba.width * scale)
                        ja_resized = ja_rgba.resize((target_w, target_h), Image.Resampling.LANCZOS)
                        pos_x = padding_x
                        pos_y = h - target_h - padding_y
                        base_img.paste(ja_resized, (pos_x, pos_y), ja_resized)
                except Exception as e:
                    logger.warning(f"Failed to overlay ja.png: {e}")

            # 2. Brand Logo on Bottom-Right
            bid = (brand_id or "jade").lower()
            brand_path = find_logo_path(f"{bid}.png") or find_logo_path("jade.png")
            if brand_path:
                try:
                    with Image.open(brand_path) as brand_img:
                        brand_rgba = brand_img.convert("RGBA")
                        scale = target_h / float(brand_rgba.height)
                        target_w = int(brand_rgba.width * scale)
                        brand_resized = brand_rgba.resize((target_w, target_h), Image.Resampling.LANCZOS)
                        pos_x = w - target_w - padding_x
                        pos_y = h - target_h - padding_y
                        base_img.paste(brand_resized, (pos_x, pos_y), brand_resized)
                except Exception as e:
                    logger.warning(f"Failed to overlay brand logo: {e}")

            # Save back to disk
            if image_path.suffix.lower() in [".jpg", ".jpeg"]:
                base_img.convert("RGB").save(image_path, "JPEG", quality=95)
            else:
                base_img.save(image_path, "PNG")
    except Exception as exc:
        logger.warning(f"Logo watermarking skipped: {exc}")


def generate_image(
    campaign_id: str,
    prompt: str,
    model: str | None = None,
    demo_mode: bool = False,
    brand_id: str | None = None,
) -> dict[str, Any]:
    """Generate image, watermark logos, and persist locally to storage/campaigns/{campaign_id}/image/{filename}."""
    target_path, filename, rel_path = determine_next_media_path(campaign_id, "image")
    chosen_model = model or os.environ.get("IMAGE_MODEL", "google/nano-banana-2-lites")

    # Ensure prompt explicitly commands bold typography text overlay
    effective_prompt = ensure_poster_text_overlay(prompt)

    if demo_mode:
        create_demo_image(target_path, effective_prompt, rel_path)
        apply_watermark_logos(target_path, brand_id)
        file_size = target_path.stat().st_size if target_path.exists() else 1024
        return {
            "local_path": rel_path,
            "url": f"/{rel_path}",
            "filename": filename,
            "mime_type": "image/png",
            "file_size": file_size,
            "provider": "demo_local",
            "model": chosen_model,
            "status": "completed",
        }

    # Live generation via FAL AI
    fal_key = os.environ.get("FAL_KEY") or os.environ.get("FAL_AI_API_KEY")
    if fal_key:
        os.environ["FAL_KEY"] = fal_key
        try:
            import fal_client

            candidate_models = [resolve_fal_model(chosen_model)]
            for fallback in ["fal-ai/nano-banana-2", "fal-ai/flux/schnell", "fal-ai/ideogram/v2"]:
                if fallback not in candidate_models:
                    candidate_models.append(fallback)

            last_exc = None
            for m in candidate_models:
                try:
                    logger.info(f"Dispatching image generation to FAL AI model: {m}")
                    args = {
                        "prompt": effective_prompt,
                        "image_size": "landscape_16_9",
                        "num_images": 1,
                    }
                    if "flux/schnell" in m:
                        args["num_inference_steps"] = 4

                    result = fal_client.subscribe(
                        m,
                        arguments=args,
                        with_logs=False,
                    )
                    images = result.get("images", [])
                    if images and "url" in images[0]:
                        image_url = images[0]["url"]
                        with httpx.Client(timeout=30.0) as client:
                            resp = client.get(image_url)
                            resp.raise_for_status()
                            target_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(target_path, "wb") as f:
                                f.write(resp.content)

                        # Apply dual logo watermark
                        apply_watermark_logos(target_path, brand_id)

                        file_size = target_path.stat().st_size
                        return {
                            "local_path": rel_path,
                            "url": f"/{rel_path}",
                            "filename": filename,
                            "mime_type": "image/png",
                            "file_size": file_size,
                            "provider": "fal",
                            "model": chosen_model,
                            "status": "completed",
                        }
                except Exception as e:
                    last_exc = e
                    logger.warning(f"FAL model endpoint {m} failed ({type(e).__name__}: {e}). Trying next fallback model...")
                    continue

            if last_exc:
                logger.error(f"All FAL models failed: {last_exc}. Falling back to demo poster.")
                create_demo_image(target_path, effective_prompt, rel_path)
                file_size = target_path.stat().st_size if target_path.exists() else 1024
                return {
                    "local_path": rel_path,
                    "url": f"/{rel_path}",
                    "filename": filename,
                    "mime_type": "image/png",
                    "file_size": file_size,
                    "provider": "fal_fallback_poster",
                    "model": chosen_model,
                    "status": "completed",
                }
        except Exception as exc:
            logger.error(f"FAL image generation initialization failed: {exc}")

    # If no FAL_KEY provided or live failed, generate high-quality demo SVG poster
    create_demo_image(target_path, effective_prompt, rel_path)
    file_size = target_path.stat().st_size if target_path.exists() else 1024
    return {
        "local_path": rel_path,
        "url": f"/{rel_path}",
        "filename": filename,
        "mime_type": "image/png",
        "file_size": file_size,
        "provider": "local_fallback",
        "model": chosen_model,
        "status": "completed",
    }
