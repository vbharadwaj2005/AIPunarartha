"""AIArtha — dashboard entry point.

Registers the views with `st.navigation` (so `st.switch_page` can reach the
`ui/` scripts), draws the single branded sidebar once, then runs the current
page. The native navigation widget is hidden; the sidebar rendered here is the
only navigation in the app. Config and theme apply once, here.
"""
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ui.styles import init_theme  # noqa: E402
from ui.nav import build_pages, sidebar  # noqa: E402

st.set_page_config(
    page_title="AIArtha — Revenue Recovery",
    page_icon="₹",
    layout="wide",
    initial_sidebar_state="expanded",
)
init_theme()

nav = st.navigation(build_pages(), position="hidden")

sidebar()

nav.run()