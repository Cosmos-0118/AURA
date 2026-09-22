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
    category VARCHAR(100),
    description TEXT,
    voice TEXT,
    audience TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
);

-- 5. CAMPAIGNS TABLE
CREATE TABLE IF NOT EXISTS campaigns (
    id CHAR(36) PRIMARY KEY,
    brand_id VARCHAR(50) NOT NULL,
    title VARCHAR(255),
    objective VARCHAR(100) NOT NULL,
    language VARCHAR(100) NOT NULL,
    thesis TEXT NOT NULL,
    target_audience TEXT,
    status ENUM(
        'draft',
        'generating',
        'generated',
        'pending_review',
        'approved',
        'rejected',
        'edited'
    ) NOT NULL DEFAULT 'draft',
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
    tag VARCHAR(100) NOT NULL,
    note TEXT NOT NULL,
    original_content LONGTEXT,
    corrected_content LONGTEXT,
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

-- 12. COMPLIANCE CHECKS TABLE
CREATE TABLE IF NOT EXISTS compliance_checks (
    id CHAR(36) PRIMARY KEY,
    campaign_id CHAR(36) NOT NULL,
    status ENUM(
        'pass',
        'review',
        'fail'
    ) NOT NULL,
    risk_level ENUM(
        'low',
        'medium',
        'high'
    ),
    issues JSON,
    suggested_fixes JSON,
    rules_checked INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (campaign_id)
        REFERENCES campaigns(id)
        ON DELETE CASCADE
);

-- 13. CAMPAIGN EVENTS TABLE
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
