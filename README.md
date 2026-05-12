# LangGraph Email Classification & Routing Agent

Ingests raw emails, classifies them as **support tickets** or **sales leads** using Claude, and routes them to the appropriate mock backend.

## Architecture

```
ingest_email → classify_email → [conditional] → handle_support → END
                                              → handle_lead    → END
                                              → handle_error   → END
```

| File | Purpose |
|---|---|
| `main.py` | LangGraph workflow, `EmailState`, graph assembly, test runner |
| `email_classifier.py` | Claude API integration (tool use + prompt caching) |
| `routing.py` | LangGraph node functions for support/lead routing |
| `mock_odoo.py` | In-memory mock Odoo CRM client |
| `test_emails.py` | 3 sample emails with pass/fail assertions |

## Prerequisites

- Python 3.11+
- An Anthropic API key

## Setup

```bash
cd EmailAgent
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Create a `.env` file:

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Run

```bash
# Process 3 test emails and print a summary table
python main.py

# Run assertions (exits with code 1 if any test fails)
python test_emails.py
```

## Sample Output

```
=== Email Classification & Routing Agent ===

------------------------------------------------------------
  Message-ID : msg-001
  From       : Sarah Johnson <sarah.johnson@example.com>
  Subject    : Cannot log in to my account - urgent!
  Class      : support  (confidence: 0.98)
  Reasoning  : Existing customer locked out of account with urgent deadline.
  Ticket #   : 1 — status: open
  Logs:
    [2026-...] ingest_email: received message_id=msg-001 ...
    [2026-...] classify_email: classification=support confidence=0.98
    [2026-...] route_support: created ticket #1
...

MSG-ID     FROM                                CLASS      CONF   ROUTED TO
---------------------------------------------------------------------------
msg-001    Sarah Johnson <sarah.johnson@ex...  support    0.98   ticket #1
msg-002    Michael Chen <m.chen@bigcorp.c...  lead       0.97   odoo #1
msg-003    Alex Rivera <alex@startup.io>       support    0.82   ticket #2
```

## Notes

- Classification uses `claude-opus-4-7` via the Anthropic SDK with forced tool use for reliable structured output.
- The system prompt is sent with `cache_control: {"type": "ephemeral"}` to reduce costs on repeated classification calls.
- `MockOdooClient` and `MockTicketQueue` are singletons; state persists in-memory for the duration of a Python process.
- `boto3` is included in `requirements.txt` as a dependency; AWS calls are not made in this implementation.
