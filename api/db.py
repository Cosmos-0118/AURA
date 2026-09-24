"""AURA Database Connection Layer.
Supports MySQL (Database: aura) and local SQLite fallback for seamless developer experience.
"""

from contextlib import contextmanager
import json
import os
from pathlib import Path
import sqlite3
import threading
from typing import Any, Generator

from dotenv import load_dotenv

load_dotenv()

STORAGE_DIR = Path(__file__).resolve().parent.parent / "storage"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)
SQLITE_DB_PATH = STORAGE_DIR / "aura.db"
_SQLITE_SCHEMA_LOCK = threading.Lock()
_SQLITE_INITIALIZED_PATHS: set[str] = set()


def get_db_mode() -> str:
    """Check if MySQL is requested or fallback to SQLite."""
    return os.environ.get("DB_ENGINE", "auto").lower()


class SQLiteDictCursor:
    def __init__(self, cursor: sqlite3.Cursor):
        self.cursor = cursor

    @property
    def rowcount(self) -> int:
        return self.cursor.rowcount

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
          domain TEXT,
          operating_status TEXT,
          overture_confidence REAL,
          source_release TEXT,
          stage TEXT NOT NULL DEFAULT 'discovered',
          score_version TEXT,
          score_breakdown TEXT,
          review_status TEXT NOT NULL DEFAULT 'pending',
          reviewed_by TEXT,
          reviewed_at DATETIME,
          review_note TEXT,
          outreach_status TEXT NOT NULL DEFAULT 'not_approved',
          outreach_approved_by TEXT,
          outreach_approved_at DATETIME,
          outreach_sent_at DATETIME,
          contact_status TEXT NOT NULL DEFAULT 'unknown',
          products TEXT,
          specialties TEXT,
          fit_reasons TEXT,
          last_verified_at DATETIME,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
          ,updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS lead_locations (
          id TEXT PRIMARY KEY,
          lead_id TEXT NOT NULL,
          external_place_id TEXT,
          name TEXT NOT NULL,
          category TEXT,
          location TEXT,
          country TEXT,
          url TEXT,
          phone TEXT,
          email TEXT,
          operating_status TEXT,
          confidence REAL,
          source_release TEXT,
          source_provider TEXT,
          raw_record TEXT,
          status TEXT NOT NULL DEFAULT 'active',
          first_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          last_seen_at DATETIME DEFAULT CURRENT_TIMESTAMP,
          last_verified_at DATETIME
        );
        CREATE INDEX IF NOT EXISTS idx_lead_locations_account ON lead_locations(lead_id);
        CREATE INDEX IF NOT EXISTS idx_lead_locations_external ON lead_locations(external_place_id);

        CREATE TABLE IF NOT EXISTS lead_accounts (
          id TEXT PRIMARY KEY,
          brand_id TEXT NOT NULL,
          company_name TEXT NOT NULL,
          domain TEXT,
          website TEXT,
          country TEXT,
          category TEXT,
          stage TEXT NOT NULL DEFAULT 'discovered',
          fit_score INTEGER NOT NULL DEFAULT 0,
          score_version TEXT,
          review_status TEXT NOT NULL DEFAULT 'pending',
          reviewed_by TEXT,
          reviewed_at DATETIME,
          review_note TEXT,
          outreach_status TEXT NOT NULL DEFAULT 'not_approved',
          outreach_approved_by TEXT,
          outreach_approved_at DATETIME,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_lead_accounts_domain ON lead_accounts(brand_id, domain);

        CREATE TABLE IF NOT EXISTS lead_contacts (
          id TEXT PRIMARY KEY,
          lead_id TEXT NOT NULL,
          location_id TEXT,
          contact_type TEXT NOT NULL,
          value TEXT NOT NULL,
          source TEXT NOT NULL,
          source_url TEXT,
          confidence REAL,
          verification_status TEXT NOT NULL DEFAULT 'unverified',
          observed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_lead_contacts_account ON lead_contacts(lead_id);

        CREATE TABLE IF NOT EXISTS lead_source_records (
          id TEXT PRIMARY KEY,
          lead_id TEXT NOT NULL,
          location_id TEXT,
          source TEXT NOT NULL,
          source_record_id TEXT NOT NULL,
          release TEXT,
          source_url TEXT,
          raw_data TEXT NOT NULL,
          observed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_lead_source_records_account ON lead_source_records(lead_id);

        CREATE TABLE IF NOT EXISTS lead_evidence (
          id TEXT PRIMARY KEY,
          lead_id TEXT NOT NULL,
          location_id TEXT,
          evidence_type TEXT NOT NULL,
          value TEXT NOT NULL,
          source TEXT NOT NULL,
          source_url TEXT,
          confidence REAL,
          observed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_lead_evidence_account ON lead_evidence(lead_id);

        CREATE TABLE IF NOT EXISTS lead_scores (
          id TEXT PRIMARY KEY,
          lead_id TEXT NOT NULL,
          score INTEGER NOT NULL,
          score_version TEXT NOT NULL,
          breakdown TEXT NOT NULL,
          qualification TEXT NOT NULL,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_lead_scores_account ON lead_scores(lead_id);

        CREATE TABLE IF NOT EXISTS lead_jobs (
          id TEXT PRIMARY KEY,
          lead_id TEXT,
          stage TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'pending',
          attempts INTEGER NOT NULL DEFAULT 0,
          next_attempt_at DATETIME,
          locked_at DATETIME,
          last_error TEXT,
          payload TEXT,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_lead_jobs_queue ON lead_jobs(status, next_attempt_at);

        CREATE TABLE IF NOT EXISTS lead_suppressions (
          id TEXT PRIMARY KEY,
          brand_id TEXT NOT NULL,
          domain TEXT,
          email TEXT,
          reason TEXT,
          created_by TEXT,
          created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_lead_suppressions_brand ON lead_suppressions(brand_id);
        CREATE INDEX IF NOT EXISTS idx_lead_suppressions_domain ON lead_suppressions(brand_id, domain);
        CREATE INDEX IF NOT EXISTS idx_lead_suppressions_email ON lead_suppressions(brand_id, email);

        CREATE TABLE IF NOT EXISTS lead_provider_usage (
          provider TEXT NOT NULL,
          period TEXT NOT NULL,
          used INTEGER NOT NULL DEFAULT 0,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
          PRIMARY KEY (provider, period)
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
        ("leads", "domain TEXT"),
        ("leads", "operating_status TEXT"),
        ("leads", "overture_confidence REAL"),
        ("leads", "source_release TEXT"),
        ("leads", "stage TEXT NOT NULL DEFAULT 'discovered'"),
        ("leads", "score_version TEXT"),
        ("leads", "score_breakdown TEXT"),
        ("leads", "review_status TEXT NOT NULL DEFAULT 'pending'"),
        ("leads", "reviewed_by TEXT"),
        ("leads", "reviewed_at DATETIME"),
        ("leads", "review_note TEXT"),
        ("leads", "outreach_status TEXT NOT NULL DEFAULT 'not_approved'"),
        ("leads", "outreach_approved_by TEXT"),
        ("leads", "outreach_approved_at DATETIME"),
        ("leads", "outreach_sent_at DATETIME"),
        ("leads", "contact_status TEXT NOT NULL DEFAULT 'unknown'"),
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

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_brand_domain ON leads(brand_id, domain)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_page_fit ON leads(fit_score DESC, name ASC, id ASC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_page_brand_fit ON leads(brand_id, fit_score DESC, name ASC, id ASC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_page_name ON leads(name ASC, id ASC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_page_brand_name ON leads(brand_id, name ASC, id ASC)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_name_search ON leads(name COLLATE NOCASE)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_brand_name_search ON leads(brand_id, name COLLATE NOCASE)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_leads_domain_search ON leads(domain)")
    cursor.execute(
        "UPDATE leads SET updated_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP) "
        "WHERE updated_at IS NULL"
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

    # Seed campaigns and full history from aura (1).sql if empty
    cursor.execute("SELECT COUNT(*) FROM campaigns")
    if cursor.fetchone()[0] == 0:
        _auto_import_aura_sql_dump(conn)


def _auto_import_aura_sql_dump(conn: sqlite3.Connection):
    """Import initial campaigns and history data from aura (1).sql dump if available."""
    candidates = [
        Path(r"D:\Computers\Projects\AURA\aura (1).sql"),
        Path(__file__).resolve().parent.parent.parent / "aura (1).sql",
        Path(__file__).resolve().parent.parent / "aura (1).sql",
    ]
    sql_file = next((p for p in candidates if p.exists()), None)
    if not sql_file:
        return

    try:
        import re
        with open(sql_file, "r", encoding="utf-8", errors="ignore") as f:
            sql_text = f.read()

        insert_pattern = re.compile(
            r"INSERT INTO [`\"]?([a-zA-Z0-9_]+)[`\"]?\s*\(([^)]+)\)\s*VALUES\s*(.+?);",
            re.DOTALL | re.IGNORECASE,
        )
        matches = insert_pattern.findall(sql_text)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        sqlite_tables = {row[0] for row in cursor.fetchall()}
        cursor.execute("PRAGMA foreign_keys = OFF")

        for table, cols_str, values_block in matches:
            tbl = table.strip().lower()
            if tbl not in sqlite_tables:
                continue

            cols = [c.strip().strip("`").strip('"') for c in cols_str.split(",")]
            cursor.execute(f"PRAGMA table_info({tbl})")
            table_info = {row[1]: row[2] for row in cursor.fetchall()}
            valid_col_indices = [i for i, c in enumerate(cols) if c in table_info]
            valid_cols = [cols[i] for i in valid_col_indices]
            if not valid_cols:
                continue

            rows_data = []
            current_val = []
            current_row = []
            in_quote = False
            quote_char = None
            escape = False
            depth = 0

            for char in values_block:
                if escape:
                    current_val.append(char)
                    escape = False
                    continue
                if char == "\\":
                    escape = True
                    continue
                if in_quote:
                    if char == quote_char:
                        in_quote = False
                        quote_char = None
                    else:
                        current_val.append(char)
                    continue
                else:
                    if char in ("'", '"'):
                        in_quote = True
                        quote_char = char
                        continue
                    elif char == "(":
                        depth += 1
                        if depth == 1:
                            current_row = []
                            current_val = []
                        continue
                    elif char == ")":
                        depth -= 1
                        if depth == 0:
                            v = "".join(current_val).strip()
                            current_row.append(None if v == "NULL" else v)
                            current_val = []
                            rows_data.append(current_row)
                            current_row = []
                        continue
                    elif char == "," and depth == 1:
                        v = "".join(current_val).strip()
                        current_row.append(None if v == "NULL" else v)
                        current_val = []
                        continue
                    elif depth == 1:
                        current_val.append(char)

            placeholders = ", ".join(["?"] * len(valid_cols))
            col_names = ", ".join(f'"{c}"' for c in valid_cols)
            sql_insert = f"INSERT OR REPLACE INTO {tbl} ({col_names}) VALUES ({placeholders})"

            for row in rows_data:
                filtered_row = [row[i] if i < len(row) else None for i in valid_col_indices]
                if tbl == "brands":
                    if "tone" in valid_cols:
                        t_idx = valid_cols.index("tone")
                        if not filtered_row[t_idx]:
                            filtered_row[t_idx] = json.dumps(["Professional", "Educational"])
                    if "do_list" in valid_cols:
                        d_idx = valid_cols.index("do_list")
                        if not filtered_row[d_idx]:
                            filtered_row[d_idx] = json.dumps([])
                    if "dont_list" in valid_cols:
                        dt_idx = valid_cols.index("dont_list")
                        if not filtered_row[dt_idx]:
                            filtered_row[dt_idx] = json.dumps([])
                elif tbl == "lessons":
                    if "reason_tag" in valid_cols:
                        rt_idx = valid_cols.index("reason_tag")
                        if not filtered_row[rt_idx] and "tag" in valid_cols:
                            filtered_row[rt_idx] = filtered_row[valid_cols.index("tag")] or "OFF_BRAND"
                        elif not filtered_row[rt_idx]:
                            filtered_row[rt_idx] = "OFF_BRAND"

                try:
                    cursor.execute(sql_insert, filtered_row)
                except Exception:
                    pass

        conn.commit()
        cursor.execute("PRAGMA foreign_keys = ON")
    except Exception:
        pass


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
          INDEX idx_leads_brand_domain (brand_id, domain)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
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
        """,
        """
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
        """,
        """
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
        """,
        """
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
        """,
        """
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
        """,
        """
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
        """,
        """
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
        """,
        """
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
        """,
        """
        CREATE TABLE IF NOT EXISTS lead_provider_usage (
          provider VARCHAR(64) NOT NULL,
          period VARCHAR(16) NOT NULL,
          used INT NOT NULL DEFAULT 0,
          updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
          PRIMARY KEY (provider, period)
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
        "ALTER TABLE campaigns MODIFY COLUMN status VARCHAR(50) NOT NULL DEFAULT 'draft'",
        "ALTER TABLE review_queue MODIFY COLUMN status VARCHAR(50) NOT NULL DEFAULT 'pending_review'",
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
        "ALTER TABLE leads ADD COLUMN email VARCHAR(255)",
        "ALTER TABLE leads ADD COLUMN requirements TEXT",
        "ALTER TABLE leads ADD COLUMN source_title TEXT",
        "ALTER TABLE leads ADD COLUMN domain VARCHAR(255)",
        "ALTER TABLE leads ADD COLUMN operating_status VARCHAR(64)",
        "ALTER TABLE leads ADD COLUMN overture_confidence DOUBLE",
        "ALTER TABLE leads ADD COLUMN source_release VARCHAR(32)",
        "ALTER TABLE leads ADD COLUMN stage VARCHAR(32) NOT NULL DEFAULT 'discovered'",
        "ALTER TABLE leads ADD COLUMN score_version VARCHAR(64)",
        "ALTER TABLE leads ADD COLUMN score_breakdown LONGTEXT",
        "ALTER TABLE leads ADD COLUMN review_status VARCHAR(32) NOT NULL DEFAULT 'pending'",
        "ALTER TABLE leads ADD COLUMN reviewed_by VARCHAR(255)",
        "ALTER TABLE leads ADD COLUMN reviewed_at DATETIME NULL",
        "ALTER TABLE leads ADD COLUMN review_note TEXT",
        "ALTER TABLE leads ADD COLUMN outreach_status VARCHAR(32) NOT NULL DEFAULT 'not_approved'",
        "ALTER TABLE leads ADD COLUMN outreach_approved_by VARCHAR(255)",
        "ALTER TABLE leads ADD COLUMN outreach_approved_at DATETIME NULL",
        "ALTER TABLE leads ADD COLUMN outreach_sent_at DATETIME NULL",
        "ALTER TABLE leads ADD COLUMN contact_status VARCHAR(32) NOT NULL DEFAULT 'unknown'",
        "ALTER TABLE leads ADD INDEX idx_leads_brand_domain (brand_id, domain)",
        "ALTER TABLE leads ADD INDEX idx_leads_page_fit (fit_score DESC, name ASC, id ASC)",
        "ALTER TABLE leads ADD INDEX idx_leads_page_brand_fit (brand_id, fit_score DESC, name ASC, id ASC)",
        "ALTER TABLE leads ADD INDEX idx_leads_page_name (name ASC, id ASC)",
        "ALTER TABLE leads ADD INDEX idx_leads_page_brand_name (brand_id, name ASC, id ASC)",
        "ALTER TABLE leads ADD INDEX idx_leads_domain_search (domain)",
        "ALTER TABLE lead_suppressions ADD INDEX idx_lead_suppressions_domain (brand_id, domain)",
        "ALTER TABLE lead_suppressions ADD INDEX idx_lead_suppressions_email (brand_id, email)",
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
    conn = sqlite3.connect(str(SQLITE_DB_PATH), timeout=15)
    schema_key = str(SQLITE_DB_PATH.resolve())
    with _SQLITE_SCHEMA_LOCK:
        if schema_key not in _SQLITE_INITIALIZED_PATHS:
            init_sqlite_db(conn)
            _SQLITE_INITIALIZED_PATHS.add(schema_key)
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
