from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

try:
    from .agents.lead_intel import start_daily_refresh
    from .services.competitor_intelligence import (
        competitor_readiness,
        start_competitor_refresh,
    )
    from .routes import assets, brands, buffer, campaigns, competitors, leads, lessons, metrics, video
except ImportError:  # Supports `cd api && uv run uvicorn main:app`.
    from agents.lead_intel import start_daily_refresh
    from services.competitor_intelligence import (  # type: ignore[no-redef]
        competitor_readiness,
        start_competitor_refresh,
    )
    from routes import assets, brands, buffer, campaigns, competitors, leads, lessons, metrics, video

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

# Ensure storage and logos directories exist and mount as static files
storage_path = Path(__file__).resolve().parent.parent / "storage"
storage_path.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(storage_path)), name="media")
app.mount("/storage", StaticFiles(directory=str(storage_path)), name="storage")

logos_path = Path(__file__).resolve().parent.parent / "web" / "public" / "logos"
if not logos_path.exists():
    logos_path = Path(__file__).resolve().parent.parent / "web" / "public" / "logo"
if logos_path.exists():
    app.mount("/logos", StaticFiles(directory=str(logos_path)), name="logos")


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
            res.append({
                "id": base,
                "name": name_map.get(base, base.title()),
                "file": f.name,
                "src": f"/logos/{f.name}",
            })
    return res


app.include_router(brands.router)
app.include_router(competitors.router)
app.include_router(campaigns.router)
app.include_router(assets.router)
app.include_router(lessons.router)
app.include_router(leads.router)
app.include_router(metrics.router)
app.include_router(video.router)
app.include_router(buffer.router)
