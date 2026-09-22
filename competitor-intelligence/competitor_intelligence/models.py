from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Competitor:
    id: str
    brand_id: str
    name: str
    niche: str
    countries: list[str]
    url: str
    priority: str = "medium"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class Snapshot:
    id: str
    competitor_id: str
    content_hash: str
    content: str
    source: str
    source_key: str
    source_url: str | None
    market: str | None
    scraped_at: str
    change_summary: str | None = None

    def to_dict(self, include_content: bool = False) -> dict[str, Any]:
        data = asdict(self)
        if not include_content:
            data.pop("content", None)
        return data


@dataclass(slots=True)
class ChangeEvent:
    id: str
    competitor_id: str
    brand_id: str
    country: str | None
    change_type: str
    impact: str
    source: str
    source_url: str | None
    summary: str
    previous_value: str | None
    current_value: str | None
    why_it_matters: str
    recommended_action: str
    evidence: str
    confidence: float
    detected_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
