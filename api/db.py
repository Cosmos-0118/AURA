"""AURA Database Connection Layer.
Supports MySQL (Database: aura) and local SQLite fallback for seamless developer experience.
"""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
from typing import Any, Generator

from dotenv import load_dotenv

load_dotenv()

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
SQLITE_DB_PATH = STORAGE_DIR / "aura.db"


def get_db_mode() -> str:
    """Check if MySQL is requested or fallback to SQLite."""
    return os.environ.get("DB_ENGINE", "auto").lower()


class SQLiteDictCursor:
    def __init__(self, cursor: sqlite3.Cursor):
        self.cursor = cursor

    def execute(self, query: str, params: Any = None):
        # Convert %s placeholder to ? for sqlite
        sqlite_query = query.replace("%s", "?")
        if params is None:
            return self.cursor.execute(sqlite_query)
        # Convert any dict/list params to JSON strings
        clean_params = []
        for p in params:
            if isinstance(p, (dict, list)):
                clean_params.append(json.dumps(p))
            else:
                clean_params.append(p)
        return self.cursor.execute(sqlite_query, clean_params)

    def fetchone(self) -> dict[str, Any] | None:
        row = self.cursor.fetchone()
        if row is None:
            return None
        columns = [d[0] for d in self.cursor.description]
        return dict(zip(columns, row))

    def fetchall(self) -> list[dict[str, Any]]:
        rows = self.cursor.fetchall()
        if not rows:
            return []
        columns = [d[0] for d in self.cursor.description]
        return [dict(zip(columns, row)) for row in rows]


class SQLiteConnectionWrapper:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def cursor(self):
        return SQLiteDictCursor(self.conn.cursor())

    def execute(self, query: str, params: Any = None):
        cursor = self.cursor()
        cursor.execute(query, params)
        return cursor

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


class MySQLConnectionWrapper:
    def __init__(self, conn: Any):
        self.conn = conn

    def cursor(self):
        return self.conn.cursor()

    def execute(self, query: str, params: Any = None):
        cursor = self.conn.cursor()
        cursor.execute(query, params)
        return cursor

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()


def init_sqlite_db(conn: sqlite3.Connection):
    cursor = conn.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS brands (
          id TEXT PRIMARY KEY,
          name TEXT NOT NULL,
          tagline TEXT,
          tone TEXT NOT NULL,
          audience TEXT NOT NULL,
          do_list TEXT NOT NULL DEFAULT '[]',
          dont_list TEXT NOT NULL DEFAULT '[]',
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS campaigns (
          id TEXT PRIMARY KEY,
          brand_id TEXT NOT NULL,
          title TEXT,
          objective TEXT NOT NULL DEFAULT 'Awareness',
          language TEXT NOT NULL DEFAULT 'en',
          thesis TEXT NOT NULL DEFAULT '',
          topic TEXT NOT NULL DEFAULT '',
          country TEXT NOT NULL DEFAULT 'SG',
          goal TEXT NOT NULL DEFAULT 'Awareness',
          platforms TEXT NOT NULL DEFAULT '["linkedin"]',
          target_audience TEXT,
          status TEXT NOT NULL DEFAULT 'draft',
          generation_provider TEXT,
          generation_model TEXT,
          lessons_used TEXT,
          campaign_facts TEXT,
          error TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          completed_at DATETIME
        );

        CREATE TABLE IF NOT EXISTS campaign_platform_content (
          id TEXT PRIMARY KEY,
          campaign_id TEXT NOT NULL,
          platform TEXT NOT NULL,
          title TEXT,
          content TEXT NOT NULL,
          hashtags TEXT,
          hook TEXT,
          script TEXT,
          captions TEXT,
          visual_concept TEXT,
          generation_prompt TEXT,
          image_generation_prompt TEXT,
          video_generation_prompt TEXT,
          language TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS campaign_media (
          id TEXT PRIMARY KEY,
          campaign_id TEXT NOT NULL,
          media_type TEXT NOT NULL,
          prompt TEXT NOT NULL,
          local_path TEXT,
          provider TEXT NOT NULL DEFAULT 'local',
          model TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending',
          media_stage TEXT NOT NULL DEFAULT 'final',
          watermarked INTEGER NOT NULL DEFAULT 0,
          logo_path TEXT,
          logo_position TEXT,
          logo_scale REAL DEFAULT 100.0,
          logo_opacity REAL DEFAULT 100.0,
          parent_media_id TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS lessons (
          id TEXT PRIMARY KEY,
          brand_id TEXT NOT NULL,
          platform TEXT,
          tag TEXT,
          reason_tag TEXT NOT NULL,
          note TEXT NOT NULL,
          original_content TEXT,
          corrected_content TEXT,
          original_body TEXT,
          edited_body TEXT,
          asset_id TEXT,
          source_campaign_id TEXT,
          source TEXT NOT NULL DEFAULT 'human_review',
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS lessons_learned (
          id TEXT PRIMARY KEY,
          campaign_id TEXT,
          brand_id TEXT,
          platform TEXT,
          tag TEXT,
          reason_tag TEXT,
          note TEXT,
          original_content TEXT,
          corrected_content TEXT,
          source_campaign_id TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS review_queue (
          id TEXT PRIMARY KEY,
          campaign_id TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending_review',
          reviewer_note TEXT,
          feedback_tag TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          reviewed_at DATETIME
        );

        CREATE TABLE IF NOT EXISTS content_assets (
          id TEXT PRIMARY KEY,
          campaign_id TEXT,
          brand_id TEXT NOT NULL,
          platform TEXT NOT NULL,
          content_type TEXT NOT NULL,
          variant TEXT NOT NULL DEFAULT 'A',
          language TEXT NOT NULL DEFAULT 'en',
          title TEXT,
          body TEXT NOT NULL,
          hashtags TEXT NOT NULL DEFAULT '[]',
          media_url TEXT,
          status TEXT NOT NULL DEFAULT 'pending_review',
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          approved_at DATETIME,
          approved_by TEXT
        );

        CREATE TABLE IF NOT EXISTS compliance_checks (
          id TEXT PRIMARY KEY,
          asset_id TEXT NOT NULL,
          result TEXT NOT NULL,
          risk TEXT NOT NULL,
          rules TEXT NOT NULL DEFAULT '[]',
          issues TEXT NOT NULL DEFAULT '[]',
          suggested_revision TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS reviews (
          id TEXT PRIMARY KEY,
          asset_id TEXT NOT NULL,
          action TEXT NOT NULL,
          reason_tag TEXT,
          note TEXT,
          original_body TEXT,
          edited_body TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS leads (
          id TEXT PRIMARY KEY,
          brand_id TEXT NOT NULL,
          name TEXT NOT NULL,
          category TEXT,
          location TEXT,
          url TEXT,
          country TEXT,
          phone TEXT,
          public_email TEXT,
          social_links TEXT,
          description TEXT,
          services TEXT,
          source TEXT NOT NULL DEFAULT 'unknown',
          source_url TEXT,
          status TEXT NOT NULL DEFAULT 'new',
          fit_score INTEGER NOT NULL DEFAULT 0,
          why TEXT,
          email TEXT,
          requirements TEXT,
          source_title TEXT,
          external_place_id TEXT,
          products TEXT,
          specialties TEXT,
          fit_reasons TEXT,
          last_verified_at DATETIME,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
          ,updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS video_generations (
          id TEXT PRIMARY KEY,
          brand_id TEXT,
          asset_id TEXT,
          prompt TEXT NOT NULL,
          aspect_ratio TEXT NOT NULL DEFAULT '9:16',
          resolution TEXT NOT NULL DEFAULT '768P',
          duration_secs INTEGER NOT NULL DEFAULT 5,
          model TEXT NOT NULL DEFAULT 'minimax/h3-max-turbo/text-to-video',
          video_url TEXT,
          file_name TEXT,
          file_size INTEGER,
          branded_video_url TEXT,
          branded_file_name TEXT,
          status TEXT NOT NULL DEFAULT 'COMPLETED',
          error_msg TEXT,
          request_id TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS competitors (
          id TEXT PRIMARY KEY,
          brand_id TEXT NOT NULL,
          name TEXT NOT NULL,
          url TEXT NOT NULL,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS campaign_events (
          id TEXT PRIMARY KEY,
          campaign_id TEXT NOT NULL,
          event_type TEXT NOT NULL,
          actor TEXT NOT NULL DEFAULT 'system',
          description TEXT,
          metadata TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS campaign_publications (
          id TEXT PRIMARY KEY,
          campaign_id TEXT NOT NULL,
          platform TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'queued',
          external_post_id TEXT,
          external_post_url TEXT,
          published_content TEXT,
          media_id TEXT,
          error_message TEXT,
          published_at DATETIME,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()

    for table, col_def in [
        ("campaigns", "title TEXT"),
        ("campaigns", "generation_provider TEXT"),
        ("campaigns", "generation_model TEXT"),
        ("campaigns", "lessons_used TEXT"),
        ("campaigns", "campaign_facts TEXT"),
        ("campaign_platform_content", "hook TEXT"),
        ("campaign_platform_content", "captions TEXT"),
        ("campaign_platform_content", "image_generation_prompt TEXT"),
        ("campaign_platform_content", "video_generation_prompt TEXT"),
        ("campaign_platform_content", "language TEXT"),
        ("lessons", "tag TEXT"),
        ("lessons", "original_content TEXT"),
        ("lessons", "corrected_content TEXT"),
        ("lessons", "source_campaign_id TEXT"),
        ("campaign_events", "description TEXT"),
        ("leads", "category TEXT"),
        ("leads", "location TEXT"),
        ("leads", "phone TEXT"),
        ("leads", "public_email TEXT"),
        ("leads", "social_links TEXT"),
        ("leads", "description TEXT"),
        ("leads", "services TEXT"),
        ("leads", "source TEXT NOT NULL DEFAULT 'unknown'"),
        ("leads", "source_url TEXT"),
        ("leads", "status TEXT NOT NULL DEFAULT 'new'"),
        ("leads", "external_place_id TEXT"),
        ("leads", "email TEXT"),
        ("leads", "requirements TEXT"),
        ("leads", "source_title TEXT"),
        ("leads", "products TEXT"),
        ("leads", "specialties TEXT"),
        ("leads", "fit_reasons TEXT"),
        ("leads", "last_verified_at DATETIME"),
        ("leads", "updated_at DATETIME"),
    ]:
        existing_columns = {
            row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()
        }
        column_name = col_def.split()[0]
        if column_name in existing_columns:
            continue
        try:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col_def}")
            conn.commit()
        except Exception as exc:
            raise RuntimeError(f"Could not migrate SQLite table {table}.{column_name}") from exc

    cursor.execute(
        "UPDATE leads SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)"
    )
    conn.commit()

    for col_def in [
        ("media_stage", "TEXT DEFAULT 'final'"),
        ("watermarked", "INTEGER DEFAULT 0"),
        ("logo_path", "TEXT"),
        ("logo_position", "TEXT"),
        ("logo_scale", "REAL DEFAULT 100.0"),
        ("logo_opacity", "REAL DEFAULT 100.0"),
        ("parent_media_id", "TEXT"),
        ("watermark_config", "TEXT"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE campaign_media ADD COLUMN {col_def[0]} {col_def[1]}")
            conn.commit()
        except Exception:
            pass

    for tbl, col_def in [
        ("campaign_platform_content", "version INTEGER DEFAULT 1"),
        ("campaign_platform_content", "is_current INTEGER DEFAULT 1"),
        ("review_queue", "review_cycle INTEGER DEFAULT 1"),
        ("review_queue", "is_current INTEGER DEFAULT 1"),
        ("campaign_publications", "provider TEXT DEFAULT 'buffer'"),
        ("campaign_publications", "buffer_post_id TEXT"),
    ]:
        try:
            cursor.execute(f"ALTER TABLE {tbl} ADD COLUMN {col_def}")
            conn.commit()
        except Exception:
            pass

    # Seed initial brands if empty
    cursor.execute("SELECT COUNT(*) FROM brands")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            """
            INSERT INTO brands (id, name, tagline, tone, audience, do_list, dont_list)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    "jade",
                    "Jade",
                    "Specialist Jewellery & Fine Art Risk Protection",
                    json.dumps(["Authoritative", "Premium", "Institutional"]),
                    "Jewellers, fine-art businesses, luxury asset businesses, and high-value asset owners.",
                    json.dumps(["Audit physical vault architecture", "Highlight multi-custody redundancies"]),
                    json.dumps(["Never guarantee zero loss", "Avoid overly promotional hype"]),
                ),
                (
                    "doctorshield",
                    "DoctorShield",
                    "Medical Indemnity & Professional Protection",
                    json.dumps(["Reassuring", "Educational", "Colleague-to-colleague"]),
                    "Doctors, clinics, medical practitioners, and healthcare businesses.",
                    json.dumps(["Focus on clinical governance", "Preserve documentation integrity"]),
                    json.dumps(["No fear-based marketing", "No claims of lawsuit immunity"]),
                ),
                (
                    "jaguar",
                    "Jaguar Transit",
                    "High-Value Valuables & Cargo in Transit Protection",
                    json.dumps(["Operational", "Precise", "Direct"]),
                    "Couriers, logistics companies, high-value goods businesses, and SMEs.",
                    json.dumps(["Focus on telemetry tracking", "Highlight border handovers"]),
                    json.dumps(["No absolute guarantees against theft", "Distinguish shipper vs carrier liability"]),
                ),
            ],
        )
        conn.commit()

    # Seed initial lessons if empty
    cursor.execute("SELECT COUNT(*) FROM lessons")
    if cursor.fetchone()[0] == 0:
        cursor.executemany(
            """
            INSERT INTO lessons (id, brand_id, platform, reason_tag, note, source)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                ("less_01", "jade", "linkedin", "TOO_SALESY", "Use educational framing instead of direct promotion.", "human_review"),
                ("less_02", "jade", "linkedin", "UNSUPPORTED_CLAIM", "Avoid absolute protection or guaranteed outcome claims.", "human_review"),
                ("less_03", "doctorshield", "instagram", "UNSUPPORTED_CLAIM", "Do not promise absolute council hearing immunity.", "human_review"),
                ("less_04", "jaguar", "linkedin", "WRONG_CTA", "Logistics directors need underwriting consults, not instant buy buttons.", "human_review"),
            ],
        )
        conn.commit()


_mysql_initialized = False


def init_mysql_db(raw_conn: Any, force: bool = False):
    """Ensure all required MySQL tables and schema modifications exist."""
    global _mysql_initialized
    if _mysql_initialized and not force:
        return

    tables_ddl = [
        """
        CREATE TABLE IF NOT EXISTS brands (
          id VARCHAR(64) PRIMARY KEY,
          name VARCHAR(128) NOT NULL,
          tagline VARCHAR(255),
          tone JSON,
          audience TEXT NOT NULL,
          do_list JSON,
          dont_list JSON,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS campaigns (
          id VARCHAR(64) PRIMARY KEY,
          brand_id VARCHAR(64) NOT NULL,
          title VARCHAR(255),
          topic TEXT,
          country VARCHAR(100),
          goal VARCHAR(255),
          platforms LONGTEXT NULL,
          objective VARCHAR(64) NOT NULL DEFAULT 'Awareness',
          language VARCHAR(32) NOT NULL DEFAULT 'en',
          thesis TEXT NOT NULL,
          target_audience TEXT,
          status VARCHAR(32) NOT NULL DEFAULT 'draft',
          error TEXT,
          completed_at DATETIME NULL,
          campaign_facts JSON,
          generation_provider VARCHAR(100),
          generation_model VARCHAR(100),
          lessons_used JSON,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          INDEX idx_brand (brand_id),
          INDEX idx_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
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
          image_generation_prompt LONGTEXT,
          video_generation_prompt LONGTEXT,
          language VARCHAR(32),
          version INT DEFAULT 1,
          is_current TINYINT(1) DEFAULT 1,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          INDEX idx_campaign (campaign_id),
          INDEX idx_platform (platform)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
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
          watermark_config LONGTEXT,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          INDEX idx_campaign_media (campaign_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS lessons (
          id VARCHAR(64) PRIMARY KEY,
          brand_id VARCHAR(64) NOT NULL,
          platform VARCHAR(32),
          tag VARCHAR(64),
          reason_tag VARCHAR(64),
          note TEXT NOT NULL,
          original_content TEXT,
          corrected_content TEXT,
          original_body LONGTEXT,
          edited_body LONGTEXT,
          asset_id VARCHAR(64),
          source_campaign_id VARCHAR(64),
          source VARCHAR(64) NOT NULL DEFAULT 'human_review',
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          INDEX idx_brand_lessons (brand_id),
          INDEX idx_lessons_source_camp (source_campaign_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS lessons_learned (
          id VARCHAR(64) PRIMARY KEY,
          campaign_id VARCHAR(64),
          brand_id VARCHAR(64),
          platform VARCHAR(32),
          tag VARCHAR(64),
          reason_tag VARCHAR(64),
          note TEXT,
          original_content TEXT,
          corrected_content TEXT,
          source_campaign_id VARCHAR(64),
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          INDEX idx_lessons_learned_camp (campaign_id),
          INDEX idx_lessons_learned_src (source_campaign_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS review_queue (
          id VARCHAR(64) PRIMARY KEY,
          campaign_id VARCHAR(64) NOT NULL,
          status VARCHAR(32) NOT NULL DEFAULT 'pending_review',
          reviewer_note TEXT,
          feedback_tag VARCHAR(64),
          review_cycle INT DEFAULT 1,
          is_current TINYINT(1) DEFAULT 1,
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          reviewed_at DATETIME NULL,
          INDEX idx_review_status (status),
          INDEX idx_review_camp (campaign_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS content_assets (
          id CHAR(36) PRIMARY KEY,
          campaign_id CHAR(36),
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
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          approved_at DATETIME NULL,
          approved_by VARCHAR(255),
          INDEX idx_assets_campaign (campaign_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
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
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          INDEX idx_compliance_asset (asset_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS reviews (
          id CHAR(36) PRIMARY KEY,
          asset_id CHAR(36) NOT NULL,
          action VARCHAR(32) NOT NULL,
          reason_tag VARCHAR(100),
          note TEXT,
          original_body LONGTEXT,
          edited_body LONGTEXT,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          INDEX idx_reviews_asset (asset_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS campaign_events (
          id CHAR(36) PRIMARY KEY,
          campaign_id CHAR(36) NOT NULL,
          event_type VARCHAR(100) NOT NULL,
          actor VARCHAR(64) NOT NULL DEFAULT 'system',
          description TEXT,
          metadata JSON,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          INDEX idx_events_campaign (campaign_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS campaign_publications (
          id CHAR(36) PRIMARY KEY,
          campaign_id CHAR(36) NOT NULL,
          platform VARCHAR(50) NOT NULL,
          status VARCHAR(50) NOT NULL DEFAULT 'queued',
          external_post_id VARCHAR(255),
          external_post_url TEXT,
          published_content LONGTEXT,
          media_id CHAR(36),
          error_message TEXT,
          provider VARCHAR(50) DEFAULT 'buffer',
          buffer_post_id VARCHAR(255),
          published_at DATETIME NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          INDEX idx_publication_campaign (campaign_id),
          INDEX idx_publication_platform (platform),
          INDEX idx_publication_status (status)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """,
        """
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
        """,
        """
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
          INDEX idx_video_gen_brand (brand_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS competitors (
          id VARCHAR(64) PRIMARY KEY,
          brand_id VARCHAR(64) NOT NULL,
          name VARCHAR(255) NOT NULL,
          url TEXT,
          website TEXT,
          country VARCHAR(100),
          created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
          INDEX idx_competitors_brand (brand_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
    ]

    alter_columns = [
        "ALTER TABLE brands ADD COLUMN tagline VARCHAR(255)",
        "ALTER TABLE brands ADD COLUMN tone JSON",
        "ALTER TABLE brands ADD COLUMN do_list JSON",
        "ALTER TABLE brands ADD COLUMN dont_list JSON",
        "ALTER TABLE campaigns ADD COLUMN topic TEXT",
        "ALTER TABLE campaigns ADD COLUMN country VARCHAR(100)",
        "ALTER TABLE campaigns ADD COLUMN goal VARCHAR(255)",
        "ALTER TABLE campaigns ADD COLUMN platforms LONGTEXT NULL",
        "ALTER TABLE campaigns MODIFY COLUMN platforms LONGTEXT NULL",
        "ALTER TABLE campaigns ADD COLUMN error TEXT",
        "ALTER TABLE campaigns ADD COLUMN completed_at DATETIME NULL",
        "ALTER TABLE campaigns ADD COLUMN campaign_facts JSON",
        "ALTER TABLE campaign_platform_content ADD COLUMN hook TEXT",
        "ALTER TABLE campaign_platform_content ADD COLUMN captions TEXT",
        "ALTER TABLE campaign_platform_content ADD COLUMN image_generation_prompt LONGTEXT",
        "ALTER TABLE campaign_platform_content ADD COLUMN video_generation_prompt LONGTEXT",
        "ALTER TABLE campaign_platform_content ADD COLUMN language VARCHAR(32)",
        "ALTER TABLE campaign_platform_content ADD COLUMN version INT DEFAULT 1",
        "ALTER TABLE campaign_platform_content ADD COLUMN is_current TINYINT(1) DEFAULT 1",
        "ALTER TABLE campaign_media ADD COLUMN media_stage VARCHAR(32) DEFAULT 'final'",
        "ALTER TABLE campaign_media ADD COLUMN watermarked TINYINT(1) DEFAULT 0",
        "ALTER TABLE campaign_media ADD COLUMN logo_path VARCHAR(512)",
        "ALTER TABLE campaign_media ADD COLUMN logo_position VARCHAR(64)",
        "ALTER TABLE campaign_media ADD COLUMN logo_scale FLOAT DEFAULT 100.0",
        "ALTER TABLE campaign_media ADD COLUMN logo_opacity FLOAT DEFAULT 100.0",
        "ALTER TABLE campaign_media ADD COLUMN parent_media_id VARCHAR(64)",
        "ALTER TABLE campaign_media ADD COLUMN watermark_config LONGTEXT",
        "ALTER TABLE review_queue ADD COLUMN review_cycle INT DEFAULT 1",
        "ALTER TABLE review_queue ADD COLUMN is_current TINYINT(1) DEFAULT 1",
        "ALTER TABLE lessons ADD COLUMN reason_tag VARCHAR(64)",
        "ALTER TABLE lessons ADD COLUMN original_body LONGTEXT",
        "ALTER TABLE lessons ADD COLUMN edited_body LONGTEXT",
        "ALTER TABLE lessons ADD COLUMN asset_id VARCHAR(64)",
        "ALTER TABLE compliance_checks ADD COLUMN asset_id VARCHAR(64)",
        "ALTER TABLE compliance_checks ADD COLUMN result VARCHAR(16)",
        "ALTER TABLE compliance_checks ADD COLUMN risk VARCHAR(16)",
        "ALTER TABLE compliance_checks ADD COLUMN rules JSON",
        "ALTER TABLE compliance_checks ADD COLUMN suggested_revision TEXT",
        "ALTER TABLE compliance_checks MODIFY COLUMN campaign_id CHAR(36) NULL",
        "ALTER TABLE compliance_checks MODIFY COLUMN status VARCHAR(16) NULL",
        "ALTER TABLE campaign_publications ADD COLUMN provider VARCHAR(50) DEFAULT 'buffer'",
        "ALTER TABLE campaign_publications ADD COLUMN buffer_post_id VARCHAR(255)",
        "ALTER TABLE competitors ADD COLUMN website TEXT",
        "ALTER TABLE competitors ADD COLUMN country VARCHAR(100)",
    ]

    try:
        with raw_conn.cursor() as cur:
            for ddl in tables_ddl:
                try:
                    cur.execute(ddl)
                except Exception:
                    pass

            for col_sql in alter_columns:
                try:
                    cur.execute(col_sql)
                except Exception:
                    pass

            # Seed initial brands if empty
            cur.execute("SELECT COUNT(*) AS c FROM brands")
            brand_count = cur.fetchone()
            cnt = brand_count["c"] if isinstance(brand_count, dict) else (brand_count[0] if brand_count else 0)
            if cnt == 0:
                cur.executemany(
                    """
                    INSERT INTO brands (id, name, tagline, tone, audience, do_list, dont_list)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    [
                        (
                            "jade",
                            "Jade",
                            "Specialist Jewellery & Fine Art Risk Protection",
                            json.dumps(["Authoritative", "Premium", "Institutional"]),
                            "Jewellers, fine-art businesses, luxury asset businesses, and high-value asset owners.",
                            json.dumps(["Audit physical vault architecture", "Highlight multi-custody redundancies"]),
                            json.dumps(["Never guarantee zero loss", "Avoid overly promotional hype"]),
                        ),
                        (
                            "doctorshield",
                            "DoctorShield",
                            "Medical Indemnity & Professional Protection",
                            json.dumps(["Reassuring", "Educational", "Colleague-to-colleague"]),
                            "Doctors, clinics, medical practitioners, and healthcare businesses.",
                            json.dumps(["Focus on clinical governance", "Preserve documentation integrity"]),
                            json.dumps(["No fear-based marketing", "No claims of lawsuit immunity"]),
                        ),
                        (
                            "jaguar",
                            "Jaguar Transit",
                            "High-Value Valuables & Cargo in Transit Protection",
                            json.dumps(["Operational", "Precise", "Direct"]),
                            "Couriers, logistics companies, high-value goods businesses, and SMEs.",
                            json.dumps(["Focus on telemetry tracking", "Highlight border handovers"]),
                            json.dumps(["No absolute guarantees against theft", "Distinguish shipper vs carrier liability"]),
                        ),
                    ],
                )

            # Seed initial lessons if empty
            cur.execute("SELECT COUNT(*) AS c FROM lessons")
            lesson_count = cur.fetchone()
            l_cnt = lesson_count["c"] if isinstance(lesson_count, dict) else (lesson_count[0] if lesson_count else 0)
            if l_cnt == 0:
                cur.executemany(
                    """
                    INSERT INTO lessons (id, brand_id, platform, reason_tag, note, source)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    [
                        ("less_01", "jade", "linkedin", "TOO_SALESY", "Use educational framing instead of direct promotion.", "human_review"),
                        ("less_02", "jade", "linkedin", "UNSUPPORTED_CLAIM", "Avoid absolute protection or guaranteed outcome claims.", "human_review"),
                        ("less_03", "doctorshield", "instagram", "UNSUPPORTED_CLAIM", "Do not promise absolute council hearing immunity.", "human_review"),
                        ("less_04", "jaguar", "linkedin", "WRONG_CTA", "Logistics directors need underwriting consults, not instant buy buttons.", "human_review"),
                    ],
                )

        raw_conn.commit()
        _mysql_initialized = True
    except Exception:
        pass


@contextmanager
def get_db() -> Generator[Any, None, None]:
    """Provide a database connection context manager (MySQL with SQLite fallback)."""
    mysql_host = os.environ.get("MYSQL_HOST")
    mysql_user = os.environ.get("MYSQL_USER", "root")
    mysql_password = os.environ.get("MYSQL_PASSWORD", "")
    mysql_db = os.environ.get("MYSQL_DATABASE", "aura")
    mysql_port = int(os.environ.get("MYSQL_PORT", 3306))

    # Try MySQL first if host is configured
    if mysql_host and get_db_mode() != "sqlite":
        raw_conn = None
        try:
            import pymysql
            import pymysql.cursors

            raw_conn = pymysql.connect(
                host=mysql_host,
                user=mysql_user,
                password=mysql_password,
                database=mysql_db,
                port=mysql_port,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False,
            )
        except Exception as exc:
            if get_db_mode() == "mysql":
                raise RuntimeError("DB_ENGINE=mysql but the MySQL database could not be opened") from exc
            raw_conn = None

        if raw_conn is not None:
            init_mysql_db(raw_conn)
            wrapper = MySQLConnectionWrapper(raw_conn)
            try:
                yield wrapper
                wrapper.commit()
            except Exception:
                wrapper.rollback()
                raise
            finally:
                wrapper.close()
            return

    # SQLite fallback
    conn = sqlite3.connect(str(SQLITE_DB_PATH))
    init_sqlite_db(conn)
    wrapper = SQLiteConnectionWrapper(conn)
    try:
        yield wrapper
        wrapper.commit()
    except Exception:
        wrapper.rollback()
        raise
    finally:
        wrapper.close()


def reset_campaign_data(db: Any) -> dict[str, int]:
    """Wipe all test campaign data, media, review items, publications, and events for a fresh start."""
    counts = {}
    tables = [
        "campaign_publications",
        "review_queue",
        "campaign_platform_content",
        "campaign_media",
        "campaign_events",
        "campaigns",
    ]
    for tbl in tables:
        try:
            res = db.execute(f"DELETE FROM {tbl}")
            counts[tbl] = getattr(res, "rowcount", 0)
        except Exception:
            pass
    return counts


get_connection = get_db
transaction = get_db


if __name__ == "__main__":
    print(f"Testing database connection (DB_ENGINE={get_db_mode()})...")
    with get_db() as db:
        try:
            res = db.execute("SHOW TABLES").fetchall()
            table_list = [list(r.values())[0] for r in res]
            print(f"MySQL connection OK. Found {len(table_list)} tables:")
            for t in sorted(table_list):
                print(f"  - {t}")
        except Exception:
            res = db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            table_list = [list(r.values())[0] for r in res]
            print(f"SQLite connection OK. Found {len(table_list)} tables:")
            for t in sorted(table_list):
                print(f"  - {t}")
    print("Database verification complete.")

