# Contracts (frozen after T+1.5h)

**Owner: Team Member 1.** Everyone else treats this file as law.

**6–8 hour sprint:** implement brands, campaigns, assets, reviews, lessons, metrics. Endpoints for competitors scan, localize, leads, and regenerate may return `501` with `{ "detail": "not in this sprint" }` unless the slice is already done. Do not let those endpoints block the demo.

If you need a change: follow the request template in [04-WORKFLOW-RULES.md](04-WORKFLOW-RULES.md). Do not add fields in your own code.

Status values, table names, JSON keys, and function signatures below are the integration surface. Spell them identically.

---

## 1. Enums (use these strings everywhere)

### `content_assets.status`

| Value | Meaning |
|---|---|
| `draft` | Pipeline still writing (rare in UI) |
| `pending_review` | In the Review Queue |
| `compliance_failed` | Scanner/LLM said FAIL; **still shown in Review Queue** |
| `approved` | Human approved |
| `rejected` | Human rejected |
| `scheduled` | Reserved, unused in UI |
| `published` | Reserved, unused in UI |

Queue query for M2: `status IN ('pending_review', 'compliance_failed')`.

### `content_assets.platform`

`linkedin` | `instagram` | `x` | `blog` | `reel`

### `content_assets.content_type`

`post` | `thread` | `caption` | `carousel` | `article` | `script`

### `campaigns.status`

`queued` | `running` | `completed` | `failed`

### `compliance_checks.result`

`PASS` | `REVIEW` | `FAIL`

### `compliance_checks.risk`

`LOW` | `MEDIUM` | `HIGH`

### Reason tags (reject / lesson)

`TOO_SALESY` | `WRONG_CTA` | `UNSUPPORTED_CLAIM` | `WRONG_BRAND_VOICE` | `BAD_LOCALIZATION` | `OTHER`

### Brand ids (seed)

`jade` | `doctorshield` | `jaguar`

### Languages

`en` | `ms` | `id` | `th` | `zh`

---

## 2. Database schema

Team Member 1 pastes this into Supabase as `db/schema.sql`.

```sql
-- AURA schema. Owner: Team Member 1.

create extension if not exists "pgcrypto";

create table if not exists brands (
  id            text primary key,          -- jade | doctorshield | jaguar
  name          text not null,
  tone          jsonb not null,            -- ["authoritative","premium"]
  audience      text not null,
  do_list       jsonb not null default '[]',
  dont_list     jsonb not null default '[]',
  created_at    timestamptz not null default now()
);

create table if not exists competitors (
  id            uuid primary key default gen_random_uuid(),
  brand_id      text not null references brands(id),
  name          text not null,
  url           text not null,
  created_at    timestamptz not null default now()
);

create table if not exists research_snapshots (
  id            uuid primary key default gen_random_uuid(),
  competitor_id uuid not null references competitors(id) on delete cascade,
  content_hash  text not null,
  content       text not null,
  change_summary text,
  scraped_at    timestamptz not null default now()
);

create table if not exists campaigns (
  id            uuid primary key default gen_random_uuid(),
  brand_id      text not null references brands(id),
  topic         text not null,
  country       text not null,
  goal          text not null,
  platforms     jsonb not null,            -- ["linkedin","instagram"]
  language      text not null default 'en',
  status        text not null default 'queued'
                check (status in ('queued','running','completed','failed')),
  error         text,
  created_at    timestamptz not null default now(),
  completed_at  timestamptz
);

create table if not exists content_assets (
  id            uuid primary key default gen_random_uuid(),
  campaign_id   uuid references campaigns(id) on delete set null,
  brand_id      text not null references brands(id),
  platform      text not null,
  content_type  text not null,
  variant       text not null default 'A',  -- A | B | loc-ms | etc
  language      text not null default 'en',
  title         text,
  body          text not null,              -- carousel: JSON array of slides as text
  hashtags      jsonb not null default '[]',
  media_url     text,
  status        text not null default 'pending_review'
                check (status in (
                  'draft','pending_review','compliance_failed',
                  'approved','rejected','scheduled','published'
                )),
  created_at    timestamptz not null default now(),
  approved_at   timestamptz,
  approved_by   text
);

create table if not exists compliance_checks (
  id            uuid primary key default gen_random_uuid(),
  asset_id      uuid not null references content_assets(id) on delete cascade,
  result        text not null check (result in ('PASS','REVIEW','FAIL')),
  risk          text not null check (risk in ('LOW','MEDIUM','HIGH')),
  rules         jsonb not null default '[]',   -- ["CLAIM_001"]
  issues        jsonb not null default '[]',   -- [{text, reason, rule_id}]
  suggested_revision text,
  created_at    timestamptz not null default now()
);

create table if not exists reviews (
  id            uuid primary key default gen_random_uuid(),
  asset_id      uuid not null references content_assets(id) on delete cascade,
  action        text not null check (action in ('approve','reject','edit')),
  reason_tag    text,
  note          text,
  original_body text,
  edited_body   text,
  created_at    timestamptz not null default now()
);

create table if not exists lessons (
  id            uuid primary key default gen_random_uuid(),
  brand_id      text not null references brands(id),
  platform      text,
  reason_tag    text not null,
  note          text not null,
  original_body text,
  edited_body   text,
  asset_id      uuid references content_assets(id) on delete set null,
  created_at    timestamptz not null default now()
);

create table if not exists leads (
  id            uuid primary key default gen_random_uuid(),
  brand_id      text not null references brands(id),
  name          text not null,
  url           text,
  country       text,
  fit_score     int not null default 0,
  why           text,
  created_at    timestamptz not null default now()
);

create index if not exists idx_assets_status on content_assets(status);
create index if not exists idx_assets_brand on content_assets(brand_id);
create index if not exists idx_lessons_brand on lessons(brand_id);
create index if not exists idx_checks_asset on compliance_checks(asset_id);
```

Carousel `body` is a JSON string:

```json
["Slide 1 headline + line", "Slide 2 ..."]
```

X threads: `body` is posts joined by `\n---\n`.

---

## 3. Seed data (minimum)

`db/seed.sql` is idempotent. At least:

**brands**

```text
jade          Jade            tone: authoritative, premium, specialist, B2B
              audience: jewellery houses, gold dealers, watch retailers
              dont: guaranteed, 100% covered, cheapest

doctorshield  DoctorShield    tone: reassuring, professional, educational, human
              audience: doctors, clinics
              dont: guaranteed, always covered, claim guaranteed

jaguar        Jaguar Transit  tone: fast, technological, security-focused, operational
              audience: cash-in-transit, valuables logistics
              dont: zero risk, guaranteed
```

**competitors** — one URL per brand (public marketing page).

**content_assets** — optional in seed; required in `db/demo.sql` (see demo script).

---

## 4. Pydantic models

File: `api/schemas.py`. Copy this shape. Extra fields only if M1 adds them here first.

```python
from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

BrandId = Literal["jade", "doctorshield", "jaguar"]
Platform = Literal["linkedin", "instagram", "x", "blog", "reel"]
ContentType = Literal["post", "thread", "caption", "carousel", "article", "script"]
AssetStatus = Literal[
    "draft", "pending_review", "compliance_failed",
    "approved", "rejected", "scheduled", "published",
]
CampaignStatus = Literal["queued", "running", "completed", "failed"]
ComplianceVerdict = Literal["PASS", "REVIEW", "FAIL"]
Risk = Literal["LOW", "MEDIUM", "HIGH"]
ReasonTag = Literal[
    "TOO_SALESY", "WRONG_CTA", "UNSUPPORTED_CLAIM",
    "WRONG_BRAND_VOICE", "BAD_LOCALIZATION", "OTHER",
]
Language = Literal["en", "ms", "id", "th", "zh"]

class Brand(BaseModel):
    id: BrandId
    name: str
    tone: list[str]
    audience: str
    do_list: list[str] = []
    dont_list: list[str] = []

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
    lessons: list[str] = []
    research_summary: str | None = None

class GeneratedAsset(BaseModel):
    platform: Platform
    content_type: ContentType
    variant: str = "A"
    title: str | None = None
    body: str
    hashtags: list[str] = []

class ComplianceIssue(BaseModel):
    text: str
    reason: str
    rule_id: str

class ComplianceResult(BaseModel):
    result: ComplianceVerdict
    risk: Risk
    rules: list[str] = []
    issues: list[ComplianceIssue] = []
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
    hashtags: list[str] = []
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
    rejection_rate: float          # 0.0–1.0
    avg_edits_per_post: float
    first_pass_approval: float     # 0.0–1.0
    compliance_failure_rate: float
    assets_total: int
    assets_pending: int
```

**Every rate returns `0.0` when its denominator is 0.** An empty database must give `GET /api/metrics` a 200 with zeros, not a divide-by-zero 500. M3's Insights page is the first screen to hit this at T+3.

JSON from FastAPI uses **snake_case**, same as Python. The TypeScript types below also use snake_case. Do not camelCase in the API.

---

## 5. Agent function signatures

M1's `graph.py` imports these. File paths are fixed. If the real file is missing, M1 imports from `agents._stubs`.

```python
# api/agents/content.py     OWNER: Team Member 4
from schemas import ContentRequest, GeneratedAsset

def generate_content(req: ContentRequest) -> list[GeneratedAsset]:
    ...

# api/agents/localize.py    OWNER: Team Member 4
def localize(
    asset: GeneratedAsset,
    language: str,
    country: str,
    brand_id: str,
) -> GeneratedAsset:
    ...

# api/agents/compliance.py  OWNER: Team Member 5
from schemas import ComplianceResult

def check_compliance(text: str, brand_id: str, platform: str) -> ComplianceResult:
    ...

# api/agents/lessons.py     OWNER: Team Member 5
def get_relevant_lessons(brand_id: str, platform: str, limit: int = 5) -> list[str]:
    """Return note strings, newest first, filtered by brand (and platform if possible)."""
    ...

def record_lesson(
    asset_id: str,
    reason_tag: str,
    note: str,
    original: str,
    edited: str | None,
    brand_id: str,
    platform: str | None = None,
) -> None:
    ...

# api/agents/research.py    OWNER: Team Member 5
def scan_competitor(competitor_id: str) -> dict:
    """
    {
      "competitor_id": str,
      "hash": str,
      "changed": bool,
      "summary": str | None
    }
    """
    ...

# api/agents/leads.py       OWNER: Team Member 5 (stub only this sprint)
def find_leads(brand_id: str, country: str, limit: int = 10) -> list[dict]:
    ...
```

**Rules for M4/M5:**

- Do not change argument names or return types.
- Never raise to kill the campaign. Catch Gemini errors and return a mock or a FAIL result.
- Do not import FastAPI. Do not create routes. Do not write to tables except `lessons`, `research_snapshots`, `leads` (M5). M1 writes `content_assets` and `compliance_checks`.
- M5 `check_compliance` is **pure** (no DB write). M1 stores the returned `ComplianceResult`.

---

## 6. REST API

Base URL: `http://localhost:8000`

All JSON. No auth header for the hackathon.

| Method | Path | Body | Response |
|---|---|---|---|
| GET | `/api/health` | — | `{ "ok": true }` |
| GET | `/api/brands` | — | `Brand[]` |
| GET | `/api/brands/{id}` | — | `Brand` |
| GET | `/api/competitors` | `?brand_id=` | `Competitor[]` |
| POST | `/api/competitors/{id}/scan` | — | `Snapshot` |
| POST | `/api/campaigns` | `CampaignCreate` | `Campaign` (status `running`) |
| GET | `/api/campaigns/{id}` | — | `Campaign` |
| GET | `/api/campaigns` | `?brand_id=` | `Campaign[]` |
| GET | `/api/assets` | `?status=&brand_id=&platform=` | `Asset[]` (each includes latest `compliance`) |
| GET | `/api/assets/{id}` | — | `Asset` |
| POST | `/api/assets/{id}/approve` | `ReviewAction` | `Asset` |
| POST | `/api/assets/{id}/reject` | `ReviewAction` | `Asset` |
| PATCH | `/api/assets/{id}` | `{ "body": "...", "title": "..." }` | `Asset` |
| POST | `/api/assets/{id}/regenerate` | — | `Asset` (new row) |
| POST | `/api/assets/{id}/localize` | `{ "language": "ms", "country": "Malaysia" }` | `Asset` (new row) |
| GET | `/api/lessons` | `?brand_id=` | `Lesson[]` |
| GET | `/api/leads` | `?brand_id=` | `Lead[]` |
| GET | `/api/metrics` | — | `Metrics` |

Errors: `{ "detail": "string" }` with 4xx/5xx.

`POST /api/campaigns` returns immediately. Poll `GET /api/campaigns/{id}` until `completed` or `failed`. Then `GET /api/assets?campaign_id=` — **add query `campaign_id`** (M1: implement this filter even though it is not in the short list above).

Confirmed extra query params M1 **must** implement:

- `GET /api/assets?campaign_id=<uuid>`
- `GET /api/assets?status=pending_review` (single status). For the queue, M2 will call twice or M1 accepts comma: `pending_review,compliance_failed`. **M1 implements:** if `status` omitted, return all; if `status=queue`, return pending_review + compliance_failed.

---

## 7. TypeScript types

File: `web/src/lib/api/types.ts` — M1 writes this. M2/M3 only import.

```ts
export type BrandId = "jade" | "doctorshield" | "jaguar";
export type Platform = "linkedin" | "instagram" | "x" | "blog" | "reel";
export type ContentType =
  | "post"
  | "thread"
  | "caption"
  | "carousel"
  | "article"
  | "script";
export type AssetStatus =
  | "draft"
  | "pending_review"
  | "compliance_failed"
  | "approved"
  | "rejected"
  | "scheduled"
  | "published";
export type CampaignStatus = "queued" | "running" | "completed" | "failed";
export type ComplianceVerdict = "PASS" | "REVIEW" | "FAIL";
export type Risk = "LOW" | "MEDIUM" | "HIGH";
export type ReasonTag =
  | "TOO_SALESY"
  | "WRONG_CTA"
  | "UNSUPPORTED_CLAIM"
  | "WRONG_BRAND_VOICE"
  | "BAD_LOCALIZATION"
  | "OTHER";
export type Language = "en" | "ms" | "id" | "th" | "zh";

export type Brand = {
  id: BrandId;
  name: string;
  tone: string[];
  audience: string;
  do_list: string[];
  dont_list: string[];
};

export type Competitor = {
  id: string;
  brand_id: BrandId;
  name: string;
  url: string;
};

export type Snapshot = {
  id: string;
  competitor_id: string;
  content_hash: string;
  change_summary: string | null;
  scraped_at: string;
};

export type CampaignCreate = {
  brand_id: BrandId;
  topic: string;
  country: string;
  goal: string;
  platforms: Platform[];
  language?: Language;
};

export type Campaign = {
  id: string;
  brand_id: BrandId;
  topic: string;
  country: string;
  goal: string;
  platforms: Platform[];
  language: Language;
  status: CampaignStatus;
  error: string | null;
  created_at: string;
  completed_at: string | null;
};

export type ComplianceIssue = {
  text: string;
  reason: string;
  rule_id: string;
};

export type ComplianceResult = {
  result: ComplianceVerdict;
  risk: Risk;
  rules: string[];
  issues: ComplianceIssue[];
  suggested_revision: string | null;
};

export type Asset = {
  id: string;
  campaign_id: string | null;
  brand_id: BrandId;
  platform: Platform;
  content_type: ContentType;
  variant: string;
  language: Language;
  title: string | null;
  body: string;
  hashtags: string[];
  media_url: string | null;
  status: AssetStatus;
  compliance: ComplianceResult | null;
  created_at: string;
  approved_at: string | null;
  approved_by: string | null;
};

export type ReviewAction = {
  reason_tag?: ReasonTag;
  note?: string;
  edited_body?: string;
  approved_by?: string;
};

export type Lesson = {
  id: string;
  brand_id: BrandId;
  platform: Platform | null;
  reason_tag: ReasonTag;
  note: string;
  original_body: string | null;
  edited_body: string | null;
  created_at: string;
};

export type Lead = {
  id: string;
  brand_id: BrandId;
  name: string;
  url: string | null;
  country: string | null;
  fit_score: number;
  why: string | null;
};

export type Metrics = {
  rejection_rate: number;
  avg_edits_per_post: number;
  first_pass_approval: number;
  compliance_failure_rate: number;
  assets_total: number;
  assets_pending: number;
};
```

Typed fetchers live in `web/src/lib/api/client.ts` (M1). Example names M2/M3 must use:

```ts
getBrands()
getBrand(id)
getCompetitors(brandId?)
scanCompetitor(id)
createCampaign(body: CampaignCreate)
getCampaign(id)
listCampaigns(brandId?)
listAssets(params: { status?: string; brand_id?: string; platform?: string; campaign_id?: string })
getAsset(id)
approveAsset(id, body?: ReviewAction)
rejectAsset(id, body: ReviewAction)
patchAsset(id, body: { body?: string; title?: string })
regenerateAsset(id)
localizeAsset(id, body: { language: Language; country: string })
listLessons(brandId?)
listLeads(brandId?)
getMetrics()
```

---

## 8. Nav items (M1 writes `web/src/config/nav-config.ts`)

Routes M2/M3 will create. M1 registers them so the sidebar works before pages exist (placeholder page is OK).

```text
/dashboard                     Overview (leave the starter; ignore it in the demo)
/dashboard/studio              Campaign Studio          M3  MUST
/dashboard/review              Review Queue             M2  MUST
/dashboard/brands              Brands                   M3  MUST
/dashboard/insights            Insights                 M3  MUST
```

Four items. Do **not** add Library, Competitors, Leads, Chat, or Calendar to the sidebar — nobody is building those pages, and a sidebar link that 404s in front of judges is worse than a missing one.

---

## 9. Pipeline behaviour M1 implements in `graph.py`

```text
load brand
lessons = get_relevant_lessons(brand, "linkedin")   # one call, not one per platform
assets = generate_content(ContentRequest(..., lessons, research_summary=None))
# skip competitor scan in this sprint
for each asset:
    check = check_compliance(asset.body, brand_id, asset.platform)
    status = "compliance_failed" if check.result == "FAIL" else "pending_review"
    INSERT content_assets
    INSERT compliance_checks
campaign.status = completed
```

Reject path:

```text
UPDATE asset status=rejected
INSERT reviews
record_lesson(..., note = note or reason_tag, ...)
```

**`lessons.note` is `NOT NULL`.** The reviewer UI does not force a note, so M1 must pass `note or reason_tag` (never `None`) and M5's `record_lesson` must coalesce defensively. A null note here is a 500 on the loudest click of the demo.

Approve path:

```text
if edited_body: UPDATE body
UPDATE status=approved, approved_at=now()
INSERT reviews action=approve (or edit)
if edited_body and differs: record_lesson as well
```

---

## 10. Mock payloads (so UI work starts before Gemini)

`GET /api/assets?status=queue` should be able to return at least one of these from seed/demo:

Jade Instagram FAIL:

```json
{
  "brand_id": "jade",
  "platform": "instagram",
  "content_type": "caption",
  "variant": "A",
  "language": "en",
  "title": null,
  "body": "Guaranteed protection for your jewellery business. Sleep easy — every piece is 100% covered.",
  "hashtags": ["#Jade", "#Jewellery"],
  "status": "compliance_failed",
  "compliance": {
    "result": "FAIL",
    "risk": "HIGH",
    "rules": ["CLAIM_001", "CLAIM_002"],
    "issues": [
      {
        "text": "Guaranteed protection",
        "reason": "Unsupported absolute insurance claim",
        "rule_id": "CLAIM_001"
      }
    ],
    "suggested_revision": "Specialist cover designed for jewellery businesses, subject to policy terms."
  }
}
```

That object is the visual spec for Team Member 2's review panel.
