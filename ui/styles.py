"""AIPunarartha — the single global stylesheet and theme injector.

One canvas, one vocabulary: monochrome-on-black IBM Plex. Everything on
screen — custom HTML cards, Streamlit widgets, plotly figures — is styled
from this one file, so every page renders identically.
"""
from __future__ import annotations

import streamlit as st

DARK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

:root {
  --bg: #000000;
  --card: #0d0d0d;
  --border: #2a2a2a;
  --muted: #1a1a1a;
  --text: #ffffff;
  --muted-text: #b0b0b0;
  --green: #4ade80;
  --red: #f87171;
  --amber: #fbbf24;
}

html, body, [data-testid="stAppViewContainer"], .stApp {
  background-color: var(--bg) !important;
  color: var(--text) !important;
  font-family: 'IBM Plex Sans', sans-serif !important;
}

[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stToolbar"] { display: none !important; }
#MainMenu, footer, header { visibility: hidden !important; }

.block-container {
  padding-top: 1rem !important;
  padding-bottom: 1rem !important;
  max-width: 1600px !important;
}

h1, h2, h3, h4 { color: var(--text) !important; font-weight: 700 !important; letter-spacing: -0.01em; }
code, .as-score-value, .as-metric-val, .stPlotlyChart text {
  font-family: 'IBM Plex Mono', monospace !important;
}
hr { border-color: var(--border) !important; }

/* --- Sidebar: brand + custom navigation, same canvas --- */
[data-testid="stSidebar"] {
  background: #050505 !important;
  border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] p { color: var(--muted-text); }

[data-testid="stSidebarHeader"] {
  display: flex !important;
  align-items: center !important;
  gap: .55rem !important;
  padding: 1rem .4rem !important;
  margin: 0 !important;
  height: auto !important;
}

/* Kill the native Streamlit page navigation (links/dropdown) completely -
   our own sidebar buttons are the only navigation. */
[data-testid="stSidebarNav"],
[data-testid="stSidebarNavItems"],
[data-testid="stSidebarNavLink"],
[data-testid="stSidebarNavSeparator"],
[data-testid="stSidebarNavViewButton"],
[data-testid="stPageLink"] {
  display: none !important;
}

.as-side-brand {
  display: flex; align-items: center; gap: .55rem;
  margin-top: -2.6rem;
  margin-bottom: .2rem;
  padding: .35rem .3rem;
  border-bottom: none;
}
.as-side-brand .as-logo {
  width: 34px; height: 34px; border-radius: .7rem; flex-shrink: 0;
  background: #fff; color: #000;
  display: flex; align-items: center; justify-content: center;
  font-size: 1rem; font-weight: 700;
}
.as-side-brand .as-brand { font-size: .95rem; font-weight: 700; color: #fff; margin: 0; line-height: 1.2; white-space: nowrap; }
.as-side-brand .as-sub { font-size: .68rem; color: #b0b0b0; margin: .05rem 0 0; white-space: nowrap; }

[data-testid="stSidebar"] .stButton { margin-bottom: .3rem; }
[data-testid="stSidebar"] button[data-testid^="baseButton"] {
  justify-content: flex-start !important;
  padding: .5rem .8rem !important;
}

/* --- Page heading --- */
.as-page-head {
  display: flex; align-items: center; gap: .75rem;
  margin: .5rem 0 1.25rem;
}
.as-page-head h2 { margin: 0; font-size: 1.6rem; }

/* --- Hero (home) --- */
.as-hero { text-align: center; padding: 2rem 1rem 2.25rem; }
.as-hero h2 { font-size: clamp(1.8rem, 3.6vw, 2.9rem); margin: 0 0 .9rem; color: #fff !important; }
.as-hero p {
  font-size: 1.1rem; color: #b0b0b0; max-width: 56rem;
  margin: 0 auto; line-height: 1.65;
}

/* --- Cards --- */
.as-card {
  background: rgba(13,13,13,.85);
  border: 2px solid var(--border);
  border-radius: 1rem;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
}
.as-card-title {
  display: flex; align-items: center; gap: .6rem;
  font-size: 1.35rem; font-weight: 700; margin: 0 0 .35rem; color: #fff;
}
.as-card-desc { color: #b0b0b0; margin: 0 0 1.1rem; font-size: .95rem; }

.as-note { color: #9c9c9c; font-size: .9rem; line-height: 1.6; max-width: 760px; margin: .25rem 0 1rem; }
.as-note strong { color: #fff; }

.as-score-card {
  background: rgba(13,13,13,.6);
  border: 2px solid var(--border);
  border-radius: 1rem;
  padding: 1.15rem 1.25rem;
  height: 100%;
  overflow: hidden;
  min-width: 0;
}
.as-score-card.primary { border-color: #fff; }
.as-score-label { color: #b0b0b0; font-size: .92rem; margin-bottom: .45rem; font-weight: 600; white-space: nowrap; }
.as-score-value { font-size: clamp(1.4rem, 2vw, 2.25rem); font-weight: 700; color: #fff; line-height: 1.1; word-break: break-word; }
.as-score-note { color: #888; font-size: .82rem; margin-top: .5rem; }

.as-badge {
  display: inline-block; padding: 0.2rem 0.65rem;
  border-radius: 999px; font-size: 0.78rem; font-weight: 600;
  border: 1px solid var(--border); background: var(--muted); color: #fff;
  white-space: nowrap;
}
.as-badge.good { background: #14532d; border-color: #22c55e; color: #86efac; }
.as-badge.warn { background: #2a1e06; border-color: #a16207; color: #fde047; }
.as-badge.bad { background: #450a0a; border-color: #b91c1c; color: #fca5a5; }
.as-badge.outline { background: transparent; border-color: #555; color: #ddd; }

.as-muted-box {
  background: rgba(26,26,26,.55);
  border: 1px solid var(--border);
  border-radius: 1rem;
  padding: 1.2rem 1.25rem;
  margin: 0.75rem 0;
}
.as-muted-box h4 { margin-top: 0; color: #fff; }

.as-metric-row {
  display: flex; justify-content: space-between; align-items: center;
  padding: 0.55rem .1rem; border-bottom: 1px solid rgba(42,42,42,.7);
  color: #cfcfcf; font-size: .92rem;
}
.as-metric-row:last-child { border-bottom: none; }
.as-metric-val { font-size: 1.12rem; color: #fff; text-align: right; }
.as-metric-val.good { color: var(--green); }
.as-metric-val.bad { color: var(--red); }
.as-metric-val.warn { color: var(--amber); }

.as-rec {
  display: flex; gap: 0.75rem; align-items: flex-start;
  background: rgba(26,26,26,.55);
  border-left: 4px solid #fff;
  border-radius: 0.75rem;
  padding: 0.85rem 1rem;
  margin-bottom: 0.6rem;
  color: #e5e5e5;
  font-size: .94rem;
}
.as-rec > span:first-child { flex-shrink: 0; line-height: 1.5; }

/* --- Alerts / empty states --- */
.as-alert {
  border-radius: 1rem;
  padding: .85rem 1.1rem;
  margin: .75rem 0;
  font-size: .93rem;
  border: 1px solid var(--border);
}
.as-alert.info { background: rgba(13,13,13,.6); color: #e5e5e5; }
.as-alert.success { background: rgba(20,83,45,.28); border-color: #22c55e; color: #bbf7d0; }
.as-alert.warn { background: rgba(42,30,6,.5); border-color: #a16207; color: #fde68a; }
.as-alert.error { background: rgba(69,10,10,.42); border-color: #b91c1c; color: #fecaca; }

.as-empty {
  display: flex; align-items: flex-start; gap: 1.1rem; text-align: left;
  border: 2px dashed var(--border);
  border-radius: 1rem;
  background: rgba(13,13,13,.45);
  padding: 1.75rem 1.5rem;
  margin: .75rem 0;
}
.as-empty .as-empty-icon { font-size: 1.8rem; line-height: 1.35; flex-shrink: 0; }
.as-empty .as-empty-title { color: #fff; font-weight: 700; font-size: 1.05rem; }
.as-empty .as-empty-body { color: #9c9c9c; margin-top: .4rem; max-width: 520px; line-height: 1.6; }

/* --- Home navigation cards --- */
.as-nav-card {
  display: flex; align-items: flex-start; gap: .9rem;
  padding: .9rem 1.1rem;
  background: rgba(13,13,13,.7);
  border: 1px solid var(--border);
  border-radius: 1rem;
  margin-bottom: .6rem;
  transition: border-color .15s ease, background .15s ease;
}
.as-nav-card:hover { border-color: #666; background: rgba(20,20,20,.9); }
.as-nav-card .as-nav-icon { font-size: 1.35rem; line-height: 1.3; flex-shrink: 0; white-space: nowrap; }
.as-nav-card .as-nav-name { color: #fff; font-weight: 600; font-size: .98rem; white-space: nowrap; }
.as-nav-card .as-nav-desc { color: #9c9c9c; font-size: .84rem; margin-top: .15rem; }

/* --- Primed message block (record detail) --- */
.as-message {
  white-space: pre-wrap; font-family: 'IBM Plex Mono', monospace;
  color: #e5e5e5; background: #0d0d0d; border: 1px solid var(--border);
  border-radius: .6rem; padding: 1rem; margin: .5rem 0 0;
}

/* --- Streamlit buttons --- */
button[data-testid="baseButton-primary"] {
  background: #fff !important; color: #000 !important;
  border: 1px solid #fff !important; border-radius: .5rem !important;
  font-weight: 600 !important;
}
button[data-testid="baseButton-primary"]:hover { opacity: .88 !important; }

button[data-testid="baseButton-secondary"] {
  background: transparent !important; color: #fff !important;
  border: 1px solid #555 !important; border-radius: .5rem !important;
  font-weight: 500 !important;
}
button[data-testid="baseButton-secondary"]:hover { background: #161616 !important; }

button[data-testid="baseButton-tertiary"] {
  background: transparent !important; color: #d4d4d4 !important;
  border: 1px solid transparent !important; border-radius: .5rem !important;
  font-weight: 500 !important;
}
button[data-testid="baseButton-tertiary"]:hover { background: #161616 !important; color: #fff !important; }

/* --- Streamlit widgets --- */
.stSelectbox > div > div {
  background: #111 !important; color: #fff !important;
  border-color: #333 !important; border-radius: .5rem !important;
}
[data-baseweb="select"] { background: #111 !important; border-color: #333 !important; }
[data-baseweb="popover"] [role="option"] { background: #0d0d0d; color: #fff; }
[data-baseweb="popover"] [role="option"]:hover,
[data-baseweb="popover"] [aria-selected="true"] { background: #222; }

[data-testid="stDataFrame"] {
  border: 1px solid var(--border); border-radius: .75rem; overflow: hidden;
}
[data-testid="stDataFrame"] [data-testid="StDataFrameColHeader"] { background: #131313; }
[data-testid="stDataFrame"] [role="row"] { border-color: #222 !important; }
[data-testid="stDataFrame"] [role="row"]:hover { background: rgba(255,255,255,.02) !important; }

[data-testid="stCaptionContainer"] p { color: #9c9c9c !important; }

.js-plotly-plot .plotly { background: transparent !important; }
</style>
"""

def init_theme() -> None:
    """Inject the shared stylesheet on every script run.

    There is no once-per-process guard here on purpose: every page is a fresh
    script run in the same process, and a one-shot flag would make the theme
    vanish as soon as the user navigates off the first page.
    """
    st.markdown(DARK_CSS, unsafe_allow_html=True)