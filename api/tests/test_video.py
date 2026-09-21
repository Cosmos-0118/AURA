"""Tests for video generation agent and endpoints."""

import pytest
from fastapi.testclient import TestClient

from main import app
from schemas import VideoGenerateRequest

client = TestClient(app)


def test_video_config_endpoint():
    response = client.get("/api/video/config")
    assert response.status_code == 200
    data = response.json()
    assert data["model"] == "minimax/h3-max-turbo/text-to-video"
    assert data["max_duration_seconds"] == 5
    assert data["default_aspect_ratio"] == "9:16"
    assert "jade" in data["prompt_presets"]


def test_strict_5_second_duration_validation_rejection():
    # Attempting to generate a video longer than 5 seconds must be rejected with 422
    payload = {
        "prompt": "Luxury diamond ring cinematic close-up",
        "duration": 6,  # EXCEEDS 5 SECONDS
        "aspect_ratio": "9:16",
    }
    response = client.post("/api/video/generate", json=payload)
    assert response.status_code == 422


def test_strict_5_second_duration_validation_schema():
    with pytest.raises(Exception):
        VideoGenerateRequest(prompt="Test prompt", duration=10)


def test_video_generation_mock_fallback():
    payload = {
        "prompt": "An emerald watch under soft studio lighting",
        "duration": 5,
        "aspect_ratio": "9:16",
    }
    response = client.post("/api/video/generate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("COMPLETED", "FAILED")
    if data["status"] == "COMPLETED":
        assert data["video"] is not None
        assert "url" in data["video"]
        assert data["video"]["url"].endswith(".mp4")
