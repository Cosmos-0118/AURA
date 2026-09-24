"""Lead outreach is gated by human approval and freezes uncertain sends."""

from unittest.mock import patch

import pytest

from agents.lead_mail import LeadMailError, build_message, draft_for, send_for


class _NoSuppressionConnection:
    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, *_args):
        return self

    def fetchone(self):
        return None


def _approved_lead(lead_id="lead-1"):
    return {
        "id": lead_id,
        "brand_id": "jade",
        "name": "Northwind Jewellers",
        "email": "info@northwind.example",
        "domain": "northwind.example",
        "requirements": "Wholesale jewellery showrooms across Malaysia.",
        "review_status": "approved",
        "outreach_status": "approved",
        "status": "qualified",
        "stage": "qualified",
        "fit_score": 92,
    }


def test_template_uses_sender_and_selected_recipient(monkeypatch):
    monkeypatch.setenv("LEAD_FROM_EMAIL", "sender@example.com")
    draft = build_message(_approved_lead())
    assert draft["from_email"] == "sender@example.com"
    assert draft["to_email"] == "info@northwind.example"
    assert draft["subject"] == "Jade for Northwind Jewellers"
    body = str(draft["body"])
    assert "Hello Northwind Jewellers team," in body
    assert "specialist cover for jewellery" in body
    assert "Wholesale jewellery showrooms across Malaysia." in body
    assert body.endswith("sender@example.com")


def test_draft_requires_human_outreach_approval():
    lead = {**_approved_lead(), "review_status": "pending", "outreach_status": "not_approved"}
    with patch("agents.lead_mail.lead_details", return_value=lead):
        with pytest.raises(LeadMailError, match="must approve"):
            draft_for("lead-1")


def test_send_does_not_claim_or_contact_gmail_without_a_password(monkeypatch):
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    with (
        patch("agents.lead_mail.lead_details", return_value=_approved_lead()),
        patch("agents.lead_mail.get_connection", return_value=_NoSuppressionConnection()),
        patch("agents.lead_mail.claim_outreach_send") as claim,
        patch("agents.lead_mail._deliver") as deliver,
    ):
        with pytest.raises(LeadMailError, match="does not use an API key"):
            send_for("lead-1")
    claim.assert_not_called()
    deliver.assert_not_called()


def test_send_uses_the_selected_lead_and_records_success(monkeypatch):
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "abcd efgh ijkl mnop")
    with (
        patch("agents.lead_mail.lead_details", return_value=_approved_lead()),
        patch("agents.lead_mail.get_connection", return_value=_NoSuppressionConnection()),
        patch("agents.lead_mail.claim_outreach_send", return_value=True) as claim,
        patch("agents.lead_mail._deliver") as deliver,
        patch("agents.lead_mail.mark_outreach_sent") as mark_sent,
    ):
        result = send_for("lead-1")
    claim.assert_called_once_with("lead-1", "info@northwind.example", "northwind.example")
    deliver.assert_called_once()
    assert deliver.call_args.args[0]["to_email"] == "info@northwind.example"
    mark_sent.assert_called_once_with("lead-1")
    assert result["ok"] is True


def test_send_failure_keeps_delivery_locked_as_uncertain(monkeypatch):
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "abcd efgh ijkl mnop")
    with (
        patch("agents.lead_mail.lead_details", return_value=_approved_lead()),
        patch("agents.lead_mail.get_connection", return_value=_NoSuppressionConnection()),
        patch("agents.lead_mail.claim_outreach_send", return_value=True),
        patch("agents.lead_mail._deliver", side_effect=RuntimeError("smtp disconnected")),
        patch("agents.lead_mail.mark_outreach_uncertain") as uncertain,
        patch("agents.lead_mail.mark_outreach_sent") as mark_sent,
    ):
        with pytest.raises(LeadMailError, match="delivery is uncertain"):
            send_for("lead-1")
    uncertain.assert_called_once_with("lead-1")
    mark_sent.assert_not_called()


def test_successful_delivery_with_failed_persistence_is_locked_for_reconciliation(monkeypatch):
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "abcd efgh ijkl mnop")
    with (
        patch("agents.lead_mail.lead_details", return_value=_approved_lead()),
        patch("agents.lead_mail.get_connection", return_value=_NoSuppressionConnection()),
        patch("agents.lead_mail.claim_outreach_send", return_value=True),
        patch("agents.lead_mail._deliver"),
        patch("agents.lead_mail.mark_outreach_sent", side_effect=RuntimeError("database unavailable")),
        patch("agents.lead_mail.mark_outreach_uncertain") as uncertain,
    ):
        with pytest.raises(LeadMailError, match="Gmail accepted"):
            send_for("lead-1")
    uncertain.assert_called_once_with("lead-1")
