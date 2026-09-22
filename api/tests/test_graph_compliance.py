from types import SimpleNamespace

from graph import _compliance_text


def test_pipeline_compliance_input_includes_title_body_and_hashtags():
    generated = SimpleNamespace(
        title="Guaranteed protection",
        body="Review the policy terms.",
        hashtags=["Insurance", "RiskManagement"],
    )

    text = _compliance_text(generated)

    assert "Guaranteed protection" in text
    assert "Review the policy terms." in text
    assert "Insurance RiskManagement" in text
