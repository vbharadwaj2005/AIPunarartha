import pandas as pd
import streamlit as st

from api_client import approve_pending, get_pending
from ui.components import badge, empty_state, info_box, page_header

page_header("Review Queue", badge("Human gate"))

try:
    pending = get_pending()
except Exception as exc:
    info_box(f"Could not reach the API server: {exc}", kind="error")
    st.stop()

if not pending:
    empty_state(
        "✅",
        "Nothing awaiting approval",
        "Auto-execute is on, so decisions run automatically; or every queued "
        "decision has already been resolved.",
    )
else:
    df = pd.DataFrame(pending)

    st.caption("These decisions are waiting for a human because auto-execute is off.")

    st.dataframe(
        df[["decision_id", "event_id", "order_id", "customer_name", "amount", "bucket", "action", "rule_fired"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "decision_id": "Decision",
            "event_id": "Event",
            "order_id": "Order",
            "customer_name": "Customer",
            "amount": st.column_config.NumberColumn("Amount (Rs.)", format="₹ %.0f"),
            "bucket": "Bucket",
            "action": "Action",
            "rule_fired": "Rule",
        },
    )

    col1, col2 = st.columns([1, 3], gap="medium")
    with col1:
        chosen = st.selectbox("Decision to approve", options=df["decision_id"].tolist())
        approve = st.button("Approve and execute", type="primary", use_container_width=True)

    if approve:
        try:
            result = approve_pending(int(chosen))
            ok = result.get("executed", False)
            kind = "success" if ok else ("info" if result.get("already_executed") else "warn")
            detail = "Executed" if ok else ("Already executed" if result.get("already_executed") else "Not executed")
            st.session_state["approve_msg"] = (kind, f"Decision {result['decision_id']}: {detail}")
        except Exception as exc:
            st.session_state["approve_msg"] = ("error", f"Execution failed: {exc}")
        st.rerun()

    if "approve_msg" in st.session_state:
        kind, msg = st.session_state.pop("approve_msg")
        info_box(msg, kind=kind)

    st.caption("Approving a decision sends the recovery action to the provider right away.")