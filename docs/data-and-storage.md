# Data, storage, and database setup

## Runtime database selection

The connection layer is api/db.py:

1. DB_ENGINE=sqlite always uses storage/aura.db.
2. DB_ENGINE=mysql requires MySQL and raises if it cannot connect.
3. DB_ENGINE=auto tries MySQL only when MYSQL_HOST is set and reachable, then
   falls back to storage/aura.db.

Each API connection initializes the selected schema and applies the small
compatibility migrations in api/db.py. The SQLite path is created on demand.
The database is local state, not a disposable cache: back it up before cleanup.

## SQLite layout

~~~text
storage/
  aura.db
  campaigns/
    {campaign_id}/
      image/
      video/
~~~

The API creates storage/aura.db and seeds baseline brands and lessons when the
tables are empty. Generated media is written under the campaign directory and
served through the API's /media and /storage static mounts.

Competitor intelligence also stores its snapshots and events in SQLite. The
default path is storage/aura.db, or AURA_INTELLIGENCE_DB when set. A legacy
database can be imported once from AURA_INTELLIGENCE_LEGACY_DB.

## MySQL setup

MySQL is optional for local development. To use it:

1. Start MySQL 8+ and create the aura database.
2. Set DB_ENGINE=mysql and MYSQL_HOST, MYSQL_PORT, MYSQL_DATABASE,
   MYSQL_USER, and MYSQL_PASSWORD in the root .env.
3. Apply the canonical schema:

~~~bash
mysql -u root -p < db/schema.sql
mysql -u root -p aura < db/seed.sql
~~~

The API also creates missing tables and applies compatibility columns when it
connects, but applying db/schema.sql makes the intended starting schema
explicit. db/schema_mysql.sql and db/CampaignStudio.sql are additional
historical/export artifacts; they are not the runtime migration mechanism.

The MySQL implementation stores structured records in MySQL and keeps binary
media on the local filesystem. Database backups alone do not preserve images or
videos.

## Core entities

| Entity | Purpose |
| --- | --- |
| brands | Brand voice, audience, and do/don't guidance |
| campaigns | Brief, generated package, status, provider/model, learned lessons |
| campaign_platform_content | Per-platform copy and generation prompts |
| content_assets | Standard-pipeline assets and their lifecycle |
| compliance_checks | Deterministic result, risk, rules, issues, revision |
| campaign_media | Original/final media, watermark state, local path |
| review_queue / reviews | Human review cycles and decisions |
| lessons / lessons_learned | Reviewer corrections fed into future generation |
| campaign_events | Audit trail for generation, review, and publication |
| campaign_publications | Buffer publication attempts and external IDs |
| leads | Account-facing lead state, review, score, and outreach fields |
| lead_accounts / lead_locations | Company-to-branch model, resolved by website domain, then public phone or normalized name and country |
| lead_contacts / lead_evidence / lead_source_records | Contact points and source-backed observations |
| lead_scores / lead_jobs / lead_suppressions / lead_provider_usage | Score history, restart-safe enrichment, suppression, and optional Hunter quota state |
| video_generations | Video provider/output history |
| competitors, snapshots, events | Competitor intelligence registry and evidence |

The SQL schema and the SQLite/MySQL initialization code have evolved together.
When adding a field, update both database paths and the relevant repository
mapping; do not assume a MySQL-only migration is sufficient.

Lead Intelligence records are persisted in the selected application database.
The crawler job queue and Hunter credit reservations share that database; no
Redis, broker, vector database, or separate lead service is required.

## Reset and seed behavior

The dangerous campaign reset route is guarded by AURA_ALLOW_RESET_DATA=true.
It deletes campaign/media/review/publication/event state; it is not a normal
development reset and should not be enabled in a shared environment.

For a deterministic SQL-backed demo, db/demo.sql contains example campaign,
review, lesson, media, and event data. It is an export-style fixture and
assumes the MySQL schema. A fresh SQLite database receives baseline brands and
lessons automatically, but not the complete demo campaign fixture.

## Backup and restore

For SQLite, stop AURA first and copy both the database and media tree:

~~~bash
./scripts/macos/aura.sh stop
mkdir -p backups
cp storage/aura.db backups/aura-$(date +%Y%m%d-%H%M%S).db
cp -R storage/campaigns backups/campaigns-$(date +%Y%m%d-%H%M%S)
~~~

For MySQL, use mysqldump plus an independent backup of storage/campaigns.
Docker collector volumes are separate state; back them up or recreate them
from the registries and Compose configuration when appropriate.
