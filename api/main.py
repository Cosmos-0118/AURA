import os
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv

_ROOT_ENV = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ROOT_ENV)
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

try:
    from .agents.lead_intel import start_daily_refresh
    from .services.competitor_intelligence import (
        competitor_readiness,
        start_competitor_refresh,
    )
    from .routes import assets, brands, buffer, campaigns, competitors, leads, lessons, media, metrics
except ImportError:  # Supports `cd api && uv run uvicorn main:app`.
    from agents.lead_intel import start_daily_refresh
    from services.competitor_intelligence import (  # type: ignore[no-redef]
        competitor_readiness,
        start_competitor_refresh,
    )
    from routes import assets, brands, buffer, campaigns, competitors, leads, lessons, media, metrics

RESERVED_PUBLIC_MEDIA_HOST = "perceptually-homocentric-lindy.ngrok-free.dev"

app = FastAPI(
    title="AURA API",
    version="0.1.0",
    on_startup=[start_daily_refresh, start_competitor_refresh],
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def restrict_public_media_origin(request, call_next):
    """Limit the configured public media origin to safe read-only routes.

    The local development API remains unauthenticated by design. When the
    reserved public media hostname is used by ngrok or another reverse proxy,
    only media reads and the non-sensitive health check should be reachable.
    """
    configured_base = os.getenv("MEDIA_PUBLIC_BASE_URL", "").strip().rstrip("/")
    configured_host = (urlparse(configured_base).hostname or "").lower()
    public_hosts = {RESERVED_PUBLIC_MEDIA_HOST, configured_host} - {""}
    request_host = (request.url.hostname or "").lower()
    forwarded_host = request.headers.get("x-forwarded-host", "").split(",", 1)[0].split(":", 1)[0].lower()
    addressed_hosts = {request_host, forwarded_host} - {""}
    public_path = request.url.path
    allowed_public_path = public_path == "/api/health" or public_path.startswith("/media/")
    allowed_public_method = request.method in {"GET", "HEAD"}

    if public_hosts.intersection(addressed_hosts) and (
        not allowed_public_method or not allowed_public_path
    ):
        return JSONResponse(
            status_code=404,
            content={"detail": "This public origin only serves media files."},
        )

    return await call_next(request)


# Ensure storage and logos directories exist and mount as static files
storage_path = Path(__file__).resolve().parent.parent / "storage"
storage_path.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(storage_path)), name="media")
app.mount("/storage", StaticFiles(directory=str(storage_path)), name="storage")

logo_dir = Path(__file__).resolve().parent.parent / "web" / "public" / "logo"
if not logo_dir.exists():
    logo_dir = Path(__file__).resolve().parent.parent / "web" / "public" / "logos"
if logo_dir.exists():
    app.mount("/logo", StaticFiles(directory=str(logo_dir)), name="logo")
    app.mount("/logos", StaticFiles(directory=str(logo_dir)), name="logos")


@app.get("/api/health", tags=["health"])
def health() -> dict[str, object]:
    payload: dict[str, object] = {"ok": True}
    try:
        payload["competitor_intelligence"] = competitor_readiness()
    except Exception as exc:  # pragma: no cover - defensive health reporting
        payload["competitor_intelligence"] = {"ready": False, "error": str(exc)}
    return payload


@app.get("/api/logos", tags=["logos"])
def list_logos() -> list[dict[str, str]]:
    """Return available brand logos discovered in web/public/logos/."""
    logos_dir = Path(__file__).resolve().parent.parent / "web" / "public" / "logos"
    if not logos_dir.exists():
        logos_dir = Path(__file__).resolve().parent.parent / "web" / "public" / "logo"
    if not logos_dir.exists():
        return []

    res = []
    seen = set()
    name_map = {
        "jade": "Jade",
        "doctorshield": "DoctorShield",
        "jaguar": "Jaguar Transit",
        "jaguar-transit": "Jaguar Transit",
        "ja": "JA Assure",
        "ja-assure": "JA Assure",
    }
    for f in sorted(logos_dir.iterdir()):
        if f.suffix.lower() in [".png", ".jpg", ".jpeg", ".svg", ".webp"]:
            base = f.stem.lower()
            if base in seen:
                continue
            seen.add(base)
            name = name_map.get(base, base.title())
            res.append({
                "id": base,
                "name": name,
                "file": f.name,
                "filename": f.name,
                "src": f"/logo/{f.name}",
                "url": f"/logo/{f.name}",
            })
    return res


app.include_router(brands.router)
app.include_router(competitors.router)
app.include_router(campaigns.router)
app.include_router(assets.router)
app.include_router(lessons.router)
app.include_router(leads.router)
app.include_router(metrics.router)
app.include_router(buffer.router)
app.include_router(media.router)
