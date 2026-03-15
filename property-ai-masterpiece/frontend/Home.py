"""Property AI Masterpiece v2.0 — Landing Page"""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from utils.styling import inject_css
import utils.api_client as api

st.set_page_config(page_title="Property AI Masterpiece", page_icon="🏠",
                   layout="wide", initial_sidebar_state="expanded")
inject_css()

st.markdown("""
<style>
.hero  { font-size:2.8rem; font-weight:800; color:#1E88E5; margin-bottom:0; }
.sub   { font-size:1.1rem; color:#555; margin-top:0; }
.fcard { background:linear-gradient(135deg,#667eea,#764ba2); padding:20px;
         border-radius:12px; color:white; margin:8px 0; }
</style>""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
hc1, hc2 = st.columns([3, 1])
with hc1:
    st.markdown('<p class="hero">🏠 Property AI Masterpiece</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub">AI-powered property discovery, analysis & management</p>',
                unsafe_allow_html=True)
with hc2:
    if st.session_state.get("token"):
        st.write(f"👤 {st.session_state.get('name')}")
        st.caption(st.session_state.get("user_type", ""))
        if st.button("Logout"):
            api.logout()
    else:
        if st.button("🔐 Login / Register", type="primary"):
            st.switch_page("pages/4_Auth.py")

st.divider()

# ── Feature cards ─────────────────────────────────────────────────────────────
f1, f2, f3 = st.columns(3)
with f1:
    st.markdown('<div class="fcard"><h3>🔍 Smart Search</h3>'
                '<p>Natural language + reverse image search powered by CLIP</p></div>',
                unsafe_allow_html=True)
with f2:
    st.markdown('<div class="fcard"><h3>🛡️ Verified Authentic</h3>'
                '<p>93.67% accurate fake detector — MobileNetV3 fine-tuned on 570 images</p></div>',
                unsafe_allow_html=True)
with f3:
    st.markdown('<div class="fcard"><h3>📊 AI Insights</h3>'
                '<p>Investment analysis, neighborhood scores, quality metrics</p></div>',
                unsafe_allow_html=True)

# ── Stats ─────────────────────────────────────────────────────────────────────
st.markdown("### 📊 Platform Statistics")
k1, k2, k3, k4 = st.columns(4)
k1.metric("Images Analyzed", "570")
k2.metric("Fake Detection Acc", "93.67%")
k3.metric("AI Models", "4")
k4.metric("Vector Index", "Pinecone")

st.divider()

# ── Demo credentials ──────────────────────────────────────────────────────────
with st.expander("🔑 Demo Credentials"):
    dc1, dc2, dc3 = st.columns(3)
    with dc1:
        st.markdown("**Buyer**")
        st.code("buyer1@propertyai.demo\nBuyer123!")
    with dc2:
        st.markdown("**Seller**")
        st.code("seller1@propertyai.demo\nSeller123!")
    with dc3:
        st.markdown("**Admin**")
        st.code("admin@propertyai.demo\nAdminDemo2026!")

st.divider()

# ── Navigation ────────────────────────────────────────────────────────────────
st.markdown("### 🚀 Get Started")
n1, n2, n3, n4 = st.columns(4)
with n1:
    st.markdown("#### 🛒 Buyer\nSearch, reverse image, investment analysis, neighborhood scores")
    if st.button("Go to Buyer Dashboard", use_container_width=True, type="primary"):
        st.switch_page("pages/1_Buyer_Dashboard.py")
with n2:
    st.markdown("#### 🏠 Seller\nUpload photos, AI validation, manage listings, analytics")
    if st.button("Go to Seller Dashboard", use_container_width=True):
        st.switch_page("pages/2_Seller_Dashboard.py")
with n3:
    st.markdown("#### 👨‍💼 Admin\nUser management, moderation, platform analytics")
    if st.button("Go to Admin Panel", use_container_width=True):
        st.switch_page("pages/3_Admin_Panel.py")
with n4:
    st.markdown("#### 🔐 Account\nLogin or register to access all features")
    if st.button("Login / Register", use_container_width=True):
        st.switch_page("pages/4_Auth.py")

st.divider()
st.markdown(
    '<div style="text-align:center;color:gray;font-size:0.85rem">'
    'Property AI Masterpiece v2.0 · FastAPI + Streamlit + CLIP + YOLOv8 + MobileNetV3'
    '</div>', unsafe_allow_html=True)
