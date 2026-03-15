"""Admin Panel — Platform stats, user management, listing moderation."""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import utils.api_client as api
from utils.styling import inject_css

st.set_page_config(page_title="Admin Panel", page_icon="👨‍💼", layout="wide")
inject_css()

# ── Auth guard ────────────────────────────────────────────────────────────────
hc1, hc2 = st.columns([4, 1])
with hc1:
    st.title("👨‍💼 Admin Panel")
with hc2:
    if st.session_state.get("token"):
        st.caption(f"👤 {st.session_state.get('name')}")
        if st.button("Logout", key="admin_logout"):
            api.logout()
    else:
        if st.button("Login"):
            st.switch_page("pages/4_Auth.py")

if not st.session_state.get("token"):
    st.warning("Admin access requires login.")
    if st.button("Go to Login", type="primary"):
        st.switch_page("pages/4_Auth.py")
    st.stop()

if st.session_state.get("user_type") not in ("admin",):
    st.error("⛔ Admin access only.")
    st.stop()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_overview, tab_users, tab_listings = st.tabs(
    ["📊 Overview", "👥 Users", "🏠 Listings"])

# ── OVERVIEW ──────────────────────────────────────────────────────────────────
with tab_overview:
    stats = api.admin_stats()
    if stats:
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total Users",    stats.get("total_users", 0))
        k2.metric("Active Users",   stats.get("active_users", 0))
        k3.metric("Total Listings", stats.get("total_listings", 0))
        k4.metric("Published",      stats.get("published_listings", 0))
        k5.metric("Total Images",   stats.get("total_images", 0))

        st.divider()
        oc1, oc2 = st.columns(2)
        with oc1:
            st.markdown("#### User Breakdown")
            buyers  = stats.get("buyers", 0)
            sellers = stats.get("sellers", 0)
            admins  = stats.get("admins", 0)
            st.write(f"🛒 Buyers: **{buyers}**")
            st.write(f"🏠 Sellers: **{sellers}**")
            st.write(f"👨‍💼 Admins: **{admins}**")
        with oc2:
            st.markdown("#### Listing Status")
            for status in ("published", "draft", "pending", "sold", "archived"):
                count = stats.get(f"{status}_listings", 0)
                if count:
                    st.write(f"• {status.title()}: **{count}**")
    else:
        st.info("Could not load platform stats.")

# ── USERS ─────────────────────────────────────────────────────────────────────
with tab_users:
    search_q = st.text_input("Search users by name or email", key="user_search")
    page     = st.number_input("Page", min_value=1, value=1, key="user_page")

    data = api.admin_users(page=page, search=search_q or None)
    if data:
        users = data.get("users", [])
        total = data.get("total", 0)
        st.caption(f"{total} user(s) found")

        for u in users:
            uc1, uc2, uc3, uc4 = st.columns([4, 1, 1, 1])
            with uc1:
                active_icon = "🟢" if u.get("is_active") else "🔴"
                st.write(f"{active_icon} **{u.get('name', '—')}** "
                         f"— {u.get('email', '—')} "
                         f"({u.get('user_type', '—')})")
                st.caption(f"Joined: {str(u.get('created_at', ''))[:10]}")
            with uc2:
                st.caption("Active" if u.get("is_active") else "Suspended")
            with uc3:
                if u.get("is_active"):
                    if st.button("Suspend", key=f"susp_{u['id']}"):
                        api.admin_suspend_user(u["id"])
                        st.rerun()
                else:
                    if st.button("Activate", key=f"act_{u['id']}"):
                        api.admin_activate_user(u["id"])
                        st.rerun()
            with uc4:
                if st.button("Delete", key=f"delusr_{u['id']}"):
                    api.admin_delete_user(u["id"])
                    st.rerun()
    else:
        st.info("No users found.")

# ── LISTINGS ──────────────────────────────────────────────────────────────────
with tab_listings:
    status_filter = st.selectbox("Filter by status",
                                 ["all", "published", "draft", "pending",
                                  "sold", "archived"])
    lpage = st.number_input("Page", min_value=1, value=1, key="listing_page")

    data = api.admin_listings(
        status=None if status_filter == "all" else status_filter,
        page=lpage)
    if data:
        listings = data.get("listings", [])
        total    = data.get("total", 0)
        st.caption(f"{total} listing(s)")

        for l in listings:
            lc1, lc2, lc3 = st.columns([5, 1, 2])
            with lc1:
                st.write(f"**{l.get('title', 'Untitled')}** — "
                         f"{l.get('city', '')}, {l.get('state', '')} — "
                         f"${l.get('price', 0):,.0f}")
                try:
                    qs = l.get('overall_quality_score')
                    qs_str = f"{float(qs):.1f}" if qs is not None else "N/A"
                except (TypeError, ValueError):
                    qs_str = "N/A"
                st.caption(f"Seller: {l.get('seller_name', '—')}  ·  "
                           f"Status: {l.get('status', '—')}  ·  "
                           f"Quality: {qs_str}")
            with lc2:
                st.caption(l.get("status", "—").title())
            with lc3:
                new_status = st.selectbox(
                    "Set status",
                    ["published", "draft", "pending", "archived"],
                    key=f"lstatus_{l['id']}",
                    index=["published", "draft", "pending", "archived"].index(
                        l.get("status", "draft"))
                    if l.get("status") in ["published", "draft", "pending", "archived"]
                    else 1,
                )
                if st.button("Apply", key=f"lapply_{l['id']}"):
                    api.admin_update_listing_status(l["id"], new_status)
                    st.rerun()
    else:
        st.info("No listings found.")
