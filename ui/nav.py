"""AIArtha — single source of truth for navigation and the sidebar.

`PAGE_SPECS` defines every view (icon, title, script path, URL slug, and
description) exactly once. `build_pages()` feeds `st.navigation`, `sidebar()`
renders the branded sidebar that `app.py` draws around every page, and
`nav_cards()` renders the same views as cards on the Home page. There is
exactly one navigation definition in the whole app.
"""
from __future__ import annotations

import streamlit as st

from ui.components import html, sidebar_brand

# (icon, title, script path relative to the app root, url_path, description)
PAGE_SPECS = [
    ("🏠", "Home", "ui/Home.py", "home", "The overview you are reading now."),
    ("📊", "Batch Summary", "ui/Batch_Summary.py", "batch-summary",
     "Headline numbers, bucket mix, and a drift scan across the latest batch."),
    ("📋", "Records", "ui/Records.py", "records",
     "Every ingested event with its classification and decision — filterable."),
    ("🔍", "Record Detail", "ui/Record_Detail.py", "record-detail",
     "The full reasoning chain for a single event: classify → decide → act."),
    ("✅", "Review Queue", "ui/Review_Queue.py", "review-queue",
     "Actions waiting for a human when auto-execute is turned off."),
    ("⚠️", "Exceptions", "ui/Exceptions.py", "exceptions",
     "Records that hit a stopping rule and need manual triage."),
]

DEFAULT_PAGE = "ui/Home.py"


def build_pages():
    """Build the `st.Page` list used by `st.navigation` in the entrypoint."""
    return [
        st.Page(script, title=title, icon=_icon, url_path=url, default=(script == DEFAULT_PAGE))
        for _icon, title, script, url, _desc in PAGE_SPECS
    ]


def sidebar() -> None:
    """Branded sidebar: logo + app name up top, one nav button per view."""
    with st.sidebar:
        sidebar_brand()
        for _icon, title, script, _url, _desc in PAGE_SPECS:
            if st.button(f"{_icon} {title}", key=f"nav_{script}", use_container_width=True):
                st.switch_page(script)


def nav_cards() -> None:
    """Render every view (except Home) as a card; used by the Home page."""
    cards = [
        (icon, title, desc)
        for icon, title, _script, _url, desc in PAGE_SPECS
        if title != "Home"
    ]
    html("".join(
        f'<div class="as-nav-card"><div class="as-nav-icon">{icon}</div>'
        f'<div><div class="as-nav-name">{title}</div>'
        f'<div class="as-nav-desc">{desc}</div></div></div>'
        for icon, title, desc in cards
    ))


__all__ = ["PAGE_SPECS", "DEFAULT_PAGE", "build_pages", "sidebar", "nav_cards"]