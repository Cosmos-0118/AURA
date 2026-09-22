from __future__ import annotations

import json
import os
from pathlib import Path

from .models import Competitor, WatchSource


ROOT = Path(__file__).resolve().parent.parent


def project_env(name: str, default: str = "") -> str:
    """Read only the requested setting from AURA's local .env in local mode."""
    if name in os.environ:
        return os.environ[name]
    env_path = ROOT.parent / ".env"
    if env_path.is_file():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            key, separator, value = line.partition("=")
            if separator and key.strip() == name:
                return value.strip().strip('"\'')
    return default


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
WATCHES_PATH = Path(os.getenv("INTEL_WATCHES", str(ROOT / "config" / "watches.json")))
REQUEST_TIMEOUT = env_int("INTEL_REQUEST_TIMEOUT", 20)
SCAN_INTERVAL = env_int("INTEL_SCAN_INTERVAL", 900)
SEARXNG_URL = os.getenv("SEARXNG_URL", "").rstrip("/")
WEBHOOK_TOKEN = os.getenv("INTEL_WEBHOOK_TOKEN", "")
CHANGEDETECTION_API_URL = os.getenv("CHANGEDETECTION_API_URL", "http://changedetection:5000").rstrip("/")
CHANGEDETECTION_API_KEY = os.getenv("CHANGEDETECTION_API_KEY", "")
GEMINI_API_KEY = project_env("GEMINI_API_KEY")
GEMINI_MODEL = project_env("GEMINI_MODEL", "gemini-3.6-flash")


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


def load_watches(path: Path = WATCHES_PATH) -> list[WatchSource]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError(f"Watch configuration must be a list: {path}")
    watches = [WatchSource(**item) for item in raw]
    if len({watch.id for watch in watches}) != len(watches):
        raise ValueError("Watch IDs must be unique")
    return watches
