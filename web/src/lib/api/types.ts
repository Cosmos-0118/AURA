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
  campaign_facts?: CampaignFacts | null;
};

export type CampaignFacts = {
  event_name?: string | null;
  date?: string | null;
  time?: string | null;
  location?: string | null;
  price?: string | null;
  cta?: string | null;
  brand?: string | null;
};

export type CampaignSubmitResult = {
  success: boolean;
  campaign_id: string;
  status: string;
  message: string;
};

export type OperationalModeInfo = {
  demo_mode: boolean;
  groq_model: string;
  image_model: string;
  video_model: string;
};

export type CampaignPublicationItem = {
  id: string;
  campaign_id: string;
  platform: string;
  status: "queued" | "publishing" | "published" | "failed";
  external_post_id?: string | null;
  external_post_url?: string | null;
  published_content?: string | null;
  media_id?: string | null;
  error_message?: string | null;
  published_at?: string | null;
  created_at?: string | null;
};

export type CampaignEventItem = {
  id: string;
  campaign_id: string;
  event_type: string;
  actor: string;
  description?: string | null;
  metadata?: Record<string, unknown> | null;
  created_at: string;
};

export type CampaignReviewCard = {
  review_id: string;
  campaign_id: string;
  review_status: string;
  campaign_status: string;
  reviewer_note?: string | null;
  feedback_tag?: string | null;
  reviewed_at?: string | null;
  queued_at: string;
  brand_id: BrandId;
  campaign_title: string;
  objective: string;
  language: Language;
  thesis: string;
  target_audience?: string | null;
  campaign_facts?: CampaignFacts | null;
  latest_image_url?: string | null;
  latest_image_prompt?: string | null;
  has_video: boolean;
  latest_video_url?: string | null;
  linkedin_content: string;
  linkedin_hashtags: string[];
  publications: Record<string, unknown>;
  events_count: number;
  compliance_passed: boolean;
  lessons_applied_count: number;
};

export type PublishResponse = {
  success: boolean;
  campaign_id: string;
  platform: string;
  status: string;
  external_post_id?: string | null;
  external_post_url?: string | null;
  published_at?: string | null;
  message: string;
};

