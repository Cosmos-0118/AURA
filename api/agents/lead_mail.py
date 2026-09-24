"""Outbound email for one selected lead.

The sender is the Gmail account in LEAD_FROM_EMAIL. Gmail does not accept an
API key for this. Sending uses that account's app password over SMTP.
"""

from __future__ import annotations

import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from dotenv import load_dotenv

try:
    from .lead_intel import load_scraped_leads
    from .lead_pipeline import claim_outreach_send, lead_details, mark_outreach_failed, mark_outreach_sent
    from ..db import get_connection
except ImportError:
    from lead_intel import load_scraped_leads
    from lead_pipeline import claim_outreach_send, lead_details, mark_outreach_failed, mark_outreach_sent
    from db import get_connection

_ROOT_ENV = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ROOT_ENV)
load_dotenv()

DEFAULT_FROM = "priyan123xyz@gmail.com"
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

PITCH: dict[str, tuple[str, str]] = {
    "jade": (
        "Jade",
        "specialist cover for jewellery and watch stock, showroom premises, and transit of high-value pieces",
    ),
    "doctorshield": (
        "DoctorShield",
        "professional indemnity for clinics and practitioners, including defence costs and regulatory inquiries",
    ),
    "jaguar": (
        "Jaguar Transit",
        "operational support for secure cash-in-transit and valuables logistics, including fleet visibility and compliance reporting",
    ),
}


class LeadMailError(Exception):
    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def from_email() -> str:
    value = (os.getenv("LEAD_FROM_EMAIL") or DEFAULT_FROM).strip().strip('"').strip("'")
    return value or DEFAULT_FROM


def app_password() -> str:
    raw = os.getenv("GMAIL_APP_PASSWORD") or ""
    value = raw.replace(" ", "").strip().strip('"').strip("'")
    if not value or value.startswith("your_"):
        return ""
    return value


def mail_configured() -> bool:
    return bool(app_password())


def _find_lead(lead_id: str) -> dict:
    row = lead_details(lead_id)
    if row:
        row["email"] = row.get("email") or row.get("public_email")
        return row
    for row in load_scraped_leads():
        if str(row.get("id")) == lead_id:
            return row
    raise LeadMailError("That lead is no longer in the current list.", 404)


def build_message(lead: dict) -> dict[str, str | bool]:
    brand_id = str(lead.get("brand_id") or "")
    product, spec = PITCH.get(brand_id, ("AURA", "the product selected for this lead"))
    name = str(lead.get("name") or "there").strip() or "there"
    insight = str(lead.get("requirements") or lead.get("why") or "your public website").strip()
    sender = from_email()
    recipient = str(lead.get("email") or "").strip()
    subject = f"{product} for {name}"
    body = "\n".join(
        [
            f"Hello {name} team,",
            "",
            f"We are writing from {product}. We provide {spec}.",
            "",
            "From your public website, this stood out to us:",
            insight,
            "",
            "Would you be open to a short conversation about whether this fits your requirements, and whether you would like to review a proposal to buy from us?",
            "",
            "Thank you,",
            product,
            sender,
        ]
    )
    return {
        "from_email": sender,
        "to_email": recipient,
        "subject": subject,
        "body": body,
        "configured": mail_configured(),
    }


def draft_for(lead_id: str) -> dict[str, str | bool]:
    draft = build_message(_find_lead(lead_id))
    if not draft["to_email"]:
        raise LeadMailError("This lead has no published email address.")
    return draft


def _deliver(draft: dict[str, str | bool]) -> None:
    message = EmailMessage()
    message["From"] = str(draft["from_email"])
    message["To"] = str(draft["to_email"])
    message["Subject"] = str(draft["subject"])
    message.set_content(str(draft["body"]))
    password = app_password()
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(str(draft["from_email"]), password)
            smtp.send_message(message)
    except smtplib.SMTPAuthenticationError as exc:
        raise LeadMailError(
            "Gmail rejected the app password. Create one for the sender account and set GMAIL_APP_PASSWORD.",
            502,
        ) from exc
    except OSError as exc:
        raise LeadMailError("Gmail could not be reached.", 502) from exc
    except smtplib.SMTPException as exc:
        raise LeadMailError("Gmail did not accept this email.", 502) from exc


def send_for(lead_id: str) -> dict[str, str | bool]:
    lead = _find_lead(lead_id)
    if lead.get("review_status") != "approved" or lead.get("outreach_status") != "approved":
        raise LeadMailError("A human reviewer must approve this lead for outreach before sending.", 409)
    email = str(lead.get("email") or lead.get("public_email") or "").strip().lower()
    domain = str(lead.get("domain") or "").strip().lower()
    try:
        with get_connection() as connection:
            suppressed = connection.execute(
                "SELECT id FROM lead_suppressions WHERE brand_id=%s AND ((domain=%s AND domain IS NOT NULL) OR (email=%s AND email IS NOT NULL)) LIMIT 1",
                (lead.get("brand_id"), domain or None, email or None),
            ).fetchone()
    except Exception as exc:
        raise LeadMailError("Could not verify the outreach suppression list.", 503) from exc
    if suppressed:
        raise LeadMailError("This business is on the outreach suppression list.", 409)
    draft = build_message(lead)
    if not draft["to_email"]:
        raise LeadMailError("This lead has no published email address.")
    if not mail_configured():
        raise LeadMailError(
            "Gmail is not configured. Add GMAIL_APP_PASSWORD to .env. Gmail does not use an API key for sending.",
            503,
        )
    if not claim_outreach_send(lead_id):
        raise LeadMailError("This outreach was already sent or another send is in progress.", 409)
    try:
        _deliver(draft)
    except Exception as exc:
        mark_outreach_failed(lead_id)
        if isinstance(exc, LeadMailError):
            raise
        raise LeadMailError("The email could not be sent. Review the lead before trying again.", 502) from exc
    mark_outreach_sent(lead_id)
    return {
        "ok": True,
        "from_email": draft["from_email"],
        "to_email": draft["to_email"],
        "subject": draft["subject"],
    }
