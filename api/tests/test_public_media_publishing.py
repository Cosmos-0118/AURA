"""Automated Test Suite for AURA Public Media URLs & Buffer Publishing.
Tests public URL construction, localhost rejection, pre-flight reachability validation,
final watermarked media selection, duplicate publish protection, and diagnostic endpoints.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from main import app
from media.url import (
    MediaConfigurationError,
    MediaUnreachableError,
    build_public_media_url,
    get_media_config,
    validate_public_media_url_sync,
)
from publishing.buffer import BufferPublishError
from publishing.service import publish_to_platform

client = TestClient(app)


# --------------------------------------------------------------------------
# 0. Public Origin Route Boundary
# --------------------------------------------------------------------------

def test_public_media_origin_allows_media_and_health_only(monkeypatch):
    """The reserved public host must not expose the unauthenticated API."""
    public_url = "https://perceptually-homocentric-lindy.ngrok-free.dev"
    monkeypatch.setenv("MEDIA_PUBLIC_BASE_URL", public_url)

    public_headers = {"host": "perceptually-homocentric-lindy.ngrok-free.dev"}
    health_response = client.get("/api/health", headers=public_headers)
    brands_response = client.get("/api/brands", headers=public_headers)

    assert health_response.status_code == 200
    assert brands_response.status_code == 404

    forwarded_response = client.get(
        "/api/brands",
        headers={"host": "127.0.0.1:8000", "x-forwarded-host": "perceptually-homocentric-lindy.ngrok-free.dev"},
    )
    assert forwarded_response.status_code == 404


def test_local_origin_keeps_development_api_access(monkeypatch):
    """The route boundary applies to the public host, not localhost development."""
    monkeypatch.setenv("MEDIA_PUBLIC_BASE_URL", "https://perceptually-homocentric-lindy.ngrok-free.dev")

    response = client.get("/openapi.json", headers={"host": "127.0.0.1:8000"})

    assert response.status_code != 404


# --------------------------------------------------------------------------
# 1. Public URL Construction Tests
# --------------------------------------------------------------------------

def test_build_public_media_url_with_storage_prefix():
    """Verify normal conversion of storage/ path to public /media/... URL."""
    base = "https://abc123.ngrok-free.app"
    path = "storage/campaigns/123/image/final_v1.png"
    result = build_public_media_url(path, base_url=base)
    assert result == "https://abc123.ngrok-free.app/media/campaigns/123/image/final_v1.png"


def test_build_public_media_url_without_storage_prefix():
    """Verify paths stored without leading 'storage/' are normalized safely."""
    base = "https://abc123.ngrok-free.app"
    path = "campaigns/123/image/final_v1.png"
    result = build_public_media_url(path, base_url=base)
    assert result == "https://abc123.ngrok-free.app/media/campaigns/123/image/final_v1.png"


def test_build_public_media_url_video():
    """Verify video paths are formatted properly."""
    base = "https://cdn.example.com"
    path = "storage/campaigns/999/video/final_v2.mp4"
    result = build_public_media_url(path, base_url=base)
    assert result == "https://cdn.example.com/media/campaigns/999/video/final_v2.mp4"


def test_build_public_media_url_trailing_slashes_handled():
    """Verify trailing slashes in base URL do not create double slashes."""
    base = "https://abc123.ngrok-free.app///"
    path = "/storage/campaigns/456/image/final_v1.png"
    result = build_public_media_url(path, base_url=base)
    assert result == "https://abc123.ngrok-free.app/media/campaigns/456/image/final_v1.png"


# --------------------------------------------------------------------------
# 2. Missing Environment Variable & Localhost Rejection
# --------------------------------------------------------------------------

def test_missing_media_public_base_url_raises_clear_error(monkeypatch):
    """Verify missing MEDIA_PUBLIC_BASE_URL raises clear configuration error."""
    monkeypatch.delenv("MEDIA_PUBLIC_BASE_URL", raising=False)
    with pytest.raises(MediaConfigurationError) as exc_info:
        build_public_media_url("storage/campaigns/123/image/final_v1.png")
    assert "MEDIA_PUBLIC_BASE_URL is not configured" in str(exc_info.value)
    assert "Buffer requires a publicly accessible HTTPS media URL" in str(exc_info.value)


@pytest.mark.parametrize("local_url", [
    "http://localhost:8000",
    "https://localhost:8000",
    "http://127.0.0.1:8000",
    "http://0.0.0.0:8000",
])
def test_localhost_rejection(monkeypatch, local_url):
    """Verify localhost, 127.0.0.1, 0.0.0.0 are strictly rejected."""
    monkeypatch.setenv("MEDIA_PUBLIC_BASE_URL", local_url)
    with pytest.raises(MediaConfigurationError) as exc_info:
        build_public_media_url("storage/campaigns/123/image/final_v1.png")
    assert "cannot use localhost or 127.0.0.1" in str(exc_info.value)


def test_file_protocol_rejected():
    """Verify local filesystem paths or file:// paths are stripped or rejected."""
    base = "https://abc123.ngrok-free.app"
    path = "file:///Users/username/project/storage/campaigns/123/image/final_v1.png"
    result = build_public_media_url(path, base_url=base)
    assert "file://" not in result
    assert "/Users/" not in result
    assert result == "https://abc123.ngrok-free.app/media/campaigns/123/image/final_v1.png"


# --------------------------------------------------------------------------
# 3. Pre-Flight Reachability Validation Tests
# --------------------------------------------------------------------------

def test_reachability_validator_rejects_localhost():
    """Verify reachability validator immediately rejects localhost without network call."""
    with pytest.raises(MediaConfigurationError):
        validate_public_media_url_sync("http://localhost:8000/media/test.png")


def test_reachability_validator_handles_unreachable_domain():
    """Verify unreachable domain produces MediaUnreachableError with actionable message."""
    with pytest.raises(MediaUnreachableError) as exc_info:
        validate_public_media_url_sync("https://invalid-non-existent-domain-xyz-12345.com/media/test.png", timeout=2.0)
    assert "Buffer cannot access the media URL" in str(exc_info.value)


def test_reachability_validator_success_on_200():
    """Verify reachability validator succeeds when HTTP 200 is returned."""
    mock_resp = MagicMock(status_code=200)
    with patch("httpx.Client.head", return_value=mock_resp):
        res = validate_public_media_url_sync("https://example.com/media/campaigns/123/image/final_v1.png")
        assert res is True


# --------------------------------------------------------------------------
# 4. Final Watermarked Media Selection Enforcement
# --------------------------------------------------------------------------

def test_publish_rejects_original_media_when_final_missing(monkeypatch):
    """Verify publishing fails with 'Final watermarked media is not ready' when only original media exists."""
    monkeypatch.setenv("MEDIA_PUBLIC_BASE_URL", "https://abc123.ngrok-free.app")
    monkeypatch.setenv("SKIP_MEDIA_URL_REACHABILITY_CHECK", "true")

    mock_db = MagicMock()
    # 1. Campaign is approved
    mock_db.execute.return_value.fetchone.side_effect = [
        {"id": "camp_01", "status": "approved"},  # campaigns
        None,                                     # campaign_publications duplicate check
        {"content": "Approved LinkedIn Copy"},    # campaign_platform_content
        None,                                     # campaign_media (no final watermarked media found!)
    ]

    with pytest.raises(BufferPublishError) as exc_info:
        publish_to_platform(mock_db, "camp_01", "linkedin")

    assert "Final watermarked media is not ready." in str(exc_info.value)


# --------------------------------------------------------------------------
# 5. Buffer Publishing Success & Record Persistence
# --------------------------------------------------------------------------

def test_publish_success_saves_record_and_media_id(monkeypatch):
    """Verify successful Buffer publication saves status='published', buffer_post_id, and media_id."""
    monkeypatch.setenv("MEDIA_PUBLIC_BASE_URL", "https://abc123.ngrok-free.app")
    monkeypatch.setenv("SKIP_MEDIA_URL_REACHABILITY_CHECK", "true")

    mock_db = MagicMock()
    mock_db.execute.return_value.fetchone.side_effect = [
        {"id": "camp_01", "status": "approved"},
        None,  # No duplicate
        {"content": "Approved LinkedIn Post", "hashtags": ["#Security"]},
        {
            "id": "media_final_123",
            "media_type": "image",
            "local_path": "storage/campaigns/camp_01/image/final_v1.png",
            "media_stage": "final",
            "watermarked": 1,
            "status": "completed",
        },
    ]

    with patch("publishing.service.get_channel_id", return_value="chan_linkedin_1"), \
         patch("publishing.service.create_buffer_post", return_value={"post_id": "buf_post_999"}), \
         patch("publishing.service.log_event"):

        result = publish_to_platform(mock_db, "camp_01", "linkedin")

        assert result["success"] is True
        assert result["status"] == "published"
        assert result["post_id"] == "buf_post_999"

        # Verify UPDATE campaign_publications called with buffer_post_id
        update_calls = [
            str(c) for c in mock_db.execute.mock_calls
            if "UPDATE campaign_publications" in str(c)
        ]
        assert len(update_calls) > 0


# --------------------------------------------------------------------------
# 6. Buffer Failure Records Failed Status & Error Message
# --------------------------------------------------------------------------

def test_publish_failure_records_failed_status(monkeypatch):
    """Verify failed Buffer API calls update campaign_publications to status='failed'."""
    monkeypatch.setenv("MEDIA_PUBLIC_BASE_URL", "https://abc123.ngrok-free.app")
    monkeypatch.setenv("SKIP_MEDIA_URL_REACHABILITY_CHECK", "true")

    mock_db = MagicMock()
    mock_db.execute.return_value.fetchone.side_effect = [
        {"id": "camp_01", "status": "approved"},
        None,
        {"content": "Approved Content"},
        {
            "id": "media_final_123",
            "media_type": "image",
            "local_path": "storage/campaigns/camp_01/image/final_v1.png",
            "media_stage": "final",
            "watermarked": 1,
            "status": "completed",
        },
    ]

    with patch("publishing.service.get_channel_id", return_value="chan_linkedin_1"), \
         patch("publishing.service.create_buffer_post", side_effect=BufferPublishError("Buffer token expired")), \
         patch("publishing.service.log_event"):

        with pytest.raises(BufferPublishError) as exc_info:
            publish_to_platform(mock_db, "camp_01", "linkedin")

        assert "Buffer token expired" in str(exc_info.value)

        # Check for status='failed' update in DB
        failed_calls = [
            str(c) for c in mock_db.execute.mock_calls
            if "SET status = 'failed'" in str(c)
        ]
        assert len(failed_calls) > 0


# --------------------------------------------------------------------------
# 7. Duplicate Publishing Protection
# --------------------------------------------------------------------------

def test_duplicate_protection_prevents_republishing():
    """Verify that if a campaign is already published to a platform, it returns already_published=True."""
    mock_db = MagicMock()
    mock_db.execute.return_value.fetchone.side_effect = [
        {"id": "camp_01", "status": "published"},
        {
            "id": "pub_existing_1",
            "campaign_id": "camp_01",
            "platform": "linkedin",
            "status": "published",
            "buffer_post_id": "buf_existing_123",
            "external_post_url": "https://publish.buffer.com",
            "published_at": "2026-09-22T20:00:00Z",
        },
    ]

    result = publish_to_platform(mock_db, "camp_01", "linkedin")
    assert result["already_published"] is True
    assert result["success"] is False
    assert result["post_id"] == "buf_existing_123"


# --------------------------------------------------------------------------
# 8. Diagnostics Endpoint (GET /api/media/config)
# --------------------------------------------------------------------------

def test_media_config_endpoint_configured(monkeypatch):
    """Verify GET /api/media/config returns configured=True and base_url."""
    monkeypatch.setenv("MEDIA_PUBLIC_BASE_URL", "https://abc123.ngrok-free.app")
    resp = client.get("/api/media/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["configured"] is True
    assert data["base_url"] == "https://abc123.ngrok-free.app"
    assert data["media_endpoint_available"] is True


def test_media_config_endpoint_unconfigured(monkeypatch):
    """Verify GET /api/media/config returns configured=False when unset."""
    monkeypatch.delenv("MEDIA_PUBLIC_BASE_URL", raising=False)
    resp = client.get("/api/media/config")
    assert resp.status_code == 200
    data = resp.json()
    assert data["configured"] is False
    assert data["base_url"] is None
