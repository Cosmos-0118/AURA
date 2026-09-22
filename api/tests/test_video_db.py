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
)
from routes.video import _persist_generation, _INSERT_GENERATION

client = TestClient(app)


def test_migration_sql_structure():
    """Verify migration SQL file contains required table, columns, and indexes."""
    with open("../db/migrations/001_video_generations.sql", "r", encoding="utf-8") as f:
        sql = f.read()

    assert "create table if not exists video_generations" in sql.lower()
    assert "brand_id" in sql
    assert "asset_id" in sql
    assert "prompt" in sql
    assert "aspect_ratio" in sql
    assert "resolution" in sql
    assert "duration_secs" in sql
    assert "video_url" in sql
    assert "file_name" in sql
    assert "file_size" in sql
    assert "status" in sql
    assert "created_at" in sql
    assert "idx_video_gen_created" in sql
    assert "idx_video_gen_brand" in sql


def test_persist_generation_successful():
    """Verify _persist_generation constructs the right query and parameters."""
    body = VideoGenerateRequest(
        prompt="A luxury jewelry ring on black velvet",
        aspect_ratio="9:16",
        resolution="768P",
        duration=5,
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
    with patch("routes.video.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        _persist_generation(body, response)

        assert mock_conn.execute.called
        args, _ = mock_conn.execute.call_args
        sql, params = args
        assert "insert into video_generations" in sql.lower()
        # Check passed params
        assert params[2] == "A luxury jewelry ring on black velvet"
        assert params[3] == "9:16"
        assert params[4] == "768P"
        assert params[5] == 5
        assert params[7] == "https://example.com/test.mp4"
        assert params[10] == "COMPLETED"
        assert params[12] == "req-12345"


def test_persist_generation_db_offline_does_not_raise():
    """Verify _persist_generation gracefully handles DB outages without failing."""
    body = VideoGenerateRequest(
        prompt="Test resilient insert",
        aspect_ratio="16:9",
        duration=5,
    )
    response = VideoGenerateResponse(status="FAILED", error="Some generation error")

    with patch("routes.video.get_connection") as mock_get_conn:
        mock_get_conn.side_effect = Exception("Postgres connection refused (simulated)")
        # Must not raise an exception
        _persist_generation(body, response)


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
            "status": "COMPLETED",
            "error_msg": None,
            "request_id": "req-999",
            "created_at": now,
        },
        {
            "id": "33333333-3333-3333-3333-333333333333",
            "brand_id": "doctorshield",
            "asset_id": None,
            "prompt": "Doctor consultation room",
            "aspect_ratio": "16:9",
            "resolution": "1080P",
            "duration_secs": 5,
            "model": "minimax/h3-max-turbo/text-to-video",
            "video_url": None,
            "file_name": None,
            "file_size": None,
            "status": "FAILED",
            "error_msg": "Safety policy triggered",
            "request_id": "req-888",
            "created_at": now - datetime.timedelta(minutes=5),
        },
    ]

    mock_conn = MagicMock()
    mock_conn.execute.return_value.fetchall.return_value = mock_rows

    with patch("routes.video.get_connection") as mock_get_conn:
        mock_get_conn.return_value.__enter__.return_value = mock_conn
        res = client.get("/api/video/history?limit=10&brand_id=jade")

        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2
        assert data[0]["id"] == "11111111-1111-1111-1111-111111111111"
        assert data[0]["brand_id"] == "jade"
        assert data[0]["prompt"] == "Emerald pendant close up"
        assert data[0]["video_url"] == "https://storage.googleapis.com/test/emerald.mp4"
        assert data[0]["status"] == "COMPLETED"

        assert data[1]["id"] == "33333333-3333-3333-3333-333333333333"
        assert data[1]["status"] == "FAILED"
        assert data[1]["error_msg"] == "Safety policy triggered"


def test_get_history_db_offline_fallback():
    """Verify GET /api/video/history returns [] when database is unreachable."""
    with patch("routes.video.get_connection") as mock_get_conn:
        mock_get_conn.side_effect = Exception("Database connection failed (simulated)")
        res = client.get("/api/video/history")
        assert res.status_code == 200
        assert res.json() == []
