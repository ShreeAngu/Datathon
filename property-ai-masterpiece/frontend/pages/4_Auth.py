"""Login / Register page."""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import utils.api_client as api
from utils.styling import inject_css

st.set_page_config(page_title="Login — Property AI", page_icon="🔐", layout="centered")
inject_css()
st.title("🔐 Account")

# Already logged in
if st.session_state.get("token"):
    st.success(f"✅ Logged in as **{st.session_state.get('name')}** "
               f"({st.session_state.get('user_type')})")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("🔍 Buyer Dashboard", use_container_width=True):
            st.switch_page("pages/1_Buyer_Dashboard.py")
    with col2:
        if st.button("🏠 Seller Dashboard", use_container_width=True):
            st.switch_page("pages/2_Seller_Dashboard.py")
    with col3:
        if st.button("Logout", use_container_width=True):
            api.logout()
    st.stop()

tab_login, tab_reg = st.tabs(["Login", "Register"])

with tab_login:
    with st.form("login_form"):
        email = st.text_input("Email", placeholder="buyer1@propertyai.demo")
        pwd   = st.text_input("Password", type="password", placeholder="Buyer123!")
        submitted = st.form_submit_button("Login", type="primary", use_container_width=True)

    if submitted:
        if not email or not pwd:
            st.error("Email and password are required")
        else:
            with st.spinner("Logging in..."):
                r = api.login(email, pwd)
            if r and r.get("token"):
                st.success(f"Welcome back, {r['name']}!")
                utype = r.get("user_type", "buyer")
                if utype == "admin":
                    st.switch_page("pages/3_Admin_Panel.py")
                elif utype == "seller":
                    st.switch_page("pages/2_Seller_Dashboard.py")
                else:
                    st.switch_page("pages/1_Buyer_Dashboard.py")
            else:
                st.error("Invalid credentials. Check email and password.")

    st.divider()
    st.caption("Demo accounts:")
    st.code("buyer1@propertyai.demo / Buyer123!\nseller1@propertyai.demo / Seller123!\nadmin@propertyai.demo / AdminDemo2026!")

with tab_reg:
    with st.form("register_form"):
        rname  = st.text_input("Full Name")
        remail = st.text_input("Email")
        rutype = st.selectbox("I am a", ["buyer", "seller", "both"])
        rpwd   = st.text_input("Password", type="password")
        rpwd2  = st.text_input("Confirm Password", type="password")
        reg_submitted = st.form_submit_button("Create Account", type="primary",
                                              use_container_width=True)

    if reg_submitted:
        if not all([rname, remail, rpwd]):
            st.error("All fields are required")
        elif rpwd != rpwd2:
            st.error("Passwords do not match")
        elif len(rpwd) < 8:
            st.error("Password must be at least 8 characters")
        else:
            with st.spinner("Creating account..."):
                r = api.register(remail, rpwd, rname, rutype)
            if r and r.get("token"):
                st.success(f"Account created! Welcome, {r['name']}!")
                st.rerun()
            else:
                st.error("Registration failed. Email may already be in use.")
