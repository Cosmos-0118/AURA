from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


RELATIONSHIP_TYPES = frozenset(
    {
        "DIRECT_COMPETITOR",
        "INDIRECT_COMPETITOR",
        "PARTNER",
        "UNDERWRITER",
        "DISTRIBUTOR",
        "SECURE_LOGISTICS_COMPETITOR",
        "ADJACENT",
    }
)
PRIORITY_TYPES = frozenset({"high", "medium", "low"})


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _organization_slug(name: str) -> str:
    slug = "".join(character.lower() if character.isalnum() else "-" for character in name)
    return "-".join(part for part in slug.split("-") if part)


@dataclass(slots=True)
class Competitor:
    id: str
    brand_id: str
    name: str
    niche: str
    countries: list[str]
    url: str
    priority: str = "medium"
    organization_id: str = ""
    relationship: str = "DIRECT_COMPETITOR"
    market: str = ""
    product_category: str = ""
    monitor: bool = True
    retired: bool = False

    def __post_init__(self) -> None:
        if self.relationship not in RELATIONSHIP_TYPES:
            allowed = ", ".join(sorted(RELATIONSHIP_TYPES))
            raise ValueError(f"Unsupported competitor relationship {self.relationship!r}; expected one of {allowed}")
        if self.priority not in PRIORITY_TYPES:
            raise ValueError(f"Unsupported competitor priority {self.priority!r}")
        if not self.organization_id:
            self.organization_id = _organization_slug(self.name)
        if not self.market:
            self.market = ", ".join(self.countries)
        if not self.product_category:
            self.product_category = self.niche

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
