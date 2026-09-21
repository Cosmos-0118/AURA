"""Tests for the M4 content engine.

Run with:
    cd api && uv run python -m pytest tests/content/ -v

All tests are offline — no network calls, no database required.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

# Support both package and direct invocation import styles
try:
    from agents.content import (
        _BANNED_WORDS,
        _deterministic_asset,
        _validate_gemini_output,
        generate_content,
    )
    from prompts.content.linkedin import BRAND_VOICES, build_gemini_prompt, render_brand
    from schemas import ContentRequest, GeneratedAsset
except ImportError:
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    from agents.content import (  # type: ignore[no-redef]
        _BANNED_WORDS,
        _deterministic_asset,
        _validate_gemini_output,
        generate_content,
    )
    from prompts.content.linkedin import BRAND_VOICES, build_gemini_prompt, render_brand  # type: ignore[no-redef]
    from schemas import ContentRequest, GeneratedAsset  # type: ignore[no-redef]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _req(
    brand_id: str = "jade",
    platforms: list[str] | None = None,
    lessons: list[str] | None = None,
    topic: str = "fine jewellery risk assessment",
    country: str = "Malaysia",
    goal: str = "educate retailers on specialist coverage",
) -> ContentRequest:
    return ContentRequest(
        brand_id=brand_id,
        topic=topic,
        country=country,
        goal=goal,
        platforms=platforms or ["linkedin"],
        lessons=lessons or [],
    )


# ---------------------------------------------------------------------------
# Phase 2: Deterministic A/B LinkedIn Generation
# ---------------------------------------------------------------------------


class TestLinkedInGeneration:
    def test_linkedin_returns_two_variants(self):
        """LinkedIn always produces exactly two variants: A and B."""
        assets = generate_content(_req(platforms=["linkedin"]))
        assert len(assets) == 2
        variants = {a.variant for a in assets}
        assert variants == {"A", "B"}

    def test_brands_produce_different_output(self):
        """Each brand generates recognisably different copy."""
        jade = generate_content(_req(brand_id="jade", topic="inventory risk"))
        ds = generate_content(_req(brand_id="doctorshield", topic="inventory risk"))
        jaguar = generate_content(_req(brand_id="jaguar", topic="inventory risk"))

        jade_bodies = {a.body for a in jade}
        ds_bodies = {a.body for a in ds}
        jaguar_bodies = {a.body for a in jaguar}

        # No body should be shared across brands
        assert jade_bodies.isdisjoint(ds_bodies)
        assert jade_bodies.isdisjoint(jaguar_bodies)
        assert ds_bodies.isdisjoint(jaguar_bodies)

    def test_variant_a_differs_from_variant_b_per_brand(self):
        """Variant A and B must produce different bodies for the same brand."""
        for brand_id in ("jade", "doctorshield", "jaguar"):
            assets = generate_content(_req(brand_id=brand_id))
            bodies = [a.body for a in assets]
            assert bodies[0] != bodies[1], f"A == B for brand {brand_id}"

    def test_lessons_influence_copy(self):
        """Supplying lessons should change the deterministic output."""
        without = generate_content(_req(lessons=[]))
        with_lessons = generate_content(_req(lessons=["Avoid pricing references", "Use inclusive language"]))
        bodies_without = {a.body for a in without}
        bodies_with = {a.body for a in with_lessons}
        # At least one body should differ
        assert bodies_without != bodies_with

    def test_only_requested_platforms(self):
        """Only platforms in the request are returned."""
        assets = generate_content(_req(platforms=["linkedin"]))
        assert all(a.platform == "linkedin" for a in assets)

    def test_unknown_platform_skipped(self):
        """Platforms outside linkedin/instagram are silently skipped."""
        assets = generate_content(_req(platforms=["x", "blog"]))
        assert assets == []

    def test_no_banned_words(self):
        """None of the three brands should produce banned words."""
        for brand_id in ("jade", "doctorshield", "jaguar"):
            assets = generate_content(_req(brand_id=brand_id))
            for asset in assets:
                body_lower = asset.body.lower()
                for word in _BANNED_WORDS:
                    assert word not in body_lower, (
                        f"Banned word '{word}' found in {brand_id} body"
                    )

    def test_returns_pydantic_objects(self):
        """Assets must be valid Pydantic GeneratedAsset instances."""
        assets = generate_content(_req())
        for asset in assets:
            assert isinstance(asset, GeneratedAsset)
            # Round-trip validation
            revalidated = GeneratedAsset.model_validate(asset.model_dump())
            assert revalidated.body == asset.body

    def test_hashtags_have_no_hash_prefix(self):
        """Hashtag strings must not start with '#'."""
        assets = generate_content(_req())
        for asset in assets:
            for tag in asset.hashtags:
                assert not tag.startswith("#"), f"Tag has # prefix: {tag}"

    def test_all_three_brands_linkedin(self):
        """Smoke test: all brands produce 2 valid LinkedIn assets."""
        for brand_id in ("jade", "doctorshield", "jaguar"):
            assets = generate_content(_req(brand_id=brand_id, platforms=["linkedin"]))
            assert len(assets) == 2, f"Expected 2 assets for {brand_id}"
            for asset in assets:
                assert asset.platform == "linkedin"
                assert asset.content_type == "post"
                assert len(asset.body) >= 50


# ---------------------------------------------------------------------------
# Phase 3: Gemini fallback paths
# ---------------------------------------------------------------------------


class TestGeminiFallback:
    """All tests mock the network — no real Gemini calls."""

    def _make_valid_gemini_response(self, platform: str = "linkedin") -> dict:
        return {
            "platform": platform,
            "content_type": "post",
            "variant": "A",
            "title": "Gemini Title",
            "body": "This is a Gemini-generated body long enough to pass validation checks.",
            "hashtags": ["GeminiTag", "TestTag"],
        }

    def test_missing_api_key_returns_deterministic(self):
        """When GEMINI_API_KEY is empty, deterministic path is used."""
        with patch("agents.content._GEMINI_API_KEY", ""):
            assets = generate_content(_req())
        assert len(assets) == 2
        for asset in assets:
            assert isinstance(asset, GeneratedAsset)

    def test_placeholder_api_key_returns_deterministic(self):
        """When key is the placeholder string, deterministic path is used."""
        with patch("agents.content._GEMINI_API_KEY", "your_personal_gemini_key"):
            assets = generate_content(_req())
        assert len(assets) == 2

    def test_invalid_json_falls_back(self):
        """Invalid JSON from Gemini triggers deterministic fallback."""
        with patch("agents.content._GEMINI_API_KEY", "fake-key-12345"):
            with patch("httpx.post") as mock_post:
                mock_post.return_value.raise_for_status = lambda: None
                mock_post.return_value.json.return_value = {
                    "candidates": [{"content": {"parts": [{"text": "not-json-{{{"}]}}]
                }
                assets = generate_content(_req())
        assert len(assets) == 2
        for asset in assets:
            assert isinstance(asset, GeneratedAsset)

    def test_wrong_platform_in_response_falls_back(self):
        """Gemini returning wrong platform triggers deterministic fallback."""
        bad_response = self._make_valid_gemini_response(platform="instagram")
        import json as _json
        with patch("agents.content._GEMINI_API_KEY", "fake-key-12345"):
            with patch("httpx.post") as mock_post:
                mock_post.return_value.raise_for_status = lambda: None
                mock_post.return_value.json.return_value = {
                    "candidates": [{"content": {"parts": [{"text": _json.dumps(bad_response)}]}}]
                }
                assets = generate_content(_req(platforms=["linkedin"]))
        assert len(assets) == 2
        assert all(a.platform == "linkedin" for a in assets)

    def test_banned_words_in_gemini_output_falls_back(self):
        """Gemini output containing banned words triggers deterministic fallback."""
        import json as _json
        bad_response = self._make_valid_gemini_response()
        bad_response["body"] = "This is guaranteed to work and is 100% covered."

        with patch("agents.content._GEMINI_API_KEY", "fake-key-12345"):
            with patch("httpx.post") as mock_post:
                mock_post.return_value.raise_for_status = lambda: None
                mock_post.return_value.json.return_value = {
                    "candidates": [{"content": {"parts": [{"text": _json.dumps(bad_response)}]}}]
                }
                assets = generate_content(_req())
        # Should still get 2 assets via deterministic fallback
        assert len(assets) == 2
        for asset in assets:
            assert "guaranteed" not in asset.body.lower()

    def test_network_timeout_falls_back(self):
        """Network timeout triggers deterministic fallback."""
        import httpx as _httpx
        with patch("agents.content._GEMINI_API_KEY", "fake-key-12345"):
            with patch("httpx.post", side_effect=_httpx.TimeoutException("timeout")):
                assets = generate_content(_req())
        assert len(assets) == 2
        for asset in assets:
            assert isinstance(asset, GeneratedAsset)

    def test_http_error_falls_back(self):
        """HTTP error response triggers deterministic fallback."""
        with patch("agents.content._GEMINI_API_KEY", "fake-key-12345"):
            with patch("httpx.post") as mock_post:
                mock_post.return_value.raise_for_status.side_effect = Exception("429 Too Many Requests")
                assets = generate_content(_req())
        assert len(assets) == 2

    def test_body_too_short_falls_back(self):
        """Gemini output with body < 20 chars triggers fallback."""
        import json as _json
        bad_response = self._make_valid_gemini_response()
        bad_response["body"] = "Short."

        with patch("agents.content._GEMINI_API_KEY", "fake-key-12345"):
            with patch("httpx.post") as mock_post:
                mock_post.return_value.raise_for_status = lambda: None
                mock_post.return_value.json.return_value = {
                    "candidates": [{"content": {"parts": [{"text": _json.dumps(bad_response)}]}}]
                }
                assets = generate_content(_req())
        for asset in assets:
            assert len(asset.body) >= 20


# ---------------------------------------------------------------------------
# Phase 4: Lesson awareness
# ---------------------------------------------------------------------------


class TestLessonAwareness:
    def test_lessons_appear_in_gemini_prompt(self):
        """Lessons are injected into the Gemini system prompt."""
        lessons = ["Avoid pricing references", "Use inclusive language"]
        req = _req(lessons=lessons)
        prompt = build_gemini_prompt(req, "linkedin", "A")
        for lesson in lessons:
            assert lesson in prompt

    def test_deterministic_body_changes_with_lessons(self):
        """Lesson text changes the deterministic body for each brand."""
        for brand_id in ("jade", "doctorshield", "jaguar"):
            without = render_brand(
                brand_id=brand_id, topic="risk", country="SG",
                goal="educate", lessons=[], variant="A",
            )
            with_lessons = render_brand(
                brand_id=brand_id, topic="risk", country="SG",
                goal="educate", lessons=["Be more concise"], variant="A",
            )
            assert without["body"] != with_lessons["body"], (
                f"Lessons did not change body for brand {brand_id}"
            )

    def test_multiple_lessons_all_reflected(self):
        """Multiple lessons produce a different body than zero lessons."""
        for brand_id in ("jade", "doctorshield", "jaguar"):
            many_lessons = ["Lesson 1", "Lesson 2", "Lesson 3"]
            rendered = render_brand(
                brand_id=brand_id, topic="risk", country="SG",
                goal="educate", lessons=many_lessons, variant="B",
            )
            # The lesson sentence should reference multiple insights
            assert "3" in rendered["body"] or "insight" in rendered["body"]


# ---------------------------------------------------------------------------
# Validation unit tests
# ---------------------------------------------------------------------------


class TestValidateGeminiOutput:
    def test_valid_output_passes(self):
        assert _validate_gemini_output(
            {
                "platform": "linkedin",
                "content_type": "post",
                "body": "A" * 50,
                "hashtags": [],
            },
            "linkedin",
        )

    def test_missing_required_field_fails(self):
        assert not _validate_gemini_output(
            {"platform": "linkedin", "content_type": "post"},  # missing body
            "linkedin",
        )

    def test_wrong_platform_fails(self):
        assert not _validate_gemini_output(
            {"platform": "instagram", "content_type": "caption", "body": "A" * 50},
            "linkedin",
        )

    def test_short_body_fails(self):
        assert not _validate_gemini_output(
            {"platform": "linkedin", "content_type": "post", "body": "Too short"},
            "linkedin",
        )

    def test_banned_word_fails(self):
        for word in ("guaranteed", "100% covered", "zero risk"):
            assert not _validate_gemini_output(
                {
                    "platform": "linkedin",
                    "content_type": "post",
                    "body": f"This is {word} to be a great post with enough length.",
                },
                "linkedin",
            )
