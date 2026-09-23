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
export type CampaignStatus =
  | "draft"
  | "generating"
  | "generated"
  | "pending_review"
  | "approved"
  | "rejected"
  | "edited"
  | "queued"
  | "running"
  | "completed"
  | "failed";
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

export type CompetitorRecord = Competitor & {
  niche: string;
  countries: string[];
  priority: 'high' | 'medium' | 'low';
  organization_id: string;
  relationship: string;
  market: string;
  product_category: string;
  monitor: boolean;
  retired: boolean;
};

export type CompetitorMonitor = {
  competitor_id: string;
  competitor_name: string;
  brand_id: BrandId;
  priority: string;
  organization_id: string;
  relationship: string;
  relationship_market: string;
  product_category: string;
  monitor_enabled: number;
  retired: number;
  source: string | null;
  source_url: string | null;
  market: string | null;
  source_key: string | null;
  last_checked: string | null;
  latest_hash: string | null;
  change_summary: string | null;
  snapshots: number;
  versions: number;
  status: 'not_checked' | 'active' | string;
};

export type CompetitorWatch = {
  id: string;
  competitor_id: string;
  url: string;
  kind: string;
  priority: 'high' | 'medium' | 'low';
  interval_hours: number;
  last_checked: string | null;
};

export type CompetitorEvent = {
  id: string;
  competitor_id: string;
  brand_id: BrandId;
  country: string | null;
  change_type: string;
  impact: 'high' | 'medium' | 'low' | string;
  source: string;
  source_url: string | null;
  summary: string;
  previous_value: string | null;
  current_value: string | null;
  why_it_matters: string;
  recommended_action: string;
  evidence: string;
  confidence: number;
  detected_at: string;
  competitor_name?: string;
  organization_id?: string;
  relationship?: string;
  product_category?: string;
};

export type CompetitorSourceHealth = {
  source: string;
  status: string;
  detail: string;
};

export type CompetitorDashboard = {
  summary: {
    total: number;
    high: number;
    medium: number;
    low: number;
    competitors: number;
    relationships: number;
    organizations: number;
  };
  competitors: CompetitorRecord[];
  monitors: CompetitorMonitor[];
  watches: CompetitorWatch[];
  events: CompetitorEvent[];
  source_health: CompetitorSourceHealth[];
  ready?: boolean;
};

export type CompetitorScanResult = {
  competitor_id: string;
  status: string;
  changed: boolean;
  summary: string | null;
  event_id: string | null;
  error: string | null;
};

export type CompetitorEventAnalysis = {
  summary: string;
  why_it_matters: string;
  recommended_action: string;
  confidence_reason: string;
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
  category?: string | null;
  location?: string | null;
  url: string | null;
  country: string | null;
  fit_score: number;
  why: string | null;
  email?: string | null;
  phone?: string | null;
  requirements?: string | null;
  source_url?: string | null;
  source_title?: string | null;
  public_email?: string | null;
  social_links?: string[];
  description?: string | null;
  services?: string[];
  source?: string;
  status?: string;
  external_place_id?: string | null;
  products?: string[];
  specialties?: string[];
  fit_reasons?: string[];
  last_verified_at?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

export type LeadRefreshStatus = {
  refreshing: boolean;
  configured: boolean;
  last_scraped_at: string | null;
  last_error: string | null;
  updated: number;
  watched: number;
};

export type LeadEmailDraft = {
  from_email: string;
  to_email: string;
  subject: string;
  body: string;
  configured: boolean;
};

export type LeadEmailResult = {
  ok: boolean;
  from_email: string;
  to_email: string;
  subject: string;
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
  version?: number;
  is_current?: boolean;
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
  media_stage?: "original" | "final";
  watermarked?: boolean;
  logo_path?: string | null;
  logo_position?: string | null;
  logo_scale?: number | null;
  logo_opacity?: number | null;
  parent_media_id?: string | null;
  watermark_config?: any;
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
  provider?: string | null;
  buffer_post_id?: string | null;
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

export type VideoAspectRatio = '9:16' | '16:9' | '1:1' | '4:3' | '3:4' | '21:9';
export type VideoResolution = '768P' | '1080P' | '480P';
export type VideoPromptExpansion = 'disabled' | 'balanced' | 'quality';

export type VideoGenerateRequest = {
  prompt: string;
  duration?: number;
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

export type BufferShareMode = 'shareNow' | 'addToQueue' | 'shareNext' | 'customScheduled';
export type BufferInstagramType = 'post' | 'story' | 'reel';

export type BufferStatus = {
  configured: boolean;
  endpoint: string;
};

export type BufferChannel = {
  id: string;
  name: string;
  display_name: string;
  service: string;
  avatar: string;
  is_queue_paused: boolean;
  organization_id: string;
  organization_name: string;
};

export type BufferPublishRequest = {
  channel_id: string;
  text: string;
  mode?: BufferShareMode;
  due_at?: string | null;
  image_url?: string | null;
  video_url?: string | null;
  instagram_type?: BufferInstagramType | null;
};

export type BufferPublishResult = {
  ok: boolean;
  post_id: string | null;
  due_at: string | null;
  message: string;
};

export type VideoConfig = {
  model: string;
  max_duration_seconds: number;
  default_aspect_ratio: VideoAspectRatio;
  supported_aspect_ratios: VideoAspectRatio[];
  supported_resolutions: VideoResolution[];
  prompt_presets: Record<string, string>;
};

export type VideoSaveExportRequest = {
  id: string;
  branded_video_url: string;
  branded_file_name?: string | null;
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
  created_at: string;
};

export type WatermarkLogoItem = {
  id?: string;
  logo_path: string;
  anchor: string;
  scale: number;
  opacity: number;
  x?: number;
  y?: number;
};

export type HistoryCampaignSummary = {
  id: string;
  brand_id: string;
  title?: string | null;
  thesis?: string | null;
  objective?: string | null;
  status: string;
  created_at: string;
  updated_at?: string | null;
  platforms: string[];
  has_final_image: boolean;
  has_final_video: boolean;
  has_original_image: boolean;
  review_cycle: number;
  review_status?: string | null;
  publications_count: number;
};

export type AssistantChatRequest = {
  message: string;
  target_platform?: string | null;
  regenerate_media?: boolean;
  media_type?: 'image' | 'video';
};

export type AssistantChatResponse = {
  reply: string;
  campaign_id: string;
  regenerated_platforms: string[];
  compliance_results: Record<string, any>;
  new_media?: CampaignMediaItem | null;
  updated_contents: CampaignPlatformContentItem[];
};

export type ResubmitReviewRequest = {
  note?: string | null;
};

export type ResubmitReviewResponse = {
  success: boolean;
  campaign_id: string;
  status: string;
  review_cycle: number;
  message: string;
};

export type CampaignWorkspaceHistory = {
  campaign: Record<string, any>;
  contents: CampaignPlatformContentItem[];
  media: CampaignMediaItem[];
  review_cycles: Record<string, any>[];
  publications: CampaignPublicationItem[];
  events: CampaignEventItem[];
  lessons: Record<string, any>[];
};

export type BrandLogoItem = {
  id?: string;
  name: string;
  filename: string;
  file?: string;
  url: string;
  src?: string;
};

