from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

BrandId = Literal["jade", "doctorshield", "jaguar"]
Platform = Literal["linkedin", "instagram", "x", "blog", "reel"]
ContentType = Literal["post", "thread", "caption", "carousel", "article", "script"]
AssetStatus = Literal[
    "draft",
    "pending_review",
    "compliance_failed",
    "approved",
    "rejected",
    "scheduled",
    "published",
]
CampaignStatus = Literal["queued", "running", "completed", "failed"]
ComplianceVerdict = Literal["PASS", "REVIEW", "FAIL"]
Risk = Literal["LOW", "MEDIUM", "HIGH"]
ReasonTag = Literal[
    "TOO_SALESY",
    "WRONG_CTA",
    "UNSUPPORTED_CLAIM",
    "WRONG_BRAND_VOICE",
    "BAD_LOCALIZATION",
    "OTHER",
]
Language = Literal["en", "ms", "id", "th", "zh"]


class Brand(BaseModel):
    id: BrandId
    name: str
    tone: list[str]
    audience: str
    do_list: list[str] = Field(default_factory=list)
    dont_list: list[str] = Field(default_factory=list)


class Competitor(BaseModel):
    id: str
    brand_id: BrandId
    name: str
    url: str


class Snapshot(BaseModel):
    id: str
    competitor_id: str
    content_hash: str
    change_summary: str | None = None
    scraped_at: datetime


class ContentRequest(BaseModel):
    brand_id: BrandId
    topic: str
    country: str
    goal: str
    platforms: list[Platform]
    language: Language = "en"
    lessons: list[str] = Field(default_factory=list)
    research_summary: str | None = None


class GeneratedAsset(BaseModel):
    platform: Platform
    content_type: ContentType
    variant: str = "A"
    title: str | None = None
    body: str
    hashtags: list[str] = Field(default_factory=list)


class ComplianceIssue(BaseModel):
    text: str
    reason: str
    rule_id: str


class ComplianceResult(BaseModel):
    result: ComplianceVerdict
    risk: Risk
    rules: list[str] = Field(default_factory=list)
    issues: list[ComplianceIssue] = Field(default_factory=list)
    suggested_revision: str | None = None


class CampaignCreate(BaseModel):
    brand_id: BrandId
    topic: str
    country: str
    goal: str
    platforms: list[Platform]
    language: Language = "en"


class Campaign(BaseModel):
    id: str
    brand_id: BrandId
    topic: str
    country: str
    goal: str
    platforms: list[Platform]
    language: Language
    status: CampaignStatus
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class Asset(BaseModel):
    id: str
    campaign_id: str | None = None
    brand_id: BrandId
    platform: Platform
    content_type: ContentType
    variant: str
    language: Language
    title: str | None = None
    body: str
    hashtags: list[str] = Field(default_factory=list)
    media_url: str | None = None
    status: AssetStatus
    compliance: ComplianceResult | None = None
    created_at: datetime
    approved_at: datetime | None = None
    approved_by: str | None = None


class ReviewAction(BaseModel):
    reason_tag: ReasonTag | None = None
    note: str | None = None
    edited_body: str | None = None
    approved_by: str | None = "reviewer"


class AssetPatch(BaseModel):
    body: str | None = None
    title: str | None = None


class LocalizeRequest(BaseModel):
    language: Language
    country: str


class Lesson(BaseModel):
    id: str
    brand_id: BrandId
    platform: Platform | None = None
    reason_tag: ReasonTag
    note: str
    original_body: str | None = None
    edited_body: str | None = None
    created_at: datetime


class Lead(BaseModel):
    id: str
    brand_id: BrandId
    name: str
    url: str | None = None
    country: str | None = None
    fit_score: int
    why: str | None = None


class Metrics(BaseModel):
    rejection_rate: float
    avg_edits_per_post: float
    lessons_count: int
    compliance_failure_rate: float
    assets_total: int
    assets_pending: int
