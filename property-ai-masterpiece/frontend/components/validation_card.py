"""AI validation results card for seller upload."""
import streamlit as st
from typing import Dict
from utils.styling import score_badge
from utils.api_client import BASE


def render_validation_card(v: Dict, file_bytes: bytes = None):
    """Render full AI validation result for one uploaded image."""
    overall = v.get("overall_quality", 0)
    room    = v.get("verified_room_type", "unknown").replace("_", " ").title()
    matched = v.get("matches_expected", True)

    # Header row
    hc1, hc2 = st.columns([5, 1])
    with hc1:
        if matched:
            st.success(f"✅ Room verified: **{room}** "
                       f"({v.get('room_confidence', 0)*100:.0f}% confidence)")
        else:
            st.warning(f"⚠️ Room mismatch — detected as **{room}**")
    with hc2:
        cls = "score-high" if overall >= 75 else ("score-mid" if overall >= 50 else "score-low")
        st.markdown(f'<div style="text-align:center">'
                    f'<div style="font-size:0.75rem;color:#666">Overall</div>'
                    f'<span class="score-badge {cls}" style="font-size:1.1rem">'
                    f'{overall:.0f}/100</span></div>', unsafe_allow_html=True)

    # Score grid
    sc1, sc2, sc3, sc4 = st.columns(4)
    with sc1:
        ls = v.get("lighting_score", 0)
        st.metric("🌞 Lighting", f"{ls:.0f}/100",
                  delta="Good" if ls >= 70 else "Needs work",
                  delta_color="normal" if ls >= 70 else "inverse")
        if ls < 60:
            st.caption(v.get("lighting_feedback", ""))
    with sc2:
        cs = v.get("clutter_score", 0)
        st.metric("🧹 Clutter", f"{cs:.0f}/100",
                  delta="Clean" if cs >= 70 else "Cluttered",
                  delta_color="normal" if cs >= 70 else "inverse")
        locs = v.get("clutter_locations", [])
        if locs:
            st.caption(f"Objects: {', '.join(locs[:3])}")
    with sc3:
        cmp = v.get("composition_score", 0)
        st.metric("📐 Composition", f"{cmp:.0f}/100",
                  delta="Good" if cmp >= 70 else "Issues",
                  delta_color="normal" if cmp >= 70 else "inverse")
        issues = v.get("composition_issues", [])
        if issues:
            st.caption(", ".join(issues[:2]))
    with sc4:
        ai_prob = v.get("ai_probability", 0)
        auth    = 100 - ai_prob
        st.metric("🛡️ Authentic", f"{auth:.0f}/100",
                  delta="Real" if not v.get("is_ai_generated") else "AI Detected",
                  delta_color="normal" if not v.get("is_ai_generated") else "inverse")
        if v.get("is_ai_generated"):
            st.error("⚠️ AI-generated image")

    # Duplicate warning
    if v.get("is_duplicate"):
        st.warning(f"⚠️ Possible duplicate — similar image found in listing "
                   f"`{v.get('duplicate_listing_id', 'unknown')}`")

    # Heatmap
    heatmap = v.get("clutter_heatmap_path")
    if heatmap and v.get("clutter_score", 100) < 70:
        with st.expander("🔥 View Clutter Heatmap"):
            hc1, hc2 = st.columns(2)
            with hc1:
                if file_bytes:
                    st.image(file_bytes, caption="Original", use_container_width=True)
                else:
                    st.caption("Original image")
            with hc2:
                heatmap_url = f"{BASE}/uploads/heatmaps/{heatmap.split('/')[-1]}"
                try:
                    st.image(heatmap_url, caption="Clutter heatmap (red = high)",
                             use_container_width=True)
                except Exception:
                    st.caption(f"Heatmap: `{heatmap}`")

    # Recommendations
    recs = v.get("recommendations", [])
    if recs:
        with st.expander(f"💡 {len(recs)} Recommendations to improve score"):
            for rec in recs[:6]:
                priority = rec.get("priority", "low")
                icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")
                st.write(f"{icon} **{rec.get('action', rec.get('issue', ''))}**")
                if rec.get("tip"):
                    st.caption(f"   💡 {rec['tip']}")

    st.divider()
