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
          objective TEXT NOT NULL DEFAULT 'Awareness',
          language TEXT NOT NULL DEFAULT 'en',
          thesis TEXT NOT NULL DEFAULT '',
          topic TEXT NOT NULL DEFAULT '',
          country TEXT NOT NULL DEFAULT 'SG',
          goal TEXT NOT NULL DEFAULT 'Awareness',
          platforms TEXT NOT NULL DEFAULT '["linkedin"]',
          target_audience TEXT,
          status TEXT NOT NULL DEFAULT 'draft',
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
          script TEXT,
          visual_concept TEXT,
          generation_prompt TEXT,
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
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS lessons (
          id TEXT PRIMARY KEY,
          brand_id TEXT NOT NULL,
          platform TEXT,
          reason_tag TEXT NOT NULL,
          note TEXT NOT NULL,
          original_body TEXT,
          edited_body TEXT,
          asset_id TEXT,
          source TEXT NOT NULL DEFAULT 'human_review',
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
          url TEXT,
          country TEXT,
          fit_score INTEGER NOT NULL DEFAULT 0,
          why TEXT,
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
          metadata TEXT,
          created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    conn.commit()

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
        except Exception:
            raw_conn = None

        if raw_conn is not None:
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


get_connection = get_db
transaction = get_db


