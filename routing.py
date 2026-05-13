import re
from datetime import datetime, timezone
from mock_odoo import odoo_client
from json_output import append_contact, append_ticket
from notifier import send_ticket_email


class MockTicketQueue:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tickets = []
            cls._instance._next_id = 1
        return cls._instance

    def create_ticket(self, email: dict, classification: str) -> dict:
        ticket = {
            "id": self._next_id,
            "message_id": email.get("message_id", ""),
            "from": email.get("from", ""),
            "subject": email.get("subject", ""),
            "body": email.get("body", ""),
            "classification": classification,
            "status": "open",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._tickets.append(ticket)
        self._next_id += 1
        return {"success": True, "ticket": ticket}

    def list_tickets(self) -> list:
        return list(self._tickets)

    def reset(self):
        self._tickets = []
        self._next_id = 1


ticket_queue = MockTicketQueue()


def _extract_email_addr(from_field: str) -> str:
    match = re.search(r"<([^>]+)>", from_field)
    if match:
        return match.group(1)
    return from_field.strip()


def _extract_name(from_field: str) -> str:
    match = re.match(r"^(.+?)\s*<", from_field)
    if match:
        return match.group(1).strip()
    addr = _extract_email_addr(from_field)
    local = addr.split("@")[0]
    return local.replace(".", " ").replace("_", " ").title()


def route_support(state: dict) -> dict:
    logs = list(state.get("logs", []))
    errors = list(state.get("errors", []))
    ts = datetime.now(timezone.utc).isoformat()

    try:
        email = state.get("parsed_email") or state.get("raw_email", {})
        result = ticket_queue.create_ticket(email, state.get("classification", "support"))
        ticket = result["ticket"]
        confidence = state.get("confidence", 0.0)
        reasoning = state.get("reasoning", "")
        append_ticket(ticket, confidence, reasoning)
        logs.append(f"[{ts}] route_support: created ticket #{ticket['id']} → tickets.json")
        try:
            send_ticket_email(ticket, confidence, reasoning)
            logs.append(f"[{ts}] route_support: notification email sent for ticket #{ticket['id']}")
        except Exception as e:
            logs.append(f"[{ts}] route_support: email notification failed: {e}")
        return {
            "routing_result": result,
            "logs": logs,
            "errors": errors,
        }
    except Exception as e:
        errors.append(f"[{ts}] route_support error: {e}")
        return {"routing_result": {"success": False, "error": str(e)}, "logs": logs, "errors": errors}

def route_lead(state: dict) -> dict:
    logs = list(state.get("logs", []))
    errors = list(state.get("errors", []))
    ts = datetime.now(timezone.utc).isoformat()

    try:
        email = state.get("parsed_email") or state.get("raw_email", {})
        from_field = email.get("from", "")
        sender_email = _extract_email_addr(from_field)
        sender_name = _extract_name(from_field)
        result = odoo_client.create_contact(sender_email, sender_name, email)
        contact = result["contact"]
        append_contact(contact, state.get("confidence", 0.0), state.get("reasoning", ""))
        logs.append(f"[{ts}] route_lead: created Odoo contact #{contact['id']} → contacts.json")
        return {
            "routing_result": result,
            "logs": logs,
            "errors": errors,
        }
    except Exception as e:
        errors.append(f"[{ts}] route_lead error: {e}")
        return {"routing_result": {"success": False, "error": str(e)}, "logs": logs, "errors": errors}
