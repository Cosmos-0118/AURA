"""Buffer publish client tests. These never call the live Buffer API."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from agents.buffer import BufferPublishRequest, _build_input
from main import app

client = TestClient(app)


def test_status_reports_missing_key():
    with patch("agents.buffer.api_key", return_value=""):
        response = client.get("/api/buffer/status")
    assert response.status_code == 200
    assert response.json()["configured"] is False


def test_channels_returns_connected_profiles():
    sample = [
        {
            "id": "ch_li",
            "name": "aura-li",
            "display_name": "AURA LinkedIn",
            "service": "linkedin",
            "avatar": "",
            "is_queue_paused": False,
            "organization_id": "org_1",
            "organization_name": "AURA",
        }
    ]
    with patch("routes.buffer.list_channels") as listed:
        listed.return_value = []
        from agents.buffer import BufferChannel

        listed.return_value = [BufferChannel(**sample[0])]
        response = client.get("/api/buffer/channels")
    assert response.status_code == 200
    assert response.json()["channels"][0]["service"] == "linkedin"


def test_publish_builds_automatic_share_now_with_image():
    payload = _build_input(
        BufferPublishRequest(
            channel_id="ch_1",
            text="Hello from AURA",
            mode="shareNow",
            image_url="https://example.com/photo.jpg",
            instagram_type="reel",
        )
    )
    assert payload["schedulingType"] == "automatic"
    assert payload["mode"] == "shareNow"
    assert payload["assets"][0]["image"]["url"].endswith("photo.jpg")
    assert payload["metadata"]["instagram"]["type"] == "reel"
    assert payload["metadata"]["instagram"]["shouldShareToFeed"] is True


def test_publish_endpoint_returns_post_id():
    from agents.buffer import BufferPublishResult

    with patch("routes.buffer.publish_post") as publish:
        publish.return_value = BufferPublishResult(
            ok=True,
            post_id="post_1",
            due_at=None,
            message="Buffer accepted the post (published immediately).",
        )
        response = client.post(
            "/api/buffer/publish",
            json={"channel_id": "ch_1", "text": "Test caption", "mode": "shareNow"},
        )
    assert response.status_code == 200
    assert response.json()["post_id"] == "post_1"
