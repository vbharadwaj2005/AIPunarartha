"""AIArtha — shared UI builders used by every view.

Everything renders from the `as-*` classes defined in `ui/styles.py`, so the
whole dashboard is one design language. Only helpers that are actually used
live here.
"""
from __future__ import annotations

import streamlit as st

GREYS = ["#ffffff", "#d4d4d4", "#a8a8a8", "#7c7c7c", "#505050", "#333333"]


def html(markup: str) -> None:
    st.markdown(markup, unsafe_allow_html=True)


def sidebar_brand(title: str = "AIArtha", subtitle: str = "Revenue recovery",
                  glyph: str = "\u20b9") -> None:
    """Logo tile + app name pinned to the top of the sidebar on every page."""
    html(
        f"""
        <div class="as-side-brand">
          <div class="as-logo">{glyph}</div>
          <div>
            <p class="as-brand">{title}</p>
            <p class="as-sub">{subtitle}</p>
          </div>
        </div>
        """
    )


def hero(headline: str, body: str) -> None:
    html(f'<div class="as-hero"><h2>{headline}</h2><p>{body}</p></div>')


def page_header(title: str, badge_text: str | None = None) -> None:
    tag = badge(title, "outline") if badge_text else ""
    html(f'<div class="as-page-head"><h2>{title}</h2>{tag}</div>')


def card_open(title_html: str, desc_html: str | None = None) -> None:
    """Open the single `.as-card` panel with its title (and optional desc)."""
    desc = f'<div class="as-card-desc">{desc_html}</div>' if desc_html else ""
    html(f'<div class="as-card"><div class="as-card-title">{title_html}</div>{desc}')


def card_close() -> None:
    """Close a `.as-card` panel opened with `card_open`."""
    html("</div>")


def subnote(text_html: str) -> None:
    """A small muted note, from the one `.as-note` style."""
    html(f'<div class="as-note">{text_html}</div>')


def subheading(title: str) -> None:
    st.markdown(f"#### {title}")


def badge(text: str, tone: str = "outline") -> str:
    """Return an `.as-badge` span. Tones: good/warn/bad/outline."""
    cls = tone if tone in ("good", "warn", "bad", "outline") else "outline"
    return f'<span class="as-badge {cls}">{text}</span>'


def score_card(label: str, value: str, *, primary: bool = False, note: str | None = None) -> None:
    cls = "as-score-card primary" if primary else "as-score-card"
    note_html = f'<div class="as-score-note">{note}</div>' if note else ""
    html(f'<div class="{cls}"><div class="as-score-label">{label}</div>'
         f'<div class="as-score-value">{value}</div>{note_html}</div>')


def metric_row(label: str, value: str, tone: str | None = None) -> str:
    cls = f" as-metric-val {tone}" if tone in ("good", "bad", "warn") else " as-metric-val"
    return (f'<div class="as-metric-row"><span>{label}</span>'
            f'<span class="{cls}">{value}</span></div>')


def info_box(msg: str, kind: str = "info") -> None:
    html(f'<div class="as-alert {kind}">{msg}</div>')


def empty_state(icon: str, title: str, body: str) -> None:
    html(
        f'<div class="as-empty"><div class="as-empty-icon">{icon}</div>'
        f'<div class="as-empty-text"><div class="as-empty-title">{title}</div>'
        f'<div class="as-empty-body">{body}</div></div></div>'
    )


def rec_rows(items) -> None:
    html("".join(f'<div class="as-rec"><span>✓</span><span>{item}</span></div>' for item in items))


def chain_card(title: str, rows, badges=()) -> None:
    """A numbered chain step: title, optional badges, then metric rows."""
    badge_html = "".join(badge(*item) for item in badges)
    inner = "".join(metric_row(*row) for row in rows)
    html(f'<div class="as-muted-box"><h4>{title}</h4>{badge_html}'
         f'<div style="margin-top:.6rem">{inner}</div></div>')


def divider() -> None:
    html('<hr>')


def base_layout(**overrides) -> dict:
    """Shared dark layout for plotly figures (monochrome, IBM Plex Mono ticks)."""
    layout = dict(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="IBM Plex Sans, sans-serif", color="#b0b0b0", size=12),
        xaxis=dict(gridcolor="#1c1c1c", zerolinecolor="#2a2a2a", tickfont=dict(color="#b0b0b0")),
        yaxis=dict(gridcolor="#1c1c1c", zerolinecolor="#2a2a2a", tickfont=dict(color="#b0b0b0")),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#b0b0b0")),
        margin=dict(l=12, r=12, t=28, b=12),
        hoverlabel=dict(bgcolor="#0d0d0d", bordercolor="#2a2a2a", font=dict(color="#fff")),
    )
    layout.update(overrides)
    return layout