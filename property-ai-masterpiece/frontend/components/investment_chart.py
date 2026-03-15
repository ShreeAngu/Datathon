"""Investment analysis display component."""
import streamlit as st
from typing import Dict


def render_investment_chart(inv: Dict):
    """Render investment metrics from analyze_investment() response."""
    if not inv:
        st.info("No investment data available.")
        return

    score = inv.get("investment_score", 0)
    grade_color = "#28a745" if score >= 70 else ("#ffc107" if score >= 45 else "#dc3545")

    # Score header
    st.markdown(
        f'<div style="text-align:center;padding:12px;background:{grade_color}20;'
        f'border-radius:10px;border:1px solid {grade_color}40;margin-bottom:12px">'
        f'<div style="font-size:2rem;font-weight:800;color:{grade_color}">'
        f'{score:.0f}<span style="font-size:1rem">/100</span></div>'
        f'<div style="color:#555;font-size:0.85rem">Investment Score</div></div>',
        unsafe_allow_html=True,
    )

    # Key metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Gross Yield",   f"{inv.get('gross_rental_yield', 0):.1f}%")
    m2.metric("Net Yield",     f"{inv.get('net_rental_yield', 0):.1f}%")
    m3.metric("Cap Rate",      f"{inv.get('cap_rate', 0):.1f}%")

    m4, m5, m6 = st.columns(3)
    m4.metric("Est. Monthly Rent", f"${inv.get('estimated_monthly_rent', 0):,.0f}")
    m5.metric("Price/sqft",
              f"${inv.get('price_per_sqft', 0):,.0f}" if inv.get("price_per_sqft") else "N/A")
    m6.metric("Market Avg/sqft",
              f"${inv.get('market_avg_ppsf', 0):,.0f}" if inv.get("market_avg_ppsf") else "N/A")

    # Market position
    pos = inv.get("market_position", "market_rate")
    pos_map = {
        "below_market": ("🟢 Below Market", "success"),
        "market_rate":  ("🟡 Market Rate",  "warning"),
        "above_market": ("🔴 Above Market", "error"),
    }
    label, kind = pos_map.get(pos, ("⚪ Unknown", "info"))
    getattr(st, kind)(label)

    # Recommendation
    rec = inv.get("recommendation", "")
    if rec:
        st.caption(f"💡 {rec}")

    # Comps
    comps = inv.get("comparable_count", 0)
    if comps:
        st.caption(f"Based on {comps} comparable listing(s) in the area")
