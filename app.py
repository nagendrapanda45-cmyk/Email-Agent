import json
import os
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv, set_key

load_dotenv()

st.set_page_config(page_title="Email Agent Dashboard", layout="wide")
st.title("Email Agent Dashboard")

ENV_PATH = Path(".env")
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "."))


# ---------------------------------------------------------------------------
# Sidebar — recipient settings
# ---------------------------------------------------------------------------

with st.sidebar:
    st.header("Notification Recipients")
    st.caption("Enter the email address that should receive each notification type.")

    ticket_email = st.text_input(
        "Ticket notifications",
        value=os.getenv("TICKET_NOTIFY_EMAIL", os.getenv("SUPPORT_NOTIFY_EMAIL", "")),
        placeholder="support-team@yourcompany.com",
    )
    lead_email = st.text_input(
        "Lead notifications",
        value=os.getenv("LEAD_NOTIFY_EMAIL", ""),
        placeholder="sales-team@yourcompany.com",
    )
    error_email = st.text_input(
        "Error notifications",
        value=os.getenv("ERROR_NOTIFY_EMAIL", ""),
        placeholder="ops-team@yourcompany.com",
    )

    if st.button("Save Settings", type="primary", use_container_width=True):
        ENV_PATH.touch(exist_ok=True)
        set_key(str(ENV_PATH), "TICKET_NOTIFY_EMAIL", ticket_email)
        set_key(str(ENV_PATH), "LEAD_NOTIFY_EMAIL", lead_email)
        set_key(str(ENV_PATH), "ERROR_NOTIFY_EMAIL", error_email)
        load_dotenv(override=True)
        st.success("Saved to .env — restart poller.py to apply.")

    st.divider()
    if st.button("Refresh Data", use_container_width=True):
        st.rerun()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_json(filepath: Path) -> list:
    if filepath.exists():
        try:
            return json.loads(filepath.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


tickets = load_json(OUTPUT_DIR / "tickets.json")
contacts = load_json(OUTPUT_DIR / "contacts.json")
errors = load_json(OUTPUT_DIR / "errors.json")
all_records = tickets + contacts + errors


# ---------------------------------------------------------------------------
# Cost helpers
# ---------------------------------------------------------------------------

def record_cost(r: dict) -> float:
    return r.get("token_usage", {}).get("cost_usd", 0.0)


def record_input_tokens(r: dict) -> int:
    return r.get("token_usage", {}).get("input_tokens", 0)


def record_output_tokens(r: dict) -> int:
    return r.get("token_usage", {}).get("output_tokens", 0)


total_cost = sum(record_cost(r) for r in all_records)
total_input = sum(record_input_tokens(r) for r in all_records)
total_output = sum(record_output_tokens(r) for r in all_records)


# ---------------------------------------------------------------------------
# Metrics row
# ---------------------------------------------------------------------------

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Tickets", len(tickets))
c2.metric("Leads", len(contacts))
c3.metric("Errors", len(errors))
c4.metric("Input Tokens", f"{total_input:,}")
c5.metric("Output Tokens", f"{total_output:,}")
c6.metric("Total Cost", f"${total_cost:.4f}")

st.divider()


# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

def priority_badge(priority: str) -> str:
    colors = {"Urgent": "🔴", "High": "🟠", "Medium": "🔵", "Low": "🟢"}
    return f"{colors.get(priority, '⚪')} {priority}"


def usage_summary(r: dict) -> str:
    u = r.get("token_usage", {})
    if not u:
        return "—"
    cr = u.get("cache_read_input_tokens", 0)
    return (f"in={u.get('input_tokens',0):,}  out={u.get('output_tokens',0):,}  "
            f"cache_read={cr:,}  cost=${u.get('cost_usd',0):.5f}")


tab1, tab2, tab3 = st.tabs(["🎫  Tickets", "👤  Leads", "⚠️  Errors"])

with tab1:
    if not tickets:
        st.info("No tickets yet. Send a support email to the watched inbox to get started.")
    else:
        for r in reversed(tickets):
            priority = r.get("priority", "Medium")
            label = f"#{r['id']} — {r.get('subject','')[:60]}  |  {priority_badge(priority)}  |  {r.get('created_at','')[:19]}"
            with st.expander(label):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"**From:** {r.get('from','')}")
                    st.markdown(f"**Priority:** {priority_badge(priority)}")
                    st.markdown(f"**Status:** {r.get('status','open').upper()}")
                    st.markdown(f"**Confidence:** {r.get('confidence',0):.0%}")
                    st.markdown(f"**Reasoning:** {r.get('reasoning','')}")
                    st.text_area("Body", r.get("body", ""), height=120,
                                 disabled=True, key=f"t_{r['id']}_body")
                with col2:
                    st.markdown("**Token Usage**")
                    u = r.get("token_usage", {})
                    if u:
                        st.metric("Input tokens", f"{u.get('input_tokens',0):,}")
                        st.metric("Output tokens", f"{u.get('output_tokens',0):,}")
                        st.metric("Cache read", f"{u.get('cache_read_input_tokens',0):,}")
                        st.metric("Cost (USD)", f"${u.get('cost_usd',0):.5f}")
                    else:
                        st.write("Not available")

with tab2:
    if not contacts:
        st.info("No leads yet. Send a sales inquiry to the watched inbox to get started.")
    else:
        for r in reversed(contacts):
            priority = r.get("priority", "Medium")
            label = f"#{r['id']} — {r.get('name','')} <{r.get('email','')}>  |  {priority_badge(priority)}  |  {r.get('create_date','')[:19]}"
            with st.expander(label):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"**Name:** {r.get('name','')}")
                    st.markdown(f"**Email:** {r.get('email','')}")
                    st.markdown(f"**Subject:** {r.get('original_subject','')}")
                    st.markdown(f"**Priority:** {priority_badge(priority)}")
                    st.markdown(f"**Stage:** {r.get('stage','new')}")
                    st.markdown(f"**Confidence:** {r.get('confidence',0):.0%}")
                    st.markdown(f"**Reasoning:** {r.get('reasoning','')}")
                with col2:
                    st.markdown("**Token Usage**")
                    u = r.get("token_usage", {})
                    if u:
                        st.metric("Input tokens", f"{u.get('input_tokens',0):,}")
                        st.metric("Output tokens", f"{u.get('output_tokens',0):,}")
                        st.metric("Cache read", f"{u.get('cache_read_input_tokens',0):,}")
                        st.metric("Cost (USD)", f"${u.get('cost_usd',0):.5f}")
                    else:
                        st.write("Not available")

with tab3:
    if not errors:
        st.info("No errors yet.")
    else:
        for i, r in enumerate(reversed(errors)):
            label = f"Error — {r.get('subject','')[:60]}  |  conf={r.get('confidence',0):.0%}  |  {r.get('failed_at','')[:19]}"
            with st.expander(label):
                col1, col2 = st.columns([2, 1])
                with col1:
                    st.markdown(f"**From:** {r.get('from','')}")
                    st.markdown(f"**Subject:** {r.get('subject','')}")
                    st.markdown(f"**Classification attempted:** {r.get('classification','unknown')}")
                    st.markdown(f"**Confidence:** {r.get('confidence',0):.0%}")
                    st.markdown(f"**Reasoning:** {r.get('reasoning','')}")
                    if r.get("errors"):
                        for err in r["errors"]:
                            st.error(err)
                with col2:
                    st.markdown("**Token Usage**")
                    u = r.get("token_usage", {})
                    if u:
                        st.metric("Input tokens", f"{u.get('input_tokens',0):,}")
                        st.metric("Output tokens", f"{u.get('output_tokens',0):,}")
                        st.metric("Cache read", f"{u.get('cache_read_input_tokens',0):,}")
                        st.metric("Cost (USD)", f"${u.get('cost_usd',0):.5f}")
                    else:
                        st.write("Not available")


# ---------------------------------------------------------------------------
# Token usage breakdown table
# ---------------------------------------------------------------------------

st.divider()
st.subheader("Token Usage & Cost — All Records")

if all_records:
    def ts_key(r: dict) -> str:
        return r.get("created_at") or r.get("create_date") or r.get("failed_at") or ""

    sorted_records = sorted(all_records, key=ts_key, reverse=True)

    rows = []
    for r in sorted_records[:50]:
        u = r.get("token_usage", {})
        record_type = ("ticket" if "status" in r
                       else "lead" if "email" in r and "stage" in r
                       else "error")
        rows.append({
            "Type": record_type,
            "Subject / Name": (r.get("subject") or r.get("original_subject") or r.get("name") or "")[:50],
            "From": r.get("from", r.get("email", ""))[:35],
            "Priority": r.get("priority", "—"),
            "Confidence": f"{r.get('confidence', 0):.0%}",
            "Input Tokens": u.get("input_tokens", 0),
            "Output Tokens": u.get("output_tokens", 0),
            "Cache Read": u.get("cache_read_input_tokens", 0),
            "Cost (USD)": round(u.get("cost_usd", 0.0), 6),
        })

    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    total_row = pd.DataFrame([{
        "Type": "TOTAL",
        "Subject / Name": "",
        "From": "",
        "Priority": "",
        "Confidence": "",
        "Input Tokens": df["Input Tokens"].sum(),
        "Output Tokens": df["Output Tokens"].sum(),
        "Cache Read": df["Cache Read"].sum(),
        "Cost (USD)": round(df["Cost (USD)"].sum(), 6),
    }])
    st.dataframe(total_row, use_container_width=True, hide_index=True)
else:
    st.info("No records yet.")
