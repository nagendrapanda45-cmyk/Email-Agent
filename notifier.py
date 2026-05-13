import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _build_html(ticket: dict, confidence: float, reasoning: str) -> str:
    rows = [
        ("Ticket ID", f"#{ticket['id']}"),
        ("Status", ticket.get("status", "open").upper()),
        ("From", ticket.get("from", "")),
        ("Subject", ticket.get("subject", "")),
        ("Classification", ticket.get("classification", "")),
        ("Confidence", f"{confidence * 100:.0f}%"),
        ("Reasoning", reasoning),
        ("Created At", ticket.get("created_at", "")),
        ("Message ID", ticket.get("message_id", "")),
    ]

    rows_html = "".join(
        f"""<tr>
              <td style="padding:8px 12px;background:#f4f4f4;font-weight:bold;
                         border:1px solid #ddd;white-space:nowrap;">{label}</td>
              <td style="padding:8px 12px;border:1px solid #ddd;">{value}</td>
            </tr>"""
        for label, value in rows
    )

    body_preview = ticket.get("body", "")[:500]
    if len(ticket.get("body", "")) > 500:
        body_preview += "…"

    return f"""<!DOCTYPE html>
<html>
<body style="font-family:Arial,sans-serif;color:#222;max-width:700px;margin:auto;padding:24px;">
  <h2 style="color:#c0392b;">New Support Ticket #{ticket['id']}</h2>
  <p style="color:#555;">A new support ticket has been created by the Email Agent.</p>

  <table style="border-collapse:collapse;width:100%;margin-top:16px;">
    {rows_html}
  </table>

  <h3 style="margin-top:28px;border-bottom:1px solid #ddd;padding-bottom:6px;">Email Body</h3>
  <div style="background:#fafafa;border:1px solid #ddd;padding:12px 16px;
              white-space:pre-wrap;font-size:14px;line-height:1.6;">
{body_preview}
  </div>

  <p style="margin-top:24px;font-size:12px;color:#999;">
    Sent automatically by the LangGraph Email Agent.
  </p>
</body>
</html>"""


def send_ticket_email(ticket: dict, confidence: float, reasoning: str):
    gmail_address = os.environ["GMAIL_ADDRESS"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]
    recipient = os.environ["SUPPORT_NOTIFY_EMAIL"]

    subject = f"New Support Ticket #{ticket['id']} — {ticket.get('subject', '(no subject)')}"
    html = _build_html(ticket, confidence, reasoning)

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
