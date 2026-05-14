import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

IST = timezone(timedelta(hours=5, minutes=30))


class MockOdooClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._contacts = []
            cls._instance._next_id = cls._next_available_id()
        return cls._instance

    @staticmethod
    def _next_available_id() -> int:
        try:
            filepath = Path(os.getenv("OUTPUT_DIR", ".")) / "contacts.json"
            if filepath.exists():
                data = json.loads(filepath.read_text(encoding="utf-8"))
                if data:
                    return max(c.get("id", 0) for c in data) + 1
        except Exception:
            pass
        return 1

    def create_contact(self, email: str, name: str, source_email: dict) -> dict:
        contact = {
            "id": self._next_id,
            "name": name,
            "email": email,
            "create_date": datetime.now(IST).isoformat(),
            "stage": "new",
            "tags": ["email-lead"],
            "source": "email",
            "message_id": source_email.get("message_id", ""),
            "original_subject": source_email.get("subject", ""),
        }
        self._contacts.append(contact)
        self._next_id += 1
        return {"success": True, "contact": contact}

    def list_contacts(self) -> list:
        return list(self._contacts)

    def get_contact(self, contact_id: int) -> dict | None:
        return next((c for c in self._contacts if c["id"] == contact_id), None)

    def reset(self):
        self._contacts = []
        self._next_id = 1


odoo_client = MockOdooClient()
