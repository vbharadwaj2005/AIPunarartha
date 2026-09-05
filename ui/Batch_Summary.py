import pandas as pd
import plotly.express as px
import streamlit as st

from api_client import get_batch_summary, get_drift
from ui.components import (
    GREYS, badge, base_layout, divider, info_box, page_header,
    score_card, subheading, subnote,
)

page_header("Batch Summary", badge("Live"))

try:
    summary = get_batch_summary()
except Exception as exc:
    info_box(f"Could not reach the API server: {exc}", kind="error")
    st.stop()

col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    score_card("Events", f"{summary['total_events']}", note="in batch")
with col2:
    score_card("Amount at risk", f"₹{summary['total_at_risk']:,.0f}")
with col3:
    score_card("Recovered", f"₹{summary['total_recovered']:,.0f}", primary=True)
with col4:
    score_card("Recovery rate", f"{summary['recovery_rate_pct']}%", note="simulated")
with col5:
    exc = summary["exception_count"]
    tone_note = "needs triage" if exc else "none"
    score_card("Exceptions", f"{exc}", note=tone_note)

st.caption("Recovered amounts are simulated probabilities, not live settlements.")

divider()

left, right = st.columns(2, gap="medium")

with left:
    subheading("Recovery actions taken")
    action_counts = pd.DataFrame(list(summary["by_action"].items()), columns=["action", "count"])
    fig = px.bar(action_counts, x="action", y="count", color_discrete_sequence=["#ffffff"])
    fig.update_layout(**base_layout(showlegend=False, xaxis_title="", yaxis_title="count"))
    fig.update_traces(marker_line_width=0, textfont=dict(color="#b0b0b0"))
    st.plotly_chart(fig, use_container_width=True)

with right:
    subheading("Failures by bucket")
    bucket_counts = pd.DataFrame(list(summary["by_bucket"].items()), columns=["bucket", "count"])
    fig2 = px.pie(bucket_counts, names="bucket", values="count", hole=0.55,
                  color_discrete_sequence=GREYS)
    fig2.update_layout(**base_layout())
    fig2.update_traces(marker_line_width=0, textinfo="none")
    st.plotly_chart(fig2, use_container_width=True)

divider()

ratio = summary["rule_vs_llm_ratio"]
subnote(
    f"<strong>{ratio['rule']}</strong> events classified by rules, "
    f"<strong>{ratio['llm']}</strong> by the AI model."
)

try:
    drift = get_drift()
    subheading("Drift scan")
    if not drift["sufficient_data"]:
        info_box("Not enough history to compare recent events against the baseline yet.")
    else:
        shares = pd.DataFrame(
            list(drift["bucket_shifts"].items()), columns=["bucket", "shift_pp"]
        ).sort_values("shift_pp", key=abs, ascending=False)

        if drift["flag_raised"]:
            info_box(
                f"At least one bucket has moved by {drift['threshold_pct']:.0f} "
                "percentage points or more vs the historical baseline.",
                kind="warn",
            )
        else:
            info_box("No material shift in the failure mix vs baseline.", kind="success")

        chart = px.bar(
            shares.head(6), x="bucket", y="shift_pp",
            color="shift_pp", color_continuous_scale=["#f87171", "#ffffff", "#4ade80"],
        )
        chart.update_layout(**base_layout(showlegend=False))
        chart.update_coloraxes(showscale=False)
        chart.update_traces(marker_line_width=0)
        st.plotly_chart(chart, use_container_width=True)

        subnote(
            f"Recent recovery rate: <strong>{drift['recent_recovery_rate_pct'] or 'n/a'}%</strong> vs "
            f"baseline <strong>{drift['baseline_recovery_rate_pct'] or 'n/a'}%</strong> (simulated)."
        )
except Exception:
    st.caption("Drift scan unavailable.")