"""Shared CSS injected across all pages."""
import streamlit as st

GLOBAL_CSS = """
<style>
/* Metric cards */
[data-testid="metric-container"] {
    background: #f8f9fa;
    border: 1px solid #e9ecef;
    border-radius: 10px;
    padding: 12px 16px;
}
/* Score badge */
.score-badge {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 20px;
    font-weight: 600;
    font-size: 0.85rem;
}
.score-high  { background: #d4edda; color: #155724; }
.score-mid   { background: #fff3cd; color: #856404; }
.score-low   { background: #f8d7da; color: #721c24; }
/* Property card */
.prop-card {
    border: 1px solid #dee2e6;
    border-radius: 12px;
    padding: 12px;
    margin-bottom: 12px;
    background: white;
}
/* Palette swatch */
.swatch {
    display: inline-block;
    width: 36px; height: 36px;
    border-radius: 6px;
    margin: 2px;
    border: 1px solid rgba(0,0,0,0.1);
}
/* Sidebar header */
.sidebar-title {
    font-size: 1.1rem;
    font-weight: 700;
    color: #495057;
    margin-bottom: 8px;
}
</style>
"""


def inject_css():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def score_badge(score: float) -> str:
    cls = "score-high" if score >= 75 else ("score-mid" if score >= 50 else "score-low")
    return f'<span class="score-badge {cls}">{score:.0f}/100</span>'


def palette_swatches(palette: list) -> str:
    html = ""
    for c in palette[:6]:
        hex_val = c.get("hex", "#ccc")
        pct = c.get("percent", 0)
        html += (f'<span class="swatch" style="background:{hex_val}" '
                 f'title="{hex_val} {pct:.0f}%"></span>')
    return html
