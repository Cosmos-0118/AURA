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
  lessons_count: number;
  compliance_failure_rate: number;
  assets_total: number;
  assets_pending: number;
};

export type StudioCampaignCreate = {
  brand_id: BrandId;
  objective: string;
  language: Language;
  thesis: string;
  target_audience?: string;
  platforms: Platform[];
};

export type CampaignPlatformContentItem = {
  id: string;
  campaign_id: string;
  platform: Platform;
  title?: string | null;
  content: string;
  hashtags: string[];
  script?: string | null;
  visual_concept?: string | null;
  generation_prompt?: string | null;
};

export type CampaignMediaItem = {
  id: string;
  campaign_id: string;
  media_type: "image" | "video";
  prompt: string;
  local_path?: string | null;
  provider: string;
  model: string;
  status: string;
};

export type StudioCampaignDetail = {
  id: string;
  brand_id: BrandId;
  objective: string;
  language: Language;
  thesis: string;
  target_audience?: string | null;
  platforms: Platform[];
  status: string;
  error?: string | null;
  created_at: string;
  updated_at?: string | null;
  contents: CampaignPlatformContentItem[];
  media: CampaignMediaItem[];
  image_prompt?: string | null;
  video_prompt?: string | null;
};

export type OperationalModeInfo = {
  demo_mode: boolean;
  groq_model: string;
  image_model: string;
  video_model: string;
};

