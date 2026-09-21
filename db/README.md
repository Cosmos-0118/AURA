# AURA — MySQL Database Setup

This directory contains the database schema and seed data for AURA Marketing Operations Desk.

## Architecture

The system uses local MySQL for structured data and stores media binaries (images and vertical videos) on the local filesystem in `storage/campaigns/{campaign_id}/`.

```
brands
   │
   ├────────────── campaigns
   │                    │
   │                    ├── campaign_platform_content
   │                    │
   │                    ├── campaign_media
   │                    │
   │                    ├── compliance_checks
   │                    │
   │                    ├── review_queue
   │                    │
   │                    └── campaign_events
   │
   └────────────── lessons
```

## Setup Instructions

### 1. Install & Start MySQL
Ensure MySQL 8.0+ is running locally on port 3306.

### 2. Configure Environment Variables
Copy `.env.example` to `.env` in the repository root:

```env
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DATABASE=aura
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
```

> **Note:** Never commit `.env` or hardcode database passwords.

### 3. Initialize Database Schema
Run `db/schema.sql` to create the `aura` database and tables:

```bash
mysql -u root -p < db/schema.sql
```

### 4. Seed Baseline Brand & Lesson Data
Run `db/seed.sql` to populate portfolio brands and negative guidance lessons:

```bash
mysql -u root -p aura < db/seed.sql
```

### 5. Start Backend Services
From the `api/` directory:

```bash
cd api
uv run uvicorn main:app --reload --port 8000
```

### 6. Start Web Frontend
From the `web/` directory:

```bash
cd web
bun run dev
```
