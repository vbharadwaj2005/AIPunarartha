import pandas as pd
import streamlit as st

from api_client import get_exceptions
from ui.components import (
    badge, divider, empty_state, info_box, page_header, rec_rows, subheading,
)

page_header("Exceptions", badge("Manual triage"))

try:
    exceptions = get_exceptions()
except Exception as exc:
    info_box(f"Could not reach the API server: {exc}", kind="error")
    st.stop()

if not exceptions:
    empty_state("✅", "No exceptions", "Every record was auto-resolved or stopped cleanly.")
else:
    df = pd.DataFrame(exceptions)

    st.caption("These records hit a stopping rule and were not auto-recovered. Each needs a human.")

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "amount": st.column_config.NumberColumn("Amount (Rs.)", format="₹ %.0f"),
        },
    )

    divider()

    subheading("Why records end up here")
    rec_rows([
        f"{badge('max_retries', 'bad')} &nbsp;Budget exhausted; another attempt would be reckless.",
        f"{badge('cooldown_active', 'warn')} &nbsp;Too soon since the last attempt; the dunning window has not passed.",
        f"{badge('amount_below_threshold', 'outline')} &nbsp;Below the minimum amount worth pursuing automatically.",
        f"{badge('opted_out', 'bad')} &nbsp;The customer has asked not to be contacted for recovery.",
    ])