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
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure storage directory exists and mount as static files
storage_path = Path(__file__).resolve().parent.parent / "storage"
storage_path.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(storage_path)), name="media")
app.mount("/storage", StaticFiles(directory=str(storage_path)), name="storage")



@app.get("/api/health", tags=["health"])
def health() -> dict[str, object]:
    payload: dict[str, object] = {"ok": True}
    try:
        payload["competitor_intelligence"] = competitor_readiness()
    except Exception as exc:  # pragma: no cover - defensive health reporting
        payload["competitor_intelligence"] = {"ready": False, "error": str(exc)}
    return payload


app.include_router(brands.router)
app.include_router(competitors.router)
app.include_router(campaigns.router)
app.include_router(assets.router)
app.include_router(lessons.router)
app.include_router(leads.router)
app.include_router(metrics.router)
app.include_router(video.router)
app.include_router(buffer.router)
