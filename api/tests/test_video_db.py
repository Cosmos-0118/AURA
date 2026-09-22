"""Database integration and unit smoke tests for Video Generation History."""

import datetime
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from main import app
from schemas import (
    VideoFile,
    VideoGenerateRequest,
    VideoGenerateResponse,
    VideoGenerationRecord,
    VideoSaveExportRequest,
)
from routes.video import _persist_generation, _INSERT_GENERATION, _MEMORY_HISTORY

client = TestClient(app)


def test_migration_sql_structure():
    """Verify migration SQL files contain required tables, columns, and indexes."""
    with open("../db/migrations/001_video_generations.sql", "r", encoding="utf-8") as f:
        sql1 = f.read()
    with open("../db/migrations/002_dual_video_export.sql", "r", encoding="utf-8") as f:
        sql2 = f.read()

    assert "create table if not exists video_generations" in sql1.lower()
    assert "brand_id" in sql1
    assert "asset_id" in sql1
    assert "prompt" in sql1
    assert "status" in sql1
    assert "branded_video_url" in sql2
    assert "branded_file_name" in sql2


def test_persist_generation_successful():
    """Verify _persist_generation constructs the right query and parameters."""
    body = VideoGenerateRequest(
        prompt="A luxury jewelry ring on black velvet",
        aspect_ratio="9:16",
        resolution="768P",
        duration=5,
        brand_id="jade",
        asset_id="550e8400-e29b-41d4-a716-446655440000",
    )
    response = VideoGenerateResponse(
        status="COMPLETED",
        request_id="req-12345",
        video=VideoFile(
            file_name="test.mp4",
            url="https://example.com/test.mp4",
            content_type="video/mp4",
            file_size=2048576,
        ),
    )

    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = {"id": "550e8400-e29b-41d4-a716-446655440000"}
    with patch("routes.video.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        rec_id = _persist_generation(body, response)

        assert mock_conn.execute.called
        args, _ = mock_conn.execute.call_args
        sql, params = args
        assert "insert into video_generations" in sql.lower()
        # Check passed params
        assert params[0] == "jade"
        assert params[1] == "550e8400-e29b-41d4-a716-446655440000"
        assert params[2] == "A luxury jewelry ring on black velvet"
        assert params[7] == "https://example.com/test.mp4"
        assert params[12] == "COMPLETED"
        assert params[14] == "req-12345"


def test_persist_generation_db_offline_uses_memory_store():
    """Verify _persist_generation stores to memory gracefully when DB is offline."""
    body = VideoGenerateRequest(
        prompt="Test resilient insert",
        aspect_ratio="16:9",
        duration=5,
        brand_id="doctorshield",
    )
    response = VideoGenerateResponse(
        status="FAILED",
        error="Some generation error",
        request_id="req-offline-test",
    )

    with patch("routes.video.get_connection") as mock_get_conn:
        mock_get_conn.side_effect = Exception("Postgres connection refused (simulated)")
        rec_id = _persist_generation(body, response)
        assert rec_id == "req-offline-test"

        # Verify entry in memory history
        assert any(r.request_id == "req-offline-test" for r in _MEMORY_HISTORY)


def test_export_record_endpoint():
    """Verify POST /api/video/export-record updates branded video URLs."""
    export_req = {
        "id": "550e8400-e29b-41d4-a716-446655440001",
        "branded_video_url": "blob:http://localhost:3000/branded-123",
        "branded_file_name": "branded_reel.mp4",
    }
    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchone.return_value = {"id": "550e8400-e29b-41d4-a716-446655440001"}

    with patch("routes.video.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        res = client.post("/api/video/export-record", json=export_req)
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert data["branded_video_url"] == "blob:http://localhost:3000/branded-123"


def test_get_history_with_mocked_db_rows():
    """Verify GET /api/video/history correctly formats rows into VideoGenerationRecord models."""
    now = datetime.datetime.now(datetime.timezone.utc)
    mock_rows = [
        {
            "id": "11111111-1111-1111-1111-111111111111",
            "brand_id": "jade",
            "asset_id": "22222222-2222-2222-2222-222222222222",
            "prompt": "Emerald pendant close up",
            "aspect_ratio": "9:16",
            "resolution": "768P",
            "duration_secs": 5,
            "model": "minimax/h3-max-turbo/text-to-video",
            "video_url": "https://storage.googleapis.com/test/emerald.mp4",
            "file_name": "emerald.mp4",
            "file_size": 4194304,
            "branded_video_url": "https://storage.googleapis.com/test/branded_emerald.mp4",
            "branded_file_name": "branded_emerald.mp4",
            "status": "COMPLETED",
            "error_msg": None,
            "request_id": "req-999",
            "created_at": now,
        },
    ]

    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = mock_rows

    with patch("routes.video.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        res = client.get("/api/video/history?limit=10&brand_id=jade")

        assert res.status_code == 200
        data = res.json()
        assert len(data) >= 1
        assert data[0]["id"] == "11111111-1111-1111-1111-111111111111"
        assert data[0]["brand_id"] == "jade"
        assert data[0]["video_url"] == "https://storage.googleapis.com/test/emerald.mp4"
        assert data[0]["branded_video_url"] == "https://storage.googleapis.com/test/branded_emerald.mp4"
        assert data[0]["status"] == "COMPLETED"

