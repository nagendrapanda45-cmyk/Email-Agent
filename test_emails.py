import os
import sys

from dotenv import load_dotenv

load_dotenv()

if not os.getenv("ANTHROPIC_API_KEY"):
    print("ERROR: ANTHROPIC_API_KEY environment variable not set.")
    sys.exit(1)

from config import MIN_CONFIDENCE_THRESHOLD
from main import run_email
from mock_odoo import odoo_client
from routing import ticket_queue
from test_data import EXPECTED_CLASSIFICATIONS, TEST_EMAILS


def run_tests():
    ticket_queue.reset()
    odoo_client.reset()

    passed = 0
    failed = 0

    for i, (email, expected) in enumerate(
        zip(TEST_EMAILS, EXPECTED_CLASSIFICATIONS), start=1
    ):
        print(f"\n--- Test {i}: {email['subject']} ---")
        state = run_email(email)

        classification = state.get("classification", "")
        confidence = state.get("confidence", 0.0)
        errors = state.get("errors", [])

        print(f"  classification : {classification}")
        print(f"  confidence     : {confidence:.2f}")
        print(f"  reasoning      : {state.get('reasoning', '')}")
        print(f"  errors         : {errors}")

        ok = True

        if expected == "failed":
            if classification != "failed":
                print(f"  FAIL - expected 'failed', got {classification!r}")
                ok = False
        else:
            if errors:
                print(f"  FAIL - unexpected errors: {errors}")
                ok = False

            if expected is not None and classification != expected:
                print(f"  FAIL - expected {expected!r}, got {classification!r}")
                ok = False
            elif expected is None and classification not in ("support", "lead", "other", "failed"):
                print(f"  FAIL - invalid classification value: {classification!r}")
                ok = False

            if confidence < MIN_CONFIDENCE_THRESHOLD and expected != "other":
                print(f"  FAIL - confidence too low: {confidence:.2f}")
                ok = False

        if ok:
            print("  PASS")
            passed += 1
        else:
            failed += 1

    print(f"\n{'=' * 40}")
    print(f"Results: {passed} passed, {failed} failed out of {len(TEST_EMAILS)} tests")
    print(f"{'=' * 40}\n")

    print("Support Ticket Queue:")
    for t in ticket_queue.list_tickets():
        print(f"  #{t['id']} | {t['subject']} | status={t['status']}")

    print("\nOdoo Contacts:")
    for c in odoo_client.list_contacts():
        print(f"  #{c['id']} | {c['name']} <{c['email']}> | stage={c['stage']}")

    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
