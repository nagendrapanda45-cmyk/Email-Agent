# LangGraph Email Classification & Routing Agent

Watches a Gmail inbox in real time, classifies each incoming email as a **support ticket** or **sales lead** using Claude, routes it to the appropriate backend, and persists all results to JSON files on disk.

---

## How It Works

```
Gmail Inbox (IMAP)
       │
       ▼
  poller.py  — fetches unseen emails every 30s, marks them read
       │
       ▼
  ingest_email  — validates and normalises the raw email
       │
       ▼
  classify_email  — Claude (claude-opus-4-7) via tool use + prompt caching
       │
       ▼ confidence ≥ 0.5?
  ┌────┴──────────────┐──────────────────┐
  ▼                   ▼                  ▼
support              lead             unknown / error
  │                   │                  │
  ▼                   ▼                  ▼
tickets.json     contacts.json      errors.json
```

---

## Files

| File | Purpose |
|---|---|
| `poller.py` | Gmail IMAP polling loop — fetches unseen emails and feeds them to the graph |
| `config.py` | Business context configuration (Company Name, Products, Routing Thresholds) |
| `main.py` | LangGraph workflow: `EmailState`, all nodes, conditional routing, graph assembly |
| `email_classifier.py` | Claude API integration — dynamically generates intent-based prompts |
| `routing.py` | LangGraph node functions for support and lead routing |
| `mock_odoo.py` | In-memory mock Odoo CRM client (singleton) |
| `json_output.py` | Atomic JSON file writer — appends records to `tickets.json`, `contacts.json`, `errors.json` |
| `test_emails.py` | 10 sample emails with pass/fail assertions (no live inbox required) |

---

## Prerequisites

- Python 3.11+
- An Anthropic API key
- A Gmail account with IMAP enabled and an App Password

---

## Setup

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
GMAIL_ADDRESS=yourname@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
POLL_INTERVAL_SECONDS=30
OUTPUT_DIR=.
```

### Gmail App Password

1. Go to your Google Account → **Security**
2. Enable **2-Step Verification** (required)
3. Search for **App Passwords** → create one for Mail
4. Paste the 16-character password into `.env`

### Enable Gmail IMAP

Gmail → **Settings** → **See all settings** → **Forwarding and POP/IMAP** → enable IMAP → Save.

---

## Running

**Watch a live inbox:**
```bash
python poller.py
```

The poller checks for unread emails every 30 seconds (configurable via `POLL_INTERVAL_SECONDS`), runs each one through the agent, and marks it as read. Press `Ctrl+C` to stop.

**Run the built-in test emails (no inbox needed):**
```bash
python main.py        # processes 3 sample emails, prints summary table
python test_emails.py # same emails with pass/fail assertions
```

**Keep the poller running after disconnecting (AWS):**
```bash
screen -S emailagent
python poller.py
# Ctrl+A then D to detach
```

---

## Output Files

All output is written to the directory set by `OUTPUT_DIR` (default: project root).

### `tickets.json` — support tickets

```json
[
  {
    "id": 1,
    "message_id": "<abc@mail.gmail.com>",
    "from": "Customer C <c@example.com>",
    "subject": "Need password reset",
    "body": "Hi, I cannot access my wholesale portal account. Please help me reset my password.",
    "classification": "support",
    "status": "open",
    "created_at": "2026-05-11T10:32:00+00:00",
    "confidence": 0.97,
    "reasoning": "Existing customer needing help with account access."
  }
]
```

### `contacts.json` — sales leads (Odoo-style)

```json
[
  {
    "id": 1,
    "name": "Customer A",
    "email": "a@example.com",
    "stage": "new",
    "tags": ["email-lead"],
    "original_subject": "Need Sugar pricing",
    "created_at": "2026-05-11T10:33:00+00:00",
    "confidence": 0.99,
    "reasoning": "Clear inquiry about purchasing and pricing for Sugar."
  }
]
```

### `errors.json` — unclassified or failed emails

```json
[
  {
    "message_id": "<xyz@mail.gmail.com>",
    "from": "someone@example.com",
    "subject": "Re: Re: Re:",
    "classification": "unknown",
    "confidence": 0.31,
    "reasoning": "Reply chain with no clear intent.",
    "errors": [],
    "failed_at": "2026-05-11T10:45:00+00:00"
  }
]
```

Every email the agent processes ends up in exactly one of these three files. All writes are atomic — a crash mid-write will never corrupt a file.

---

## Classification Logic

Claude is called with a prompt dynamically generated from `config.py`, instructing it to infer the primary intent of the email based on the business domain. The model returns plain text parsed by regex into a structured output.

| Outcome | Condition |
|---|---|
| → `tickets.json` | `classification == "support"` and `confidence ≥ MIN_CONFIDENCE_THRESHOLD` |
| → `contacts.json` | `classification == "lead"` and `confidence ≥ MIN_CONFIDENCE_THRESHOLD` |
| → `errors.json` | `confidence < MIN_CONFIDENCE_THRESHOLD`, `classification == "other"`, or any API/parse error |

---

## Notes

- `MockOdooClient` and `MockTicketQueue` are singletons — state persists in memory for the lifetime of the process. To connect a real Odoo or ticketing system, replace the method bodies in `routing.py`.
- `boto3` is included in `requirements.txt` as a dependency; no AWS calls are made in the current implementation.
- The model used is `claude-opus-4-7`. To switch models, change the `model` parameter in `email_classifier.py`.
