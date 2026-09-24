-- AURA MySQL Database Schema for Campaign Studio and Operations Desk
-- Database: aura

CREATE DATABASE IF NOT EXISTS aura CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE aura;

CREATE TABLE IF NOT EXISTS brands (
  id VARCHAR(64) PRIMARY KEY,
  name VARCHAR(128) NOT NULL,
  tagline VARCHAR(255) NOT NULL,
  tone JSON NOT NULL,
  audience TEXT NOT NULL,
  do_list JSON NOT NULL,
  dont_list JSON NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS campaigns (
  id VARCHAR(64) PRIMARY KEY,
  brand_id VARCHAR(64) NOT NULL,
  title VARCHAR(255),
  topic TEXT,
  country VARCHAR(100),
  goal VARCHAR(255),
  platforms TEXT NOT NULL DEFAULT '["linkedin"]',
  objective VARCHAR(64) NOT NULL,
  language VARCHAR(32) NOT NULL DEFAULT 'en',
  thesis TEXT NOT NULL,
  target_audience TEXT,
  status VARCHAR(32) NOT NULL DEFAULT 'draft',
  error TEXT,
  completed_at TIMESTAMP NULL,
  campaign_facts JSON,
  generation_provider VARCHAR(100),
  generation_model VARCHAR(100),
  lessons_used JSON,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_brand (brand_id),
  INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS campaign_platform_content (
  id VARCHAR(64) PRIMARY KEY,
  campaign_id VARCHAR(64) NOT NULL,
  platform VARCHAR(32) NOT NULL,
  title VARCHAR(255),
  content TEXT NOT NULL,
  hashtags JSON,
  hook TEXT,
  script TEXT,
  visual_concept TEXT,
  captions TEXT,
  generation_prompt TEXT,
  image_generation_prompt TEXT,
  video_generation_prompt TEXT,
  language VARCHAR(32),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_campaign (campaign_id),
  INDEX idx_platform (platform),
  FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS campaign_media (
  id VARCHAR(64) PRIMARY KEY,
  campaign_id VARCHAR(64) NOT NULL,
  media_type VARCHAR(32) NOT NULL,
  prompt TEXT NOT NULL,
  local_path VARCHAR(512),
  provider VARCHAR(64) NOT NULL DEFAULT 'local',
  model VARCHAR(128) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  media_stage VARCHAR(32) NOT NULL DEFAULT 'final',
  watermarked TINYINT(1) NOT NULL DEFAULT 0,
  logo_path VARCHAR(512),
  logo_position VARCHAR(64),
  logo_scale FLOAT DEFAULT 100.0,
  logo_opacity FLOAT DEFAULT 100.0,
  parent_media_id VARCHAR(64),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_campaign_media (campaign_id),
  FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lessons (
  id VARCHAR(64) PRIMARY KEY,
  brand_id VARCHAR(64) NOT NULL,
  platform VARCHAR(32),
  tag VARCHAR(64),
  reason_tag VARCHAR(64),
  note TEXT NOT NULL,
  original_content TEXT,
  corrected_content TEXT,
  original_body TEXT,
  edited_body TEXT,
  asset_id VARCHAR(64),
  source_campaign_id VARCHAR(64),
  source VARCHAR(64) NOT NULL DEFAULT 'human_review',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_brand_lessons (brand_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS review_queue (
  id VARCHAR(64) PRIMARY KEY,
  campaign_id VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending_review',
  reviewer_note TEXT,
  feedback_tag VARCHAR(64),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  reviewed_at TIMESTAMP NULL,
  INDEX idx_review_status (status),
  FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS content_assets (
  id VARCHAR(64) PRIMARY KEY,
  campaign_id VARCHAR(64),
  brand_id VARCHAR(64) NOT NULL,
  platform VARCHAR(32) NOT NULL,
  content_type VARCHAR(64) NOT NULL,
  variant VARCHAR(16) NOT NULL DEFAULT 'A',
  language VARCHAR(32) NOT NULL DEFAULT 'en',
  title TEXT,
  body LONGTEXT NOT NULL,
  hashtags JSON NOT NULL,
  media_url TEXT,
  status VARCHAR(32) NOT NULL DEFAULT 'pending_review',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  approved_at TIMESTAMP NULL,
  approved_by VARCHAR(255),
  INDEX idx_assets_campaign (campaign_id),
  INDEX idx_assets_brand (brand_id),
  FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS compliance_checks (
  id VARCHAR(64) PRIMARY KEY,
  campaign_id VARCHAR(64),
  asset_id VARCHAR(64),
  status VARCHAR(16),
  result VARCHAR(16),
  risk_level VARCHAR(16),
  risk VARCHAR(16),
  rules JSON,
  issues JSON,
  suggested_fixes JSON,
  suggested_revision TEXT,
  rules_checked INT DEFAULT 0,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_compliance_asset (asset_id),
  FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
  FOREIGN KEY (asset_id) REFERENCES content_assets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS reviews (
  id VARCHAR(64) PRIMARY KEY,
  asset_id VARCHAR(64) NOT NULL,
  action VARCHAR(32) NOT NULL,
  reason_tag VARCHAR(100),
  note TEXT,
  original_body LONGTEXT,
  edited_body LONGTEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (asset_id) REFERENCES content_assets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS campaign_events (
  id VARCHAR(64) PRIMARY KEY,
  campaign_id VARCHAR(64) NOT NULL,
  event_type VARCHAR(100) NOT NULL,
  actor VARCHAR(64) NOT NULL DEFAULT 'system',
  description TEXT,
  metadata JSON,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_events_campaign (campaign_id),
  FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS campaign_publications (
  id VARCHAR(64) PRIMARY KEY,
  campaign_id VARCHAR(64) NOT NULL,
  platform VARCHAR(32) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'queued',
  external_post_id VARCHAR(255),
  external_post_url TEXT,
  published_content LONGTEXT,
  media_id VARCHAR(64),
  error_message TEXT,
  published_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_publications_campaign (campaign_id),
  FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS leads (
  id VARCHAR(64) PRIMARY KEY,
  brand_id VARCHAR(64) NOT NULL,
  name VARCHAR(255) NOT NULL,
  category VARCHAR(255),
  location VARCHAR(255),
  url TEXT,
  country VARCHAR(100),
  phone VARCHAR(64),
  public_email VARCHAR(255),
  social_links JSON,
  description TEXT,
  services JSON,
  source VARCHAR(100) NOT NULL DEFAULT 'unknown',
  source_url TEXT,
  status VARCHAR(64) NOT NULL DEFAULT 'new',
  fit_score INT NOT NULL DEFAULT 0,
  why TEXT,
  external_place_id VARCHAR(255),
  email VARCHAR(255),
  requirements TEXT,
  source_title TEXT,
  domain VARCHAR(255),
  operating_status VARCHAR(64),
  overture_confidence DOUBLE,
  source_release VARCHAR(32),
  stage VARCHAR(32) NOT NULL DEFAULT 'discovered',
  score_version VARCHAR(64),
  score_breakdown LONGTEXT,
  review_status VARCHAR(32) NOT NULL DEFAULT 'pending',
  reviewed_by VARCHAR(255),
  reviewed_at DATETIME NULL,
  review_note TEXT,
  outreach_status VARCHAR(32) NOT NULL DEFAULT 'not_approved',
  outreach_approved_by VARCHAR(255),
  outreach_approved_at DATETIME NULL,
  outreach_sent_at DATETIME NULL,
  contact_status VARCHAR(32) NOT NULL DEFAULT 'unknown',
  products JSON,
  specialties JSON,
  fit_reasons JSON,
  last_verified_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_leads_brand (brand_id),
  INDEX idx_leads_external_place (external_place_id),
  INDEX idx_leads_brand_domain (brand_id, domain),
  INDEX idx_leads_page_fit (fit_score DESC, name ASC, id ASC),
  INDEX idx_leads_page_brand_fit (brand_id, fit_score DESC, name ASC, id ASC),
  INDEX idx_leads_page_name (name ASC, id ASC),
  INDEX idx_leads_page_brand_name (brand_id, name ASC, id ASC),
  INDEX idx_leads_domain_search (domain)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lead_locations (
  id VARCHAR(64) PRIMARY KEY,
  lead_id VARCHAR(64) NOT NULL,
  external_place_id VARCHAR(255),
  name VARCHAR(255) NOT NULL,
  category VARCHAR(255),
  location TEXT,
  country VARCHAR(100),
  url TEXT,
  phone VARCHAR(64),
  email VARCHAR(255),
  operating_status VARCHAR(64),
  confidence DOUBLE,
  source_release VARCHAR(32),
  source_provider VARCHAR(100),
  raw_record LONGTEXT,
  status VARCHAR(64) NOT NULL DEFAULT 'active',
  first_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_seen_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_verified_at DATETIME NULL,
  INDEX idx_lead_locations_account (lead_id),
  INDEX idx_lead_locations_external (external_place_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lead_accounts (
  id VARCHAR(64) PRIMARY KEY,
  brand_id VARCHAR(64) NOT NULL,
  company_name VARCHAR(255) NOT NULL,
  domain VARCHAR(255),
  website TEXT,
  country VARCHAR(100),
  category VARCHAR(255),
  stage VARCHAR(32) NOT NULL DEFAULT 'discovered',
  fit_score INT NOT NULL DEFAULT 0,
  score_version VARCHAR(64),
  review_status VARCHAR(32) NOT NULL DEFAULT 'pending',
  reviewed_by VARCHAR(255),
  reviewed_at DATETIME NULL,
  review_note TEXT,
  outreach_status VARCHAR(32) NOT NULL DEFAULT 'not_approved',
  outreach_approved_by VARCHAR(255),
  outreach_approved_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_lead_accounts_domain (brand_id, domain)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lead_contacts (
  id VARCHAR(64) PRIMARY KEY,
  lead_id VARCHAR(64) NOT NULL,
  location_id VARCHAR(64),
  contact_type VARCHAR(32) NOT NULL,
  value VARCHAR(512) NOT NULL,
  source VARCHAR(100) NOT NULL,
  source_url TEXT,
  confidence DOUBLE,
  verification_status VARCHAR(32) NOT NULL DEFAULT 'unverified',
  observed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_lead_contacts_account (lead_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lead_source_records (
  id VARCHAR(64) PRIMARY KEY,
  lead_id VARCHAR(64) NOT NULL,
  location_id VARCHAR(64),
  source VARCHAR(100) NOT NULL,
  source_record_id VARCHAR(255) NOT NULL,
  release VARCHAR(32),
  source_url TEXT,
  raw_data LONGTEXT NOT NULL,
  observed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_lead_source_records_account (lead_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lead_evidence (
  id VARCHAR(64) PRIMARY KEY,
  lead_id VARCHAR(64) NOT NULL,
  location_id VARCHAR(64),
  evidence_type VARCHAR(64) NOT NULL,
  value LONGTEXT NOT NULL,
  source VARCHAR(100) NOT NULL,
  source_url TEXT,
  confidence DOUBLE,
  observed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_lead_evidence_account (lead_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lead_scores (
  id VARCHAR(64) PRIMARY KEY,
  lead_id VARCHAR(64) NOT NULL,
  score INT NOT NULL,
  score_version VARCHAR(64) NOT NULL,
  breakdown LONGTEXT NOT NULL,
  qualification VARCHAR(32) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_lead_scores_account (lead_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lead_jobs (
  id VARCHAR(64) PRIMARY KEY,
  lead_id VARCHAR(64),
  stage VARCHAR(32) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  attempts INT NOT NULL DEFAULT 0,
  next_attempt_at DATETIME NULL,
  locked_at DATETIME NULL,
  last_error TEXT,
  payload LONGTEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_lead_jobs_queue (status, next_attempt_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lead_suppressions (
  id VARCHAR(64) PRIMARY KEY,
  brand_id VARCHAR(64) NOT NULL,
  domain VARCHAR(255),
  email VARCHAR(255),
  reason TEXT,
  created_by VARCHAR(255),
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_lead_suppressions_brand (brand_id),
  INDEX idx_lead_suppressions_domain (brand_id, domain),
  INDEX idx_lead_suppressions_email (brand_id, email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lead_provider_usage (
  provider VARCHAR(64) NOT NULL,
  period VARCHAR(16) NOT NULL,
  used INT NOT NULL DEFAULT 0,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (provider, period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS video_generations (
  id VARCHAR(64) PRIMARY KEY,
  brand_id VARCHAR(64),
  asset_id VARCHAR(64),
  prompt TEXT NOT NULL,
  aspect_ratio VARCHAR(16) NOT NULL DEFAULT '9:16',
  resolution VARCHAR(16) NOT NULL DEFAULT '768P',
  duration_secs INT NOT NULL DEFAULT 5,
  model VARCHAR(128) NOT NULL DEFAULT 'minimax/h3-max-turbo/text-to-video',
  video_url TEXT,
  file_name VARCHAR(255),
  file_size BIGINT,
  branded_video_url TEXT,
  branded_file_name VARCHAR(255),
  status VARCHAR(32) NOT NULL DEFAULT 'COMPLETED',
  error_msg TEXT,
  request_id VARCHAR(255),
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_video_gen_created (created_at),
  INDEX idx_video_gen_brand (brand_id),
  INDEX idx_video_gen_branded (branded_video_url(255))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
