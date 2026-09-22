from __future__ import annotations

import json
import os
from pathlib import Path

from .models import Competitor


ROOT = Path(__file__).resolve().parent.parent


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


HOST = os.getenv("INTEL_HOST", "127.0.0.1")
PORT = env_int("INTEL_PORT", 8787)
DB_PATH = Path(os.getenv("INTEL_DB_PATH", str(ROOT / "data" / "intelligence.db")))
COMPETITORS_PATH = Path(
    os.getenv("INTEL_COMPETITORS", str(ROOT / "config" / "competitors.json"))
)
FEEDS_PATH = Path(os.getenv("INTEL_FEEDS", str(ROOT / "config" / "feeds.json")))
REQUEST_TIMEOUT = env_int("INTEL_REQUEST_TIMEOUT", 20)
SCAN_INTERVAL = env_int("INTEL_SCAN_INTERVAL", 900)
SEARXNG_URL = os.getenv("SEARXNG_URL", "").rstrip("/")
WEBHOOK_TOKEN = os.getenv("INTEL_WEBHOOK_TOKEN", "")
CHANGEDETECTION_API_URL = os.getenv("CHANGEDETECTION_API_URL", "http://changedetection:5000").rstrip("/")
CHANGEDETECTION_API_KEY = os.getenv("CHANGEDETECTION_API_KEY", "")


def load_competitors(path: Path = COMPETITORS_PATH) -> list[Competitor]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"Competitor configuration must be a list: {path}")
    return [Competitor(**item) for item in raw]


def load_feeds(path: Path = FEEDS_PATH) -> list[dict[str, str]]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"Feed configuration must be a list: {path}")
    return [item for item in raw if isinstance(item, dict) and item.get("url")]
