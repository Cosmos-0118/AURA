"""Localization stub — reserved, out of this sprint (Team Member 4).

This function is part of the frozen contract but localisation is explicitly
out of scope for the hackathon sprint.  It returns the asset unchanged so
that callers can wire it in without an error.
"""

from __future__ import annotations

try:
    from ..schemas import GeneratedAsset
except ImportError:  # Supports `cd api && uv run uvicorn main:app`
    from schemas import GeneratedAsset  # type: ignore[no-redef]


def localize(
    asset: GeneratedAsset,
    language: str,
    country: str,
    brand_id: str,
) -> GeneratedAsset:
    """Return the asset unchanged.  Localisation is a post-sprint feature."""
    del language, country, brand_id  # unused until localisation is implemented
    return asset.model_copy()
