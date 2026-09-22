"""Native AURA routes for competitor monitoring and intelligence."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request

try:
    from ..schemas import BrandId, Competitor, Snapshot
    from ..services.competitor_intelligence import (
        get_intelligence_service,
        service_payload,
    )
except ImportError:  # Supports `cd api && uv run uvicorn main:app`.
    from schemas import BrandId, Competitor, Snapshot  # type: ignore[no-redef]
    from services.competitor_intelligence import (  # type: ignore[no-redef]
        get_intelligence_service,
        service_payload,
    )

router = APIRouter(prefix="/api/competitors", tags=["competitors"])


def _service():
    try:
        return get_intelligence_service()
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Competitor intelligence storage is unavailable: {exc}",
        ) from exc


def _event_filters(
    brand_id: BrandId | None = None,
    country: str | None = None,
    impact: str | None = None,
    change_type: str | None = None,
    source: str | None = None,
    search: str | None = None,
) -> dict[str, str]:
    return {
        key: value
        for key, value in {
            "brand_id": brand_id,
            "country": country,
            "impact": impact,
            "change_type": change_type,
            "source": source,
            "search": search,
        }.items()
        if value
    }


@router.get("/dashboard")
def competitor_dashboard(brand_id: BrandId | None = None) -> dict[str, Any]:
    """Return the complete native dashboard payload from the AURA API."""

    service = _service()
    payload = service_payload(service)
    if brand_id:
        payload["competitors"] = [
            item for item in payload["competitors"] if item["brand_id"] == brand_id
        ]
        payload["monitors"] = [
            item for item in payload["monitors"] if item["brand_id"] == brand_id
        ]
        payload["events"] = [
            item for item in payload["events"] if item["brand_id"] == brand_id
        ]
    return payload


@router.get("/events")
def list_competitor_events(
    brand_id: BrandId | None = None,
    country: str | None = None,
    impact: str | None = None,
    change_type: str | None = None,
    source: str | None = None,
    search: str | None = None,
) -> list[dict[str, Any]]:
    return _service().events(_event_filters(brand_id, country, impact, change_type, source, search))


@router.get("/monitors")
def list_competitor_monitors() -> list[dict[str, Any]]:
    return _service().monitor_status()


@router.get("/watches")
def list_competitor_watches() -> list[dict[str, Any]]:
    return _service().watch_status()


@router.get("/source-health")
def competitor_source_health() -> list[dict[str, str]]:
    return _service().source_health()


@router.get("/events/{event_id}/diff")
def competitor_event_diff(event_id: str) -> dict[str, Any]:
    evidence = _service().event_diff(event_id)
    if evidence is None:
        raise HTTPException(status_code=404, detail="Event evidence not found")
    return evidence


@router.get("", response_model=list[Competitor])
def list_competitors(brand_id: BrandId | None = None) -> list[Competitor]:
    service = _service()
    return [
        Competitor(
            id=item.id,
            brand_id=item.brand_id,
            name=item.name,
            url=item.url,
        )
        for item in service.competitors()
        if brand_id is None or item.brand_id == brand_id
    ]


@router.post("/scan-all")
def scan_all_competitors() -> list[dict[str, Any]]:
    return [result.to_dict() for result in _service().scan_all()]


@router.post("/watches/{watch_id}/scan")
def scan_competitor_watch(watch_id: str) -> dict[str, Any]:
    service = _service()
    watch = next((item for item in service.watches() if item.id == watch_id), None)
    if watch is None:
        raise HTTPException(status_code=404, detail="Watch not found")
    return service.scan_watch(watch).to_dict()


@router.post("/events/{event_id}/analyze")
def analyze_competitor_event(event_id: str) -> dict[str, str]:
    try:
        analysis = _service().analyze_event(event_id)
    except PermissionError as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if analysis is None:
        raise HTTPException(status_code=404, detail="Event evidence not found")
    return analysis


@router.post("/webhooks/changedetection", status_code=202)
def ingest_changedetection_webhook(request: Request, payload: dict[str, Any]) -> dict[str, Any] | list[dict[str, Any]]:
    import os

    expected_token = os.getenv("INTEL_WEBHOOK_TOKEN", "")
    if expected_token and request.headers.get("X-Webhook-Token") != expected_token:
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    service = _service()
    try:
        competitor_ids = payload.get("competitor_ids")
        if isinstance(competitor_ids, list):
            return [
                service.ingest_changedetection(
                    {**payload, "competitor_id": competitor_id}
                ).to_dict()
                for competitor_id in competitor_ids
            ]
        return service.ingest_changedetection(payload).to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/poll-feeds")
def poll_competitor_feeds() -> list[dict[str, Any]]:
    try:
        return _service().poll_feeds()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/sync-changedetection")
def sync_changedetection() -> dict[str, Any]:
    try:
        return _service().sync_changedetection()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Changedetection sync failed: {exc}") from exc


@router.post("/search")
def search_competitors(payload: dict[str, Any]) -> list[dict[str, str]]:
    query = str(payload.get("query", "")).strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    try:
        return _service().search(query)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/{competitor_id}/scan", response_model=Snapshot)
def scan_competitor(competitor_id: str) -> Snapshot:
    service = _service()
    result = service.scan(competitor_id)
    if result.status == "not_found":
        raise HTTPException(status_code=404, detail=result.error or "Competitor not found")
    if result.status == "error":
        raise HTTPException(status_code=502, detail=result.error or "Competitor scan failed")

    snapshot = service.store.latest_snapshot(competitor_id)
    if snapshot is None:
        raise HTTPException(status_code=502, detail="Competitor scan did not persist a snapshot")
    return Snapshot(
        id=snapshot.id,
        competitor_id=snapshot.competitor_id,
        content_hash=snapshot.content_hash,
        change_summary=snapshot.change_summary,
        scraped_at=snapshot.scraped_at,
    )
