"""Content engine — Team Member 4.

Public surface (frozen contract):
    generate_content(req: ContentRequest) -> list[GeneratedAsset]

Graph.py imports this when AURA_MOCK_AGENTS=false.
Deterministic A/B variants ship first; Gemini upgrade is layered on top.
"""

from __future__ import annotations

import json
import os

import httpx

try:
    from ..schemas import ContentRequest, GeneratedAsset
    from ..prompts.content.linkedin import (
        build_gemini_prompt,
        render_brand,
    )
except ImportError:  # Supports `cd api && uv run uvicorn main:app`
    from schemas import ContentRequest, GeneratedAsset  # type: ignore[no-redef]
    from prompts.content.linkedin import build_gemini_prompt, render_brand  # type: ignore[no-redef]

# ---------------------------------------------------------------------------
# Gemini configuration (optional — missing key → deterministic only)
# ---------------------------------------------------------------------------

_GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
_BANNED_WORDS = ("guaranteed", "100% covered", "zero risk")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _call_gemini(prompt: str) -> dict | None:
    """Call Gemini REST API. Return parsed dict or None on ANY failure."""
    if not _GEMINI_API_KEY or _GEMINI_API_KEY == "your_personal_gemini_key":
        return None
    try:
        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{_GEMINI_MODEL}:generateContent",
            params={"key": _GEMINI_API_KEY},
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"responseMimeType": "application/json"},
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        raw_text = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
        return json.loads(raw_text)
    except Exception:
        return None  # always fall back — never propagate


def _validate_gemini_output(data: dict, expected_platform: str) -> bool:
    """Treat model output as untrusted. Reject anything that looks wrong."""
    required = {"platform", "content_type", "body"}
    if not required.issubset(data.keys()):
        return False
    if data.get("platform") != expected_platform:
        return False
    body = data.get("body", "")
    if not body or len(body) < 20:
        return False
    lower = body.lower()
    if any(w in lower for w in _BANNED_WORDS):
        return False
    return True


def _deterministic_asset(
    req: ContentRequest,
    platform: str,
    variant: str,
) -> GeneratedAsset:
    """Return a brand-voiced deterministic asset (no network calls)."""
    rendered = render_brand(
        brand_id=req.brand_id,
        topic=req.topic,
        country=req.country,
        goal=req.goal,
        lessons=req.lessons,
        variant=variant,
        platform=platform,
    )
    content_type = "post" if platform == "linkedin" else "caption"
    return GeneratedAsset(
        platform=platform,
        content_type=content_type,
        variant=variant,
        title=rendered["title"],
        body=rendered["body"],
        hashtags=rendered["hashtags"],
    )


# ---------------------------------------------------------------------------
# Public contract — the only function M1 calls
# ---------------------------------------------------------------------------


def generate_content(req: ContentRequest) -> list[GeneratedAsset]:
    """Generate A/B content for each requested platform.

    Flow per (platform, variant):
      1. Try Gemini if key present → validate → use if valid
      2. Fall back to deterministic template on any failure

    LinkedIn always produces variants A and B.
    Other platforms produce variants A and B where supported.
    """
    assets: list[GeneratedAsset] = []

    for platform in req.platforms:
        if platform not in ("linkedin", "instagram"):
            # Only LinkedIn (must) and Instagram (stretch) — skip the rest
            continue

        for variant in ("A", "B"):
            gemini_raw = _call_gemini(build_gemini_prompt(req, platform, variant))
            if gemini_raw and _validate_gemini_output(gemini_raw, platform):
                content_type = "post" if platform == "linkedin" else "caption"
                # Ensure hashtags is always a list of strings without '#'
                raw_tags = gemini_raw.get("hashtags", [])
                hashtags = [
                    t.lstrip("#") for t in raw_tags if isinstance(t, str)
                ]
                asset = GeneratedAsset(
                    platform=platform,
                    content_type=gemini_raw.get("content_type", content_type),
                    variant=variant,
                    title=gemini_raw.get("title"),
                    body=gemini_raw["body"],
                    hashtags=hashtags,
                )
            else:
                asset = _deterministic_asset(req, platform, variant)

            assets.append(asset)

    return assets
