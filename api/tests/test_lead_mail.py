"""Lead email uses the configured Gmail sender and the selected lead's address."""

from unittest.mock import patch

import pytest

from agents.lead_mail import LeadMailError, build_message, draft_for, send_for


def test_template_uses_sender_and_selected_recipient(monkeypatch):
    monkeypatch.setenv("LEAD_FROM_EMAIL", "priyan123xyz@gmail.com")
    draft = build_message(
        {
            "brand_id": "jade",
            "name": "Northwind Jewellers",
            "email": "info@northwind.example",
            "requirements": "Wholesale jewellery showrooms across Malaysia.",
        }
    )
    assert draft["from_email"] == "priyan123xyz@gmail.com"
    assert draft["to_email"] == "info@northwind.example"
    assert draft["subject"] == "Jade for Northwind Jewellers"
    body = str(draft["body"])
    assert "Hello Northwind Jewellers team," in body
    assert "specialist cover for jewellery" in body
    assert "Wholesale jewellery showrooms across Malaysia." in body
    assert body.endswith("priyan123xyz@gmail.com")


def test_draft_refuses_a_lead_without_an_email():
    with patch("agents.lead_mail.load_scraped_leads", return_value=[{"id": "lead-1", "brand_id": "jade", "name": "No Mail", "email": None}]):
        with pytest.raises(LeadMailError, match="no published email"):
            draft_for("lead-1")


def test_send_uses_the_selected_lead_and_does_not_call_gmail_without_a_password(monkeypatch):
    monkeypatch.delenv("GMAIL_APP_PASSWORD", raising=False)
    lead = {
        "id": "lead-2",
        "brand_id": "doctorshield",
        "name": "Stay Ageless",
        "email": "info@stayageless.com",
        "requirements": "Medical aesthetics clinic.",
    }
    with patch("agents.lead_mail.load_scraped_leads", return_value=[lead]), patch("agents.lead_mail._deliver") as deliver:
        with pytest.raises(LeadMailError, match="does not use an API key"):
            send_for("lead-2")
    deliver.assert_not_called()


def test_send_delivers_from_the_configured_account(monkeypatch):
    monkeypatch.setenv("GMAIL_APP_PASSWORD", "abcd efgh ijkl mnop")
    lead = {
        "id": "lead-3",
        "brand_id": "jaguar",
        "name": "Loomis",
        "email": "ir@loomis.com",
        "why": "Cash in transit.",
    }
    with patch("agents.lead_mail.load_scraped_leads", return_value=[lead]), patch("agents.lead_mail._deliver") as deliver:
        result = send_for("lead-3")
    deliver.assert_called_once()
    sent = deliver.call_args.args[0]
    assert sent["from_email"] == "priyan123xyz@gmail.com"
    assert sent["to_email"] == "ir@loomis.com"
    assert result["ok"] is True
