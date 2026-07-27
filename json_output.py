import json
import os
import tempfile
from pathlib import Path

OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "."))
TICKETS_FILE = OUTPUT_DIR / "tickets.json"
CONTACTS_FILE = OUTPUT_DIR / "contacts.json"
OTHERS_FILE = OUTPUT_DIR / "others.json"


def _read_existing(filepath: Path) -> list:
    if filepath.exists():
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
    return []


def _atomic_write(filepath: Path, data: list):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    tmp_fd, tmp_path = tempfile.mkstemp(dir=filepath.parent, suffix=".tmp")
    try:
        with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.replace(tmp_path, filepath)
    except Exception:
        os.unlink(tmp_path)
        raise


def append_ticket(
    ticket: dict, confidence: float, reasoning: str, priority: str, token_usage: dict
):
    record = {
        **ticket,
        "confidence": confidence,
        "reasoning": reasoning,
        "priority": priority,
        "token_usage": token_usage,
    }
    records = _read_existing(TICKETS_FILE)
    records.append(record)
    _atomic_write(TICKETS_FILE, records)


def append_contact(
    contact: dict, confidence: float, reasoning: str, priority: str, token_usage: dict
):
    record = {
        **contact,
        "confidence": confidence,
        "reasoning": reasoning,
        "priority": priority,
        "token_usage": token_usage,
    }
    records = _read_existing(CONTACTS_FILE)
    records.append(record)
    _atomic_write(CONTACTS_FILE, records)


def append_others(
    email: dict,
    classification: str,
    confidence: float,
    reasoning: str,
    pipeline_errors: list,
    failed_at: str,
    token_usage: dict,
):
    record = {
        "message_id": email.get("message_id", ""),
        "from": email.get("from", ""),
        "subject": email.get("subject", ""),
        "classification": classification,
        "confidence": confidence,
        "reasoning": reasoning,
        "errors": pipeline_errors,
        "failed_at": failed_at,
        "token_usage": token_usage,
    }
    records = _read_existing(OTHERS_FILE)
    records.append(record)
    _atomic_write(OTHERS_FILE, records)
