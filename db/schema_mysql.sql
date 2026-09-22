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
  objective VARCHAR(64) NOT NULL,
  language VARCHAR(32) NOT NULL DEFAULT 'en',
  thesis TEXT NOT NULL,
  target_audience TEXT,
  status VARCHAR(32) NOT NULL DEFAULT 'draft',
  error TEXT,
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
  script TEXT,
  visual_concept TEXT,
  generation_prompt TEXT,
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
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_campaign_media (campaign_id),
  FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lessons (
  id VARCHAR(64) PRIMARY KEY,
  brand_id VARCHAR(64) NOT NULL,
  platform VARCHAR(32),
  tag VARCHAR(64) NOT NULL,
  note TEXT NOT NULL,
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
  products JSON,
  specialties JSON,
  fit_reasons JSON,
  last_verified_at TIMESTAMP NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_leads_brand (brand_id),
  INDEX idx_leads_external_place (external_place_id)
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
