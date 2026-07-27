import os
from datetime import datetime, timedelta, timezone
from typing import TypedDict

IST = timezone(timedelta(hours=5, minutes=30))
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph

from email_classifier import ClassificationError, classify_email
from routing import route_lead, route_support
from json_output import append_others
from config import MIN_CONFIDENCE_THRESHOLD

load_dotenv()


class EmailState(TypedDict):
    raw_email: dict
    parsed_email: dict
    classification: str
    confidence: float
    reasoning: str
    routing_result: dict
    errors: list
    logs: list
    token_usage: dict


# ---------------------------------------------------------------------------
# Nodes
# ---------------------------------------------------------------------------

def ingest_email(state: EmailState) -> dict:
    logs = list(state.get("logs", []))
    errors = list(state.get("errors", []))
    ts = datetime.now(IST).isoformat()

    raw = state.get("raw_email", {})
    required_fields = ["from", "subject", "body", "message_id"]
    missing = [f for f in required_fields if not raw.get(f)]
    if missing:
        errors.append(f"[{ts}] ingest_email: missing fields: {missing}")

    parsed = {
        "from": raw.get("from", "").strip(),
        "subject": raw.get("subject", "").strip(),
        "body": raw.get("body", "").strip(),
        "message_id": raw.get("message_id", "").strip(),
    }
    logs.append(f"[{ts}] ingest_email: received message_id={parsed['message_id']} from={parsed['from']!r}")
    return {"parsed_email": parsed, "logs": logs, "errors": errors}


def classify_email_node(state: EmailState) -> dict:
    logs = list(state.get("logs", []))
    errors = list(state.get("errors", []))
    ts = datetime.now(timezone.utc).isoformat()

    if state.get("errors"):
        errors.append(f"[{ts}] classify_email: skipping due to prior errors")
        return {"classification": "other", "confidence": 0.0, "reasoning": "skipped",
                "token_usage": {}, "logs": logs, "errors": errors}

    try:
        email = state.get("parsed_email") or state.get("raw_email", {})
        result = classify_email(email)
        logs.append(
            f"[{ts}] classify_email: classification={result.classification} "
            f"confidence={result.confidence:.2f} "
            f"cost=${result.token_usage.get('cost_usd', 0):.5f}"
        )
        return {
            "classification": result.classification,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "token_usage": result.token_usage,
            "logs": logs,
            "errors": errors,
        }
    except ClassificationError as e:
        errors.append(f"[{ts}] classify_email error: {e}")
        return {
            "classification": "other",
            "confidence": 0.0,
            "reasoning": str(e),
            "token_usage": {},
            "logs": logs,
            "errors": errors,
        }


def handle_others(state: EmailState) -> dict:
    logs = list(state.get("logs", []))
    ts = datetime.now(timezone.utc).isoformat()
    errors = state.get("errors", [])
    email = state.get("parsed_email") or state.get("raw_email", {})
    classification = state.get("classification", "other")
    confidence = state.get("confidence", 0.0)
    reasoning = state.get("reasoning", "")
    token_usage = state.get("token_usage", {})

    try:
        append_others(email, classification, confidence, reasoning, errors, ts, token_usage)
        logs.append(f"[{ts}] handle_others: recorded to others.json (confidence={confidence:.2f})")
    except Exception as e:
        logs.append(f"[{ts}] handle_others: failed to write others.json: {e}")

    return {
        "routing_result": {"success": False, "errors": errors},
        "logs": logs,
    }


# ---------------------------------------------------------------------------
# Conditional edge
# ---------------------------------------------------------------------------

def decide_route(state: EmailState) -> str:
    if state.get("errors"):
        return "handle_others"
    classification = state.get("classification", "other")
    confidence = state.get("confidence", 0.0)
    if confidence < MIN_CONFIDENCE_THRESHOLD or classification == "other":
        return "handle_others"
    if classification == "support":
        return "handle_support"
    if classification == "lead":
        return "handle_lead"
    return "handle_others"


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def build_graph():
    graph = StateGraph(EmailState)

    graph.add_node("ingest_email", ingest_email)
    graph.add_node("classify_email", classify_email_node)
    graph.add_node("handle_support", route_support)
    graph.add_node("handle_lead", route_lead)
    graph.add_node("handle_others", handle_others)

    graph.set_entry_point("ingest_email")
    graph.add_edge("ingest_email", "classify_email")
    graph.add_conditional_edges(
        "classify_email",
        decide_route,
        {
            "handle_support": "handle_support",
            "handle_lead": "handle_lead",
            "handle_others": "handle_others",
        },
    )
    graph.add_edge("handle_support", END)
    graph.add_edge("handle_lead", END)
    graph.add_edge("handle_others", END)

    return graph.compile()


app = build_graph()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run_email(raw_email: dict) -> dict:
    initial_state: EmailState = {
        "raw_email": raw_email,
        "parsed_email": {},
        "classification": "",
        "confidence": 0.0,
        "reasoning": "",
        "routing_result": {},
        "errors": [],
        "logs": [],
        "token_usage": {},
    }
    return app.invoke(initial_state)


def print_result(state: dict):
    sep = "-" * 60
    print(sep)
    email = state.get("raw_email", {})
    print(f"  Message-ID : {email.get('message_id', '')}")
    print(f"  From       : {email.get('from', '')}")
    print(f"  Subject    : {email.get('subject', '')}")
    print(f"  Class      : {state.get('classification', '')}  (confidence: {state.get('confidence', 0):.2f})")
    print(f"  Reasoning  : {state.get('reasoning', '')}")
    usage = state.get("token_usage", {})
    if usage:
        print(f"  Tokens     : in={usage.get('input_tokens',0)} out={usage.get('output_tokens',0)} "
              f"cache_read={usage.get('cache_read_input_tokens',0)} cost=${usage.get('cost_usd',0):.5f}")
    routing = state.get("routing_result", {})
    if routing.get("ticket"):
        print(f"  Ticket #   : {routing['ticket']['id']} — status: {routing['ticket']['status']}")
    elif routing.get("contact"):
        print(f"  Odoo ID    : {routing['contact']['id']} — {routing['contact']['email']}")
    if state.get("errors"):
        print(f"  Errors     : {state['errors']}")
    print(f"  Logs:")
    for line in state.get("logs", []):
        print(f"    {line}")


# ---------------------------------------------------------------------------
# Test emails
# ---------------------------------------------------------------------------

TEST_EMAILS = [
    {
        "from": "Buyer <buyer@example.com>",
        "subject": "Need quotation for 100 MT",
        "body": "Please provide a quotation for 100 metric tons of refined product.",
        "message_id": "msg-001",
    },
    {
        "from": "Wholesale <ws@example.com>",
        "subject": "Looking for wholesale supply",
        "body": "We are a food manufacturer looking for a reliable wholesale supplier. Can we discuss rates?",
        "message_id": "msg-002",
    },
    {
        "from": "Export <ex@example.com>",
        "subject": "Can you export to Dubai?",
        "body": "We are based in the UAE and looking to import your products. Do you export to Dubai?",
        "message_id": "msg-003",
    },
    {
        "from": "Dealer <dlr@example.com>",
        "subject": "Interested in dealership",
        "body": "I have a large distribution network in my state and want to become a dealer for your products.",
        "message_id": "msg-004",
    },
    {
        "from": "Customer A <custA@example.com>",
        "subject": "Shipment delayed",
        "body": "My order #12345 was supposed to arrive yesterday but I haven't received it yet.",
        "message_id": "msg-005",
    },
    {
        "from": "Customer B <custB@example.com>",
        "subject": "Invoice missing",
        "body": "The delivery was received, but the invoice was not attached. Can you email it?",
        "message_id": "msg-006",
    },
    {
        "from": "Customer C <custC@example.com>",
        "subject": "Password reset",
        "body": "I am locked out of my wholesale ordering portal account. Can you help reset my password?",
        "message_id": "msg-007",
    },
    {
        "from": "Applicant <app@example.com>",
        "subject": "Job application",
        "body": "Please find my resume attached for the open position.",
        "message_id": "msg-008",
    },
    {
        "from": "Travel <travel@example.com>",
        "subject": "Hotel booking",
        "body": "Your hotel booking confirmation is ready.",
        "message_id": "msg-009",
    },
    {
        "from": "Sales <sales@printers.com>",
        "subject": "Printer sale",
        "body": "Buy our new office printers at 20% off!",
        "message_id": "msg-010",
    },
]


if __name__ == "__main__":
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
        raise SystemExit(1)

    print("\n=== Email Classification & Routing Agent ===\n")
    results = []
    for email in TEST_EMAILS:
        state = run_email(email)
        print_result(state)
        results.append(state)

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"{'MSG-ID':<10} {'FROM':<35} {'CLASS':<10} {'CONF':<6} {'ROUTED TO'}")
    print("-" * 75)
    for s in results:
        e = s.get("raw_email", {})
        routing = s.get("routing_result", {})
        if routing.get("ticket"):
            routed = f"ticket #{routing['ticket']['id']}"
        elif routing.get("contact"):
            routed = f"odoo #{routing['contact']['id']}"
        else:
            routed = "others handler"
        from_short = e.get("from", "")[:34]
        print(
            f"{e.get('message_id', ''):<10} {from_short:<35} "
            f"{s.get('classification', ''):<10} {s.get('confidence', 0):<6.2f} {routed}"
        )
    print()
