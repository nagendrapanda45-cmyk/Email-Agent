import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

_URGENT_KEYWORDS = {
    "urgent",
    "asap",
    "immediately",
    "emergency",
    "critical",
    "deadline",
    "right now",
    "time-sensitive",
    "broken",
    "outage",
    "cannot access",
    "locked out",
    "not working",
    "production issue",
    "escalate",
    "down",
}
_HIGH_KEYWORDS = {
    "important",
    "priority",
    "soon",
    "quickly",
    "end of day",
    "eod",
    "today",
    "pressing",
    "needed",
    "by tomorrow",
}
_LOW_KEYWORDS = {
    "whenever",
    "no rush",
    "when you get a chance",
    "not urgent",
    "eventually",
    "low priority",
    "no hurry",
}


def determine_priority(email: dict) -> str:
    text = (email.get("subject", "") + " " + email.get("body", "")).lower()
    if any(k in text for k in _URGENT_KEYWORDS):
        return "Urgent"
    if any(k in text for k in _HIGH_KEYWORDS):
        return "High"
    if any(k in text for k in _LOW_KEYWORDS):
        return "Low"
    return "Medium"


def _priority_color(priority: str) -> str:
    return {
        "Urgent": "#c0392b",
        "High": "#e67e22",
        "Medium": "#2980b9",
        "Low": "#27ae60",
    }.get(priority, "#555")


def _send(subject: str, html: str, recipient: str):
    gmail_address = os.environ["GMAIL_ADDRESS"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = gmail_address
    msg["To"] = recipient
    msg.attach(MIMEText(html, "html"))
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(gmail_address, app_password)
        smtp.sendmail(gmail_address, recipient, msg.as_string())


def _table_rows(rows: list[tuple]) -> str:
    return "".join(
        f"""<tr>
              <td style="padding:8px 12px;background:#f4f4f4;font-weight:bold;
                         border:1px solid #ddd;white-space:nowrap;">{label}</td>
              <td style="padding:8px 12px;border:1px solid #ddd;">{value}</td>
            </tr>"""
        for label, value in rows
    )


def send_ticket_email(ticket: dict, confidence: float, reasoning: str, priority: str):
    recipient = os.environ.get("TICKET_NOTIFY_EMAIL") or os.environ.get(
        "SUPPORT_NOTIFY_EMAIL", ""
    )
    if not recipient:
        raise ValueError("TICKET_NOTIFY_EMAIL not set")

    color = _priority_color(priority)
    body_preview = ticket.get("body", "")[:500] + (
        "…" if len(ticket.get("body", "")) > 500 else ""
    )

    rows = _table_rows(
        [
            ("Ticket ID", f"#{ticket['id']}"),
            (
                "Priority",
                f'<span style="color:{color};font-weight:bold">{priority}</span>',
            ),
            ("Status", ticket.get("status", "open").upper()),
            ("From", ticket.get("from", "")),
            ("Subject", ticket.get("subject", "")),
            ("Classification", ticket.get("classification", "")),
            ("Confidence", f"{confidence * 100:.0f}%"),
            ("Reasoning", reasoning),
            ("Created At", ticket.get("created_at", "")),
            ("Message ID", ticket.get("message_id", "")),
        ]
    )

    html = f"""<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#222;max-width:700px;margin:auto;padding:24px;">
  <h2 style="color:{color};">New Support Ticket #{ticket["id"]} — {priority}</h2>
  <p style="color:#555;">A new support ticket has been created by the Email Agent.</p>
  <table style="border-collapse:collapse;width:100%;margin-top:16px;">{rows}</table>
  <h3 style="margin-top:28px;border-bottom:1px solid #ddd;padding-bottom:6px;">Email Body</h3>
  <div style="background:#fafafa;border:1px solid #ddd;padding:12px 16px;white-space:pre-wrap;font-size:14px;line-height:1.6;">{body_preview}</div>
  <p style="margin-top:24px;font-size:12px;color:#999;">Sent automatically by the LangGraph Email Agent.</p>
</body></html>"""

    _send(
        f"[{priority}] New Support Ticket #{ticket['id']} — {ticket.get('subject', '')}",
        html,
        recipient,
    )


def send_lead_email(
    contact: dict, confidence: float, reasoning: str, priority: str, source_email: dict
):
    recipient = os.environ.get("LEAD_NOTIFY_EMAIL", "")
    if not recipient:
        raise ValueError("LEAD_NOTIFY_EMAIL not set")

    color = _priority_color(priority)
    body_preview = source_email.get("body", "")[:500] + (
        "…" if len(source_email.get("body", "")) > 500 else ""
    )

    rows = _table_rows(
        [
            ("Contact ID", f"#{contact['id']}"),
            ("Classification", "lead"),
            (
                "Priority",
                f'<span style="color:{color};font-weight:bold">{priority}</span>',
            ),
            ("Name", contact.get("name", "")),
            ("Email", contact.get("email", "")),
            ("Subject", contact.get("original_subject", "")),
            ("Stage", contact.get("stage", "new")),
            ("Confidence", f"{confidence * 100:.0f}%"),
            ("Reasoning", reasoning),
            ("Created At", contact.get("create_date", "")),
            ("Message ID", contact.get("message_id", "")),
        ]
    )

    html = f"""<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#222;max-width:700px;margin:auto;padding:24px;">
  <h2 style="color:{color};">New Sales Lead #{contact["id"]} — {priority}</h2>
  <p style="color:#555;">A new lead has been captured by the Email Agent.</p>
  <table style="border-collapse:collapse;width:100%;margin-top:16px;">{rows}</table>
  <h3 style="margin-top:28px;border-bottom:1px solid #ddd;padding-bottom:6px;">Original Email Body</h3>
  <div style="background:#fafafa;border:1px solid #ddd;padding:12px 16px;white-space:pre-wrap;font-size:14px;line-height:1.6;">{body_preview}</div>
  <p style="margin-top:24px;font-size:12px;color:#999;">Sent automatically by the LangGraph Email Agent.</p>
</body></html>"""

    _send(
        f"[{priority}] New Lead #{contact['id']} — {contact.get('name', '')} <{contact.get('email', '')}>",
        html,
        recipient,
    )


def send_error_email(error_record: dict):
    recipient = os.environ.get("ERROR_NOTIFY_EMAIL", "")
    if not recipient:
        raise ValueError("ERROR_NOTIFY_EMAIL not set")

    confidence = error_record.get("confidence", 0.0)
    error_list = error_record.get("errors", [])

    rows = _table_rows(
        [
            ("From", error_record.get("from", "")),
            ("Subject", error_record.get("subject", "")),
            ("Classification", error_record.get("classification", "unknown")),
            ("Confidence", f"{confidence * 100:.0f}%"),
            ("Reasoning", error_record.get("reasoning", "")),
            ("Failed At", error_record.get("failed_at", "")),
            ("Message ID", error_record.get("message_id", "")),
        ]
    )

    error_block = ""
    if error_list:
        items = "".join(f"<li style='margin-bottom:4px'>{e}</li>" for e in error_list)
        error_block = f"""<h3 style="margin-top:28px;color:#c0392b;">Error Details</h3>
  <ul style="background:#fff5f5;border:1px solid #f5c6cb;padding:12px 16px;border-radius:4px;">{items}</ul>"""

    html = f"""<!DOCTYPE html><html><body style="font-family:Arial,sans-serif;color:#222;max-width:700px;margin:auto;padding:24px;">
  <h2 style="color:#c0392b;">Unclassified Email — Human Review Required</h2>
  <p style="color:#555;">An email could not be confidently classified and requires manual review.</p>
  <table style="border-collapse:collapse;width:100%;margin-top:16px;">{rows}</table>
  {error_block}
  <p style="margin-top:24px;font-size:12px;color:#999;">Sent automatically by the LangGraph Email Agent.</p>
</body></html>"""

    subject = error_record.get("subject", "(no subject)")
    _send(f"[Action Required] Unclassified Email — {subject}", html, recipient)
