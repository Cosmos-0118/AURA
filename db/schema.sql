-- AURA MySQL Database Schema
-- Idempotent schema creation. Never drops tables or databases.

CREATE DATABASE IF NOT EXISTS aura
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE aura;

-- 4. BRANDS TABLE
CREATE TABLE IF NOT EXISTS brands (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    tagline VARCHAR(255),
    category VARCHAR(100),
    description TEXT,
    voice TEXT,
    tone JSON,
    audience TEXT,
    do_list JSON,
    dont_list JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);

-- 5. CAMPAIGNS TABLE
CREATE TABLE IF NOT EXISTS campaigns (
    id CHAR(36) PRIMARY KEY,
    brand_id VARCHAR(50) NOT NULL,
    title VARCHAR(255),
    topic TEXT,
    country VARCHAR(100),
    goal VARCHAR(255),
    platforms TEXT NOT NULL DEFAULT '["linkedin"]',
    objective VARCHAR(100) NOT NULL,
    language VARCHAR(100) NOT NULL,
    thesis TEXT NOT NULL,
    target_audience TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'draft',
    error TEXT,
    completed_at TIMESTAMP NULL,
    campaign_facts JSON,
    generation_provider VARCHAR(100),
    generation_model VARCHAR(100),
    lessons_used JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (brand_id)
        REFERENCES brands(id)
        ON DELETE RESTRICT
        ON UPDATE CASCADE,
    INDEX idx_campaign_brand (brand_id),
    INDEX idx_campaign_status (status),
    INDEX idx_campaign_created (created_at)
);

-- 6. CAMPAIGN PLATFORM CONTENT TABLE
CREATE TABLE IF NOT EXISTS campaign_platform_content (
    id CHAR(36) PRIMARY KEY,
    campaign_id CHAR(36) NOT NULL,
    platform ENUM(
        'linkedin',
        'instagram',
        'x',
        'reel',
        'blog'
    ) NOT NULL,
    title VARCHAR(500),
    content LONGTEXT,
    hashtags JSON,
    hook TEXT,
    script LONGTEXT,
    captions LONGTEXT,
    visual_concept TEXT,
    image_generation_prompt LONGTEXT,
    video_generation_prompt LONGTEXT,
    language VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id)
        REFERENCES campaigns(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    UNIQUE KEY unique_campaign_platform (campaign_id, platform),
    INDEX idx_platform_campaign (campaign_id)
);

-- 7. MEDIA TABLE
CREATE TABLE IF NOT EXISTS campaign_media (
    id CHAR(36) PRIMARY KEY,
    campaign_id CHAR(36) NOT NULL,
    platform_content_id CHAR(36),
    media_type ENUM(
        'image',
        'video'
    ) NOT NULL,
    provider VARCHAR(100),
    model VARCHAR(150),
    prompt LONGTEXT,
    local_path TEXT NOT NULL,
    filename VARCHAR(255),
    mime_type VARCHAR(100),
    file_size BIGINT,
    width INT,
    height INT,
    duration_seconds DECIMAL(10,2),
    media_stage VARCHAR(32) NOT NULL DEFAULT 'final',
    watermarked TINYINT(1) NOT NULL DEFAULT 0,
    logo_path VARCHAR(512),
    logo_position VARCHAR(64),
    logo_scale FLOAT DEFAULT 100.0,
    logo_opacity FLOAT DEFAULT 100.0,
    parent_media_id CHAR(36),
    status ENUM(
        'generating',
        'completed',
        'failed'
    ) NOT NULL DEFAULT 'generating',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id)
        REFERENCES campaigns(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (platform_content_id)
        REFERENCES campaign_platform_content(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    INDEX idx_media_campaign (campaign_id)
);

-- 10. LESSONS TABLE
CREATE TABLE IF NOT EXISTS lessons (
    id CHAR(36) PRIMARY KEY,
    brand_id VARCHAR(50),
    platform VARCHAR(50),
    tag VARCHAR(100),
    reason_tag VARCHAR(100),
    note TEXT NOT NULL,
    original_content LONGTEXT,
    corrected_content LONGTEXT,
    original_body LONGTEXT,
    edited_body LONGTEXT,
    asset_id CHAR(36),
    source_campaign_id CHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (brand_id)
        REFERENCES brands(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    FOREIGN KEY (source_campaign_id)
        REFERENCES campaigns(id)
        ON DELETE SET NULL
        ON UPDATE CASCADE,
    INDEX idx_lessons_brand (brand_id),
    INDEX idx_lessons_platform (platform)
);

-- 11. REVIEW QUEUE TABLE
CREATE TABLE IF NOT EXISTS review_queue (
    id CHAR(36) PRIMARY KEY,
    campaign_id CHAR(36) NOT NULL,
    status ENUM(
        'pending_review',
        'approved',
        'rejected',
        'edited'
    ) NOT NULL DEFAULT 'pending_review',
    reviewer_note TEXT,
    feedback_tag VARCHAR(100),
    reviewed_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id)
        REFERENCES campaigns(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    INDEX idx_review_status (status)
);

-- 12. CONTENT ASSETS TABLE
CREATE TABLE IF NOT EXISTS content_assets (
    id CHAR(36) PRIMARY KEY,
    campaign_id CHAR(36),
    brand_id VARCHAR(50) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    content_type VARCHAR(50) NOT NULL,
    variant VARCHAR(20) NOT NULL DEFAULT 'A',
    language VARCHAR(20) NOT NULL DEFAULT 'en',
    title TEXT,
    body LONGTEXT NOT NULL,
    hashtags JSON NOT NULL,
    media_url TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'pending_review',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP NULL,
    approved_by VARCHAR(255),
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
    INDEX idx_assets_campaign (campaign_id),
    INDEX idx_assets_brand (brand_id)
);

-- 13. COMPLIANCE CHECKS TABLE
CREATE TABLE IF NOT EXISTS compliance_checks (
    id CHAR(36) PRIMARY KEY,
    campaign_id CHAR(36),
    asset_id CHAR(36),
    status VARCHAR(16),
    result VARCHAR(16),
    risk_level VARCHAR(16),
    risk VARCHAR(16),
    rules JSON,
    issues JSON,
    suggested_fixes JSON,
    suggested_revision TEXT,
    rules_checked INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
    FOREIGN KEY (asset_id) REFERENCES content_assets(id) ON DELETE CASCADE
);

-- 14. REVIEWS TABLE
CREATE TABLE IF NOT EXISTS reviews (
    id CHAR(36) PRIMARY KEY,
    asset_id CHAR(36) NOT NULL,
    action VARCHAR(32) NOT NULL,
    reason_tag VARCHAR(100),
    note TEXT,
    original_body LONGTEXT,
    edited_body LONGTEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (asset_id) REFERENCES content_assets(id) ON DELETE CASCADE
);

-- 15. CAMPAIGN EVENTS TABLE
CREATE TABLE IF NOT EXISTS campaign_events (
    id CHAR(36) PRIMARY KEY,
    campaign_id CHAR(36) NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    description TEXT,
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id)
        REFERENCES campaigns(id)
        ON DELETE CASCADE
);

-- 16. CAMPAIGN PUBLICATIONS TABLE
CREATE TABLE IF NOT EXISTS campaign_publications (
    id CHAR(36) PRIMARY KEY,
    campaign_id CHAR(36) NOT NULL,
    platform VARCHAR(50) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'queued',
    external_post_id VARCHAR(255),
    external_post_url TEXT,
    published_content LONGTEXT,
    media_id CHAR(36),
    error_message TEXT,
    published_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id) REFERENCES campaigns(id) ON DELETE CASCADE,
    INDEX idx_publications_campaign (campaign_id)
);

-- 14. LEADS TABLE
CREATE TABLE IF NOT EXISTS leads (
    id CHAR(36) PRIMARY KEY,
    brand_id VARCHAR(50) NOT NULL,
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (brand_id) REFERENCES brands(id) ON DELETE CASCADE,
    INDEX idx_leads_brand (brand_id),
    INDEX idx_leads_external_place (external_place_id)
);

CREATE TABLE IF NOT EXISTS lead_locations (
    id CHAR(36) PRIMARY KEY,
    lead_id CHAR(36) NOT NULL,
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
    first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_verified_at DATETIME NULL,
    INDEX idx_lead_locations_account (lead_id),
    INDEX idx_lead_locations_external (external_place_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lead_accounts (
    id CHAR(36) PRIMARY KEY,
    brand_id VARCHAR(50) NOT NULL,
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
    id CHAR(36) PRIMARY KEY,
    lead_id CHAR(36) NOT NULL,
    location_id CHAR(36),
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
    id CHAR(36) PRIMARY KEY,
    lead_id CHAR(36) NOT NULL,
    location_id CHAR(36),
    source VARCHAR(100) NOT NULL,
    source_record_id VARCHAR(255) NOT NULL,
    release VARCHAR(32),
    source_url TEXT,
    raw_data LONGTEXT NOT NULL,
    observed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_lead_source_records_account (lead_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lead_evidence (
    id CHAR(36) PRIMARY KEY,
    lead_id CHAR(36) NOT NULL,
    location_id CHAR(36),
    evidence_type VARCHAR(64) NOT NULL,
    value LONGTEXT NOT NULL,
    source VARCHAR(100) NOT NULL,
    source_url TEXT,
    confidence DOUBLE,
    observed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_lead_evidence_account (lead_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lead_scores (
    id CHAR(36) PRIMARY KEY,
    lead_id CHAR(36) NOT NULL,
    score INT NOT NULL,
    score_version VARCHAR(64) NOT NULL,
    breakdown LONGTEXT NOT NULL,
    qualification VARCHAR(32) NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_lead_scores_account (lead_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lead_jobs (
    id CHAR(36) PRIMARY KEY,
    lead_id CHAR(36),
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
    id CHAR(36) PRIMARY KEY,
    brand_id VARCHAR(50) NOT NULL,
    domain VARCHAR(255),
    email VARCHAR(255),
    reason TEXT,
    created_by VARCHAR(255),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_lead_suppressions_brand (brand_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS lead_provider_usage (
    provider VARCHAR(64) NOT NULL,
    period VARCHAR(16) NOT NULL,
    used INT NOT NULL DEFAULT 0,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (provider, period)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 15. VIDEO GENERATION HISTORY
CREATE TABLE IF NOT EXISTS video_generations (
    id CHAR(36) PRIMARY KEY,
    brand_id VARCHAR(50),
    asset_id CHAR(36),
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_video_gen_created (created_at),
    INDEX idx_video_gen_brand (brand_id),
    INDEX idx_video_gen_branded (branded_video_url(255))
);
