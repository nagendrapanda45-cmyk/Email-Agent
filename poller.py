import email
import imaplib
import os
import time
from email.header import decode_header
from email.utils import parseaddr

from dotenv import load_dotenv

load_dotenv()

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL_SECONDS", "30"))


def _decode_str(value: str | bytes | None, charset: str | None = "utf-8") -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode(charset or "utf-8", errors="replace")
    return value


def _decode_header_field(raw: str | None) -> str:
    if not raw:
        return ""
    parts = decode_header(raw)
    result = []
    for fragment, charset in parts:
        result.append(_decode_str(fragment, charset))
    return "".join(result)


def _extract_body(msg: email.message.Message) -> str:
    plain = None
    html = None

    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            cd = part.get("Content-Disposition", "")
            if "attachment" in cd:
                continue
            charset = part.get_content_charset() or "utf-8"
            payload = part.get_payload(decode=True)
            if payload is None:
                continue
            text = payload.decode(charset, errors="replace")
            if ct == "text/plain" and plain is None:
                plain = text
            elif ct == "text/html" and html is None:
                html = text
    else:
        charset = msg.get_content_charset() or "utf-8"
        payload = msg.get_payload(decode=True)
        if payload:
            text = payload.decode(charset, errors="replace")
            if msg.get_content_type() == "text/html":
                html = text
            else:
                plain = text

    if plain:
        return plain.strip()

    # Minimal HTML tag strip when only HTML is available
    if html:
        import re

        return re.sub(r"<[^>]+>", " ", html).strip()

    return ""


def parse_message(raw_bytes: bytes, uid: str) -> dict | None:
    try:
        msg = email.message_from_bytes(raw_bytes)

        from_raw = _decode_header_field(msg.get("From", ""))
        realname, addr = parseaddr(from_raw)
        sender = f"{realname} <{addr}>" if realname else addr

        subject = _decode_header_field(msg.get("Subject", "(no subject)"))
        message_id = _decode_header_field(msg.get("Message-ID")) or f"imap-uid-{uid}"
        body = _extract_body(msg)

        return {
            "from": sender,
            "subject": subject,
            "body": body,
            "message_id": message_id,
        }
    except Exception as e:
        print(f"[poller] Failed to parse message uid={uid}: {e}")
        return None


def fetch_unseen(imap: imaplib.IMAP4_SSL) -> list[tuple[str, dict]]:
    imap.select("INBOX")
    status, data = imap.search(None, "UNSEEN")
    if status != "OK" or not data[0]:
        return []

    uids = data[0].split()
    results = []
    for uid in uids:
        uid_str = uid.decode()
        status, msg_data = imap.fetch(uid, "(RFC822)")
        if status != "OK" or not msg_data:
            print(f"[poller] Could not fetch uid={uid_str}, skipping")
            continue
        raw = msg_data[0][1]
        parsed = parse_message(raw, uid_str)
        if parsed:
            results.append((uid_str, parsed))
    return results


def mark_seen(imap: imaplib.IMAP4_SSL, uid: str):
    imap.store(uid, "+FLAGS", "\\Seen")


def connect() -> imaplib.IMAP4_SSL:
    address = os.environ["GMAIL_ADDRESS"]
    app_password = os.environ["GMAIL_APP_PASSWORD"]
    imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    imap.login(address, app_password)
    return imap


def poll_once():
    from main import print_result, run_email

    try:
        imap = connect()
    except Exception as e:
        print(f"[poller] Connection failed: {e}")
        return

    try:
        messages = fetch_unseen(imap)
        if not messages:
            print("[poller] No new messages.")
            return

        print(f"[poller] Found {len(messages)} unseen message(s).")
        for uid, parsed in messages:
            print(f"\n[poller] Processing uid={uid} subject={parsed['subject']!r}")
            try:
                state = run_email(parsed)
                print_result(state)
                mark_seen(imap, uid)
            except Exception as e:
                print(f"[poller] Error processing uid={uid}: {e}")
    finally:
        try:
            imap.logout()
        except Exception:
            pass


def main():
    address = os.getenv("GMAIL_ADDRESS")
    if not address:
        print("ERROR: GMAIL_ADDRESS not set in .env")
        raise SystemExit(1)
    if not os.getenv("GMAIL_APP_PASSWORD"):
        print("ERROR: GMAIL_APP_PASSWORD not set in .env")
        raise SystemExit(1)
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("ERROR: ANTHROPIC_API_KEY not set in .env")
        raise SystemExit(1)

    print(f"[poller] Watching {address} every {POLL_INTERVAL}s. Ctrl+C to stop.\n")
    while True:
        try:
            poll_once()
        except KeyboardInterrupt:
            print("\n[poller] Stopped.")
            break
        except Exception as e:
            print(f"[poller] Unexpected error: {e}")
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    main()
