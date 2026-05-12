from datetime import datetime, timezone


class MockOdooClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._contacts = []
            cls._instance._next_id = 1
        return cls._instance

    def create_contact(self, email: str, name: str, source_email: dict) -> dict:
        contact = {
            "id": self._next_id,
            "name": name,
            "email": email,
            "create_date": datetime.now(timezone.utc).isoformat(),
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
