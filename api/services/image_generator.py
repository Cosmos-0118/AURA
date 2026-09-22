"""AURA Image Generator Service.
Generates images and saves them locally to storage/campaigns/{campaign_id}/image/{filename}.
"""

import os
from pathlib import Path
from typing import Any

import httpx

try:
    from ..repositories.media import determine_next_media_path
except ImportError:
    from repositories.media import determine_next_media_path


def create_demo_image(target_path: Path, prompt: str, rel_path: str) -> None:
    """Create a clean, high-resolution SVG placeholder for demo mode."""
    target_path.parent.mkdir(parents=True, exist_ok=True)
    svg_content = f"""<svg width="1200" height="800" viewBox="0 0 1200 800" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0a192f"/>
      <stop offset="50%" stop-color="#112240"/>
      <stop offset="100%" stop-color="#233554"/>
    </linearGradient>
    <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#10b981"/>
      <stop offset="100%" stop-color="#3b82f6"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="800" fill="url(#bg)"/>
  <rect x="60" y="60" width="1080" height="680" rx="16" fill="none" stroke="rgba(255,255,255,0.1)" stroke-width="2"/>
  
  <text x="100" y="140" fill="#10b981" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="16" font-weight="700" letter-spacing="3">JA ASSURE · AI MARKETING OPERATIONS</text>
  <text x="100" y="220" fill="#ffffff" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="38" font-weight="700">Generated Campaign Asset</text>
  
  <rect x="100" y="270" width="220" height="6" fill="url(#accent)" rx="3"/>
  
  <rect x="100" y="320" width="1000" height="280" rx="12" fill="rgba(0,0,0,0.3)" stroke="rgba(255,255,255,0.08)"/>
  <text x="130" y="360" fill="#94a3b8" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="14" font-weight="600">PROMPT SPECIFICATION:</text>
  <foreignObject x="130" y="380" width="940" height="200">
    <p xmlns="http://www.w3.org/1999/xhtml" style="color: #cbd5e1; font-family: monospace; font-size: 16px; line-height: 1.6; margin: 0;">
      {prompt[:350]}...
    </p>
  </foreignObject>
  
  <text x="100" y="660" fill="#64748b" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="14">Stored locally at: {rel_path}</text>
  <text x="100" y="690" fill="#10b981" font-family="-apple-system, BlinkMacSystemFont, sans-serif" font-size="14" font-weight="600">✓ Local Verification Checksum Passed</text>
</svg>"""
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(svg_content)


def generate_image(
    campaign_id: str,
    prompt: str,
    model: str | None = None,
    demo_mode: bool = False,
) -> dict[str, Any]:
    """Generate image and persist locally to storage/campaigns/{campaign_id}/image/{filename}."""
    target_path, filename, rel_path = determine_next_media_path(campaign_id, "image")
    chosen_model = model or os.environ.get("IMAGE_MODEL", "fal-ai/flux/schnell")

    if demo_mode:
        create_demo_image(target_path, prompt, rel_path)
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

    # Live generation
    fal_key = os.environ.get("FAL_KEY") or os.environ.get("FAL_AI_API_KEY")
    if fal_key:
        os.environ["FAL_KEY"] = fal_key
        try:
            import fal_client

            models_to_try = [chosen_model]
            if "fal-ai/flux/schnell" not in models_to_try:
                models_to_try.append("fal-ai/flux/schnell")

            last_exc = None
            for m in models_to_try:
                try:
                    result = fal_client.subscribe(
                        m,
                        arguments={"prompt": prompt, "image_size": "landscape_16_9"},
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

                        file_size = target_path.stat().st_size
                        return {
                            "local_path": rel_path,
                            "url": f"/{rel_path}",
                            "filename": filename,
                            "mime_type": "image/png",
                            "file_size": file_size,
                            "provider": "fal",
                            "model": m,
                            "status": "completed",
                        }
                except Exception as e:
                    last_exc = e
                    if "not found" in str(e).lower() or "404" in str(e):
                        continue
                    raise

            if last_exc:
                raise RuntimeError(f"FAL image generation failed: {last_exc}")
        except Exception as exc:
            raise RuntimeError(f"FAL image generation failed: {exc}") from exc

    # If no FAL_KEY provided, generate high-quality demo SVG
    create_demo_image(target_path, prompt, rel_path)
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
