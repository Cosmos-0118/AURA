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
except ImportError:
    from lead_intel import load_scraped_leads

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
    draft = draft_for(lead_id)
    if not mail_configured():
        raise LeadMailError(
            "Gmail is not configured. Add GMAIL_APP_PASSWORD to .env. Gmail does not use an API key for sending.",
            503,
        )
    _deliver(draft)
    return {
        "ok": True,
        "from_email": draft["from_email"],
        "to_email": draft["to_email"],
        "subject": draft["subject"],
    }
