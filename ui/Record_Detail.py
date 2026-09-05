import streamlit as st

from api_client import get_record, get_records
from ui.components import (
    badge, card_close, card_open, chain_card, divider, empty_state, html,
    info_box, page_header, score_card,
)

page_header("Record Detail", badge("Full chain"))

try:
    records = get_records(limit=500)
except Exception as exc:
    info_box(f"Could not reach the API server: {exc}", kind="error")
    st.stop()

if not records:
    empty_state("📭", "No records yet", "Generate a synthetic batch first, then run the pipeline.")
    st.stop()

labels = {
    r["id"]: f"{r['id']} — {r['customer_name']} (Rs. {r['amount']:,.0f})"
    for r in records
}
chosen = st.selectbox("Pick a record", options=list(labels.keys()), format_func=lambda i: labels[i])

record = get_record(chosen)

col1, col2, col3, col4 = st.columns(4)
with col1:
    score_card("Customer", record["customer_name"])
with col2:
    score_card("Amount", f"₹{record['amount']:,.0f}")
with col3:
    score_card("Status", record["status"])
with col4:
    score_card("Opted out", "Yes" if record["customer_opted_out"] else "No",
               primary=record["customer_opted_out"])

divider()

chain_card("1 · Failure (raw event)", [
    ("Reason code", record["failure_reason_code"] or "—"),
    ("Reason text", record["failure_reason_text"] or "—"),
    ("Order", record["order_id"]),
    ("Contact", f"{record['customer_phone'] or '—'} / {record['customer_email'] or '—'}"),
])

class_method = record["classification_method"] or "—"
chain_card(
    "2 · Classification",
    [
        ("Confidence", f"{record['classification_confidence']}"),
        ("Reasoning", record["classification_reasoning"] or "—"),
    ],
    badges=[(record["classification_bucket"],), ("rule" if class_method == "rule" else "llm",)],
)

action = record["decision_action"]
action_tone = "good" if action == "no_action" else ("warn" if action == "reminder" else None)
chain_card("3 · Decision", [
    ("Action", action, action_tone),
    ("Rule fired", record["decision_rule_fired"] or "—"),
    ("Stopping rule", record["decision_stopping_rule"] or "none",
     "warn" if record["decision_stopping_rule"] else None),
])

outcome = record["action_outcome"] or "—"
outcome_tone = "good" if outcome == "recovered" else ("bad" if outcome == "failed" else None)
chain_card("4 · Action executed", [
    ("Channel", record["action_channel"] or "—"),
    ("Language", record["action_language"] or "—"),
    ("Payment link", record["action_payment_link"] or "—"),
    ("Outcome", outcome, outcome_tone),
])

if record.get("action_message"):
    card_open("Message drafted")
    html(f'<div class="as-message">{record["action_message"]}</div>')
    card_close()