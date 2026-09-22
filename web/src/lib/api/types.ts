export type BrandId = 'jade' | 'doctorshield' | 'jaguar';
export type Platform = 'linkedin' | 'instagram' | 'x' | 'blog' | 'reel';
export type ContentType = 'post' | 'thread' | 'caption' | 'carousel' | 'article' | 'script';
export type AssetStatus =
  | 'draft'
  | 'pending_review'
  | 'compliance_failed'
  | 'approved'
  | 'rejected'
  | 'scheduled'
  | 'published';
export type CampaignStatus = 'queued' | 'running' | 'completed' | 'failed';
export type ComplianceVerdict = 'PASS' | 'REVIEW' | 'FAIL';
export type Risk = 'LOW' | 'MEDIUM' | 'HIGH';
export type ReasonTag =
  | 'TOO_SALESY'
  | 'WRONG_CTA'
  | 'UNSUPPORTED_CLAIM'
  | 'WRONG_BRAND_VOICE'
  | 'BAD_LOCALIZATION'
  | 'OTHER';
export type Language = 'en' | 'ms' | 'id' | 'th' | 'zh';

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

export type VideoAspectRatio = '9:16' | '16:9' | '1:1' | '4:3' | '3:4' | '21:9';
export type VideoResolution = '768P' | '1080P' | '480P';
export type VideoPromptExpansion = 'disabled' | 'balanced' | 'quality';

export type VideoGenerateRequest = {
  prompt: string;
  duration?: number; // Capped at max 5 seconds
  aspect_ratio?: VideoAspectRatio;
  resolution?: VideoResolution;
  prompt_expansion_mode?: VideoPromptExpansion;
  asset_id?: string | null;
  brand_id?: string | null;
};

export type VideoFile = {
  file_name?: string | null;
  url: string;
  content_type: string;
  file_size?: number | null;
};

export type VideoGenerateResponse = {
  status: 'COMPLETED' | 'IN_PROGRESS' | 'IN_QUEUE' | 'FAILED';
  request_id?: string | null;
  video?: VideoFile | null;
  expanded_prompt?: string | null;
  asset_id?: string | null;
  error?: string | null;
  logs: string[];
};

export type VideoAttachRequest = {
  asset_id: string;
  video_url: string;
};

export type VideoSaveExportRequest = {
  id: string;
  branded_video_url: string;
  branded_file_name?: string | null;
};

export type VideoConfig = {
  model: string;
  max_duration_seconds: number;
  default_aspect_ratio: VideoAspectRatio;
  supported_aspect_ratios: VideoAspectRatio[];
  supported_resolutions: VideoResolution[];
  prompt_presets: Record<string, string>;
};

export type VideoGenerationRecord = {
  id: string;
  brand_id?: string | null;
  asset_id?: string | null;
  prompt: string;
  aspect_ratio: string;
  resolution: string;
  duration_secs: number;
  model: string;
  video_url?: string | null;
  file_name?: string | null;
  file_size?: number | null;
  branded_video_url?: string | null;
  branded_file_name?: string | null;
  status: 'COMPLETED' | 'FAILED' | 'IN_PROGRESS';
  error_msg?: string | null;
  request_id?: string | null;
  created_at: string; // ISO 8601
};
