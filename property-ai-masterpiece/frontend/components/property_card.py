"""Reusable property card component."""
import streamlit as st
from typing import Dict
from utils.api_client import image_url


def render_property_card(prop: Dict, key_prefix: str = "pc") -> bool:
    """
    Renders a property card. Returns True if 'View Details' was clicked.
    Works with both listing rows (from advanced_search) and
    reverse-search match dicts.
    """
    lid = prop.get("id") or prop.get("listing_id", "unknown")

    # Image
    img = image_url(prop.get("image_url", ""))
    if img:
        try:
            st.image(img, use_container_width=True)
        except Exception:
            st.markdown("🖼️ *Image unavailable*")
    else:
        st.markdown("🖼️ *No image*")

    # Price / title
    price = prop.get("price") or 0
    try:
        price = float(price)
    except (TypeError, ValueError):
        price = 0
    title = prop.get("title", "")
    if price:
        st.markdown(f"**${price:,.0f}**" + (f" — {title}" if title else ""))
    elif title:
        st.markdown(f"**{title}**")

    # Details row
    beds  = prop.get("bedrooms", "")
    baths = prop.get("bathrooms", "")
    sqft  = prop.get("square_feet", "")
    parts = []
    if beds:  parts.append(f"🛏 {beds}")
    if baths: parts.append(f"🚿 {baths}")
    if sqft:
        try:
            parts.append(f"📐 {int(float(sqft)):,} sqft")
        except (TypeError, ValueError):
            pass
    if parts:
        st.caption("  ·  ".join(parts))

    city  = prop.get("city", "")
    state = prop.get("state", "")
    if city or state:
        st.caption(f"📍 {city}, {state}".strip(", "))

    # Badges
    bc1, bc2, bc3 = st.columns(3)
    with bc1:
        if prop.get("authenticity_verified"):
            st.success("✅ Verified", icon=None)
    with bc2:
        try:
            qs = float(prop.get("overall_quality_score") or prop.get("overall_score") or 0)
            if qs >= 80:
                st.info(f"⭐ {qs:.0f}")
        except (TypeError, ValueError):
            pass
    with bc3:
        sim = prop.get("similarity")
        if sim is not None:
            try:
                st.caption(f"🎯 {float(sim)*100:.0f}%")
            except (TypeError, ValueError):
                pass

    clicked = st.button("View Details", key=f"{key_prefix}_{lid}",
                         use_container_width=True)
    st.markdown("---")
    return clicked
