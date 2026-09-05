import pandas as pd
import streamlit as st

from api_client import get_records
from ui.components import badge, empty_state, info_box, page_header

page_header("All Records", badge("Filterable"))

try:
    records = get_records(limit=500)
except Exception as exc:
    info_box(f"Could not reach the API server: {exc}", kind="error")
    st.stop()

if not records:
    empty_state("📭", "No records yet", "Generate a synthetic batch first, then run the pipeline.")
    st.stop()

df = pd.DataFrame(records)

f1, f2, f3 = st.columns(3)
with f1:
    bucket = st.selectbox(
        "Bucket",
        ["All"] + sorted(b for b in df["classification_bucket"].dropna().unique()),
    )
with f2:
    action = st.selectbox(
        "Decision",
        ["All"] + sorted(a for a in df["decision_action"].dropna().unique()),
    )
with f3:
    status = st.selectbox(
        "Status",
        ["All"] + sorted(s for s in df["status"].dropna().unique()),
    )

if bucket != "All":
    df = df[df["classification_bucket"] == bucket]
if action != "All":
    df = df[df["decision_action"] == action]
if status != "All":
    df = df[df["status"] == status]

columns = [
    "id", "customer_name", "amount", "status",
    "classification_bucket", "classification_method",
    "decision_action", "action_outcome",
]
st.dataframe(
    df[columns],
    use_container_width=True,
    hide_index=True,
    column_config={
        "id": st.column_config.NumberColumn("ID"),
        "customer_name": "Customer",
        "amount": st.column_config.NumberColumn("Amount (Rs.)", format="₹ %.0f"),
        "status": "Status",
        "classification_bucket": "Bucket",
        "classification_method": "Method",
        "decision_action": "Action",
        "action_outcome": "Outcome",
    },
)

st.caption(
    "Phone numbers and email addresses are masked in this view. "
    "Open Record Detail for the full reasoning chain."
)