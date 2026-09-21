from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

try:
    from .routes import assets, brands, campaigns, competitors, leads, lessons, metrics
except ImportError:  # Supports `cd api && uv run uvicorn main:app`.
    from routes import assets, brands, campaigns, competitors, leads, lessons, metrics

app = FastAPI(title="AURA API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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
def health() -> dict[str, bool]:
    return {"ok": True}


app.include_router(brands.router)
app.include_router(competitors.router)
app.include_router(campaigns.router)
app.include_router(assets.router)
app.include_router(lessons.router)
app.include_router(leads.router)
app.include_router(metrics.router)

