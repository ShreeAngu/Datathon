"""
Property AI Masterpiece — Streamlit Dashboard
Run: streamlit run frontend/app.py --server.port 8501
"""

import streamlit as st
import requests
import os
import plotly.express as px
import plotly.graph_objects as go

API = "http://localhost:8000"

st.set_page_config(
    page_title="Property AI Masterpiece",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stMetricValue"] { font-size: 1.6rem; }
.trust-high  { color: #2ecc71; font-weight: bold; }
.trust-low   { color: #e74c3c; font-weight: bold; }
.badge-real  { background:#2ecc71; color:white; padding:2px 8px; border-radius:4px; font-size:0.75rem; }
.badge-fake  { background:#e74c3c; color:white; padding:2px 8px; border-radius:4px; font-size:0.75rem; }
div[data-testid="stImage"] img { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ──────────────────────────────────────────────────────────────────
st.sidebar.image("https://img.icons8.com/fluency/96/home.png", width=60)
st.sidebar.title("Property AI")
st.sidebar.caption("Powered by CLIP · YOLOv8 · Depth Anything")
page = st.sidebar.radio("Navigate", ["🔍 Search", "📤 Upload & Analyze",
                                      "📊 Dashboard", "🖼️ Browse Gallery",
                                      "🎨 Virtual Staging"])
st.sidebar.divider()
st.sidebar.caption(f"API: `{API}`")

# ── Helpers ───────────────────────────────────────────────────────────────────
def api_get(path, params=None):
    try:
        r = requests.get(f"{API}{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None

def trust_badge(score: float) -> str:
    if score >= 60:
        return f'<span class="badge-real">✓ Real {score:.0f}</span>'
    return f'<span class="badge-fake">⚠ AI {score:.0f}</span>'

def score_color(score: float) -> str:
    if score >= 70: return "normal"
    if score >= 45: return "off"
    return "inverse"

# ── Page: Search ─────────────────────────────────────────────────────────────
if page == "🔍 Search":
    st.title("🔍 Semantic Property Search")
    st.caption("Search using natural language — powered by CLIP embeddings")

    query = st.text_input("Describe what you're looking for",
                          "bright modern living room with natural light",
                          label_visibility="collapsed")

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    with c1: min_trust   = st.slider("Min trust score", 0, 100, 0)
    with c2: accessibility = st.checkbox("♿ Accessible only")
    with c3: limit       = st.select_slider("Results", [6, 12, 24, 48], value=12)
    with c4: search_btn  = st.button("Search", use_container_width=True, type="primary")

    if search_btn and query:
        with st.spinner("Searching 570 images..."):
            data = api_get("/api/v1/search", {
                "query": query,
                "min_trust_score": min_trust,
                "accessibility_required": accessibility,
                "limit": limit,
            })

        if data and data["count"] > 0:
            st.caption(f"Found **{data['count']}** results")
            cols = st.columns(3)
            for i, r in enumerate(data["results"]):
                with cols[i % 3]:
                    img_url = f"{API}{r['image_url']}" if r.get("image_url") else None
                    if img_url:
                        st.image(img_url, use_container_width=True)
                    else:
                        st.info("No image")
                    st.markdown(trust_badge(r["trust_score"]), unsafe_allow_html=True)
                    st.caption(f"🏠 {r['room_type'].replace('_',' ').title()}  ·  "
                               f"⭐ {r['overall_score']:.0f}  ·  "
                               f"♿ {r['accessibility_score']:.0f}  ·  "
                               f"sim {r['similarity']:.3f}")
                    if st.button("Details", key=f"s_{r['id']}"):
                        st.session_state["detail_id"] = r["id"]
                        st.rerun()
        elif data:
            st.info("No results matched your filters. Try lowering the trust score threshold.")

# ── Page: Upload ──────────────────────────────────────────────────────────────
elif page == "📤 Upload & Analyze":
    st.title("📤 Upload & Analyze")
    st.caption("Upload property photos for instant AI analysis")

    uploaded = st.file_uploader("Choose images", type=["jpg", "jpeg", "png", "webp"],
                                 accept_multiple_files=True)

    if st.button("Analyze", type="primary", disabled=not uploaded):
        with st.spinner(f"Analyzing {len(uploaded)} image(s)..."):
            files = [("files", (f.name, f.read(), f.type)) for f in uploaded]
            try:
                r = requests.post(f"{API}/api/v1/upload", files=files, timeout=120)
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                st.error(f"Upload failed: {e}")
                data = None

        if data:
            st.success(f"✅ Analyzed {data['count']} image(s)")
            for img in data["images"]:
                with st.expander(f"📄 {img['filename']}", expanded=True):
                    a = img["analysis"]
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Overall Score",    f"{a['quality']['overall_score']:.1f}/100")
                    c2.metric("Trust Score",      f"{a['authenticity']['trust_score']:.1f}/100")
                    c3.metric("Accessibility",    f"{a['accessibility']['accessibility_score']:.1f}/100")
                    c4.metric("Room Type",        a["spatial"]["room_type"].replace("_", " ").title())

                    if a["authenticity"]["is_ai_generated"]:
                        st.error("⚠️ AI-Generated image detected")
                    else:
                        st.success("✅ Appears to be a real photograph")

                    if a["quality"]["recommendations"]:
                        st.subheader("Recommendations")
                        for rec in a["quality"]["recommendations"]:
                            st.info(f"💡 {rec}")

# ── Page: Dashboard ───────────────────────────────────────────────────────────
elif page == "📊 Dashboard":
    st.title("📊 Dataset Quality Dashboard")

    stats = api_get("/api/v1/stats")
    if not stats:
        st.stop()

    # KPIs
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("Total Images",   stats["total_images"])
    k2.metric("Real Photos",    stats["real_images"])
    k3.metric("AI Generated",   stats["fake_images"])
    k4.metric("Avg Quality",    f"{stats['avg_quality_score']}/100",
              delta=f"{stats['avg_quality_score']-50:.1f} vs baseline")
    k5.metric("Avg Trust",      f"{stats['avg_trust_score']}/100")

    st.divider()
    col_l, col_r = st.columns(2)

    # Room type distribution
    with col_l:
        st.subheader("Room Type Distribution")
        rd = stats["room_type_distribution"]
        fig = px.bar(x=list(rd.keys()), y=list(rd.values()),
                     labels={"x": "Room Type", "y": "Count"},
                     color=list(rd.values()), color_continuous_scale="Blues")
        fig.update_layout(showlegend=False, margin=dict(t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)

    # Style distribution
    with col_r:
        st.subheader("Style Distribution")
        sd = stats["style_distribution"]
        fig2 = px.pie(names=list(sd.keys()), values=list(sd.values()),
                      hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        fig2.update_layout(margin=dict(t=10, b=10))
        st.plotly_chart(fig2, use_container_width=True)

    # Quality radar
    st.subheader("Average Quality Dimensions")
    fig3 = go.Figure(go.Scatterpolar(
        r=[stats["avg_quality_score"],
           stats["avg_trust_score"],
           70, 65, 60],
        theta=["Overall Quality", "Authenticity", "Lighting", "Composition", "Accessibility"],
        fill="toself",
        line_color="#4A90D9",
    ))
    fig3.update_layout(polar=dict(radialaxis=dict(range=[0, 100])),
                       margin=dict(t=20, b=20))
    st.plotly_chart(fig3, use_container_width=True)

# ── Page: Gallery ─────────────────────────────────────────────────────────────
elif page == "🖼️ Browse Gallery":
    st.title("🖼️ Image Gallery")

    gc1, gc2, gc3 = st.columns(3)
    with gc1: label_filter = st.selectbox("Label", ["all", "real", "fake"])
    with gc2: page_num     = st.number_input("Page", min_value=1, value=1)
    with gc3: per_page     = st.select_slider("Per page", [12, 24, 48], value=24)

    params = {"page": page_num, "per_page": per_page}
    if label_filter != "all":
        params["label"] = label_filter

    data = api_get("/api/v1/images", params)
    if not data:
        st.stop()

    st.caption(f"Showing {len(data['items'])} of {data['total']} images  "
               f"(page {data['page']})")

    cols = st.columns(4)
    for i, item in enumerate(data["items"]):
        with cols[i % 4]:
            img_url = f"{API}{item['image_url']}" if item.get("image_url") else None
            if img_url:
                st.image(img_url, use_container_width=True)
            lbl_html = (f'<span class="badge-fake">AI</span>'
                        if item["label"] == "fake"
                        else f'<span class="badge-real">Real</span>')
            st.markdown(lbl_html, unsafe_allow_html=True)
            st.caption(f"{item['room_type'].replace('_',' ').title()}  ·  "
                       f"⭐ {item['overall_score']:.0f}")
            if st.button("Details", key=f"g_{item['id']}"):
                st.session_state["detail_id"] = item["id"]
                st.rerun()

# ── Page: Virtual Staging ─────────────────────────────────────────────────────
elif page == "🎨 Virtual Staging":
    st.title("🎨 Virtual Staging")
    st.caption("Enhance rooms while preserving architectural integrity — walls, windows and doors stay unchanged")

    styles_data  = api_get("/api/v1/staging-styles")
    samples_data = api_get("/api/v1/staging-samples", {"limit": 9})
    if not styles_data or not samples_data:
        st.stop()

    styles  = {s["id"]: s for s in styles_data["styles"]}
    samples = samples_data["samples"]

    # ── Step 1: Select room ───────────────────────────────────────────────────
    st.subheader("Step 1 — Select a Room")
    cols = st.columns(3)
    for i, img in enumerate(samples):
        with cols[i % 3]:
            st.image(f"{API}{img['image_url']}", use_container_width=True)
            st.caption(img["room_type"].replace("_", " ").title()
                       + f"  ·  `{img['category']}`")
            if st.button("Select", key=f"staging_sel_{i}_{img['id'][:8]}"):
                st.session_state["staging_image"]  = img
                st.session_state.pop("staging_result", None)
                st.rerun()

    if "staging_image" not in st.session_state:
        st.info("👆 Select a room above to continue")
        st.stop()

    sel = st.session_state["staging_image"]
    st.success(f"Selected: **{sel['room_type'].replace('_',' ').title()}**  (`{sel['id']}`)")

    # ── Step 2: Choose style ──────────────────────────────────────────────────
    st.subheader("Step 2 — Choose a Design Style")
    selected_style = st.session_state.get("staging_style", "modern")
    scols = st.columns(len(styles))
    for i, (sid, sinfo) in enumerate(styles.items()):
        emoji = {"modern":"🏢","scandinavian":"🌲","industrial":"🏭","rustic":"🏡","luxury":"💎"}.get(sid,"🎨")
        with scols[i]:
            if st.button(f"{emoji} {sinfo['name']}", key=f"style_{sid}",
                         use_container_width=True,
                         type="primary" if sid == selected_style else "secondary"):
                st.session_state["staging_style"] = sid
                st.session_state.pop("staging_result", None)
                selected_style = sid
                st.rerun()
            st.caption(sinfo["description"])

    st.divider()

    # ── Step 3: Generate ──────────────────────────────────────────────────────
    st.subheader("Step 3 — Generate")
    if st.button("🪄 Generate Staging", type="primary", use_container_width=False):
        with st.spinner(f"Staging with {styles[selected_style]['name']} style..."):
            try:
                r = requests.post(f"{API}/api/v1/stage",
                                  params={"image_id": sel["id"], "style": selected_style},
                                  timeout=120)
                r.raise_for_status()
                st.session_state["staging_result"] = r.json()
            except Exception as e:
                st.error(f"Staging failed: {e}")

    # ── Results ───────────────────────────────────────────────────────────────
    if "staging_result" in st.session_state:
        result = st.session_state["staging_result"]

        # Before / After
        st.subheader("Before / After")
        bc, ac = st.columns(2)
        with bc:
            st.image(f"{API}{result['original_image_url']}",
                     caption="📷 Before (Original)", use_container_width=True)
        with ac:
            st.image(f"{API}{result['staged_image_url']}",
                     caption=f"✨ After ({styles[result['style']]['name']})",
                     use_container_width=True)

        # Change map
        if result.get("change_map_url"):
            with st.expander("🔍 Change Detection Map"):
                st.image(f"{API}{result['change_map_url']}",
                         caption="Gold areas = modified pixels", use_container_width=True)

        # Changes report
        changes = api_get(f"/api/v1/staging-changes/{sel['id']}/{result['style']}")
        if changes:
            st.subheader("What Changed")
            cc1, cc2 = st.columns(2)
            with cc1:
                st.markdown("**✅ Modifications applied:**")
                for c in changes["changes_made"]:
                    st.markdown(f"- {c}")
            with cc2:
                st.markdown("**🔒 Preserved (unchanged):**")
                for p in changes["preserved_elements"]:
                    st.markdown(f"- {p}")

        # Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Processing Time", f"{result['processing_time']:.1f}s")
        m2.metric("Style", styles[result["style"]]["name"])
        m3.metric("Mode", result.get("tier", "—"))

        if result.get("structure_preserved"):
            st.success("✅ Architectural structure preserved — walls, windows and doors unchanged")
        if result.get("fallback"):
            st.info("💡 Style enhancement preview. Local SD 1.5 model available for full AI staging (~15s).")

        # Download
        staged_fname = result["staged_image_url"].split("/")[-1]
        staged_path  = f"dataset/staged/{staged_fname}"
        if os.path.exists(staged_path):
            with open(staged_path, "rb") as fh:
                st.download_button("📥 Download Staged Image", fh.read(),
                                   file_name=staged_fname, mime="image/jpeg")

        if st.button("🔄 Try another style / room"):
            st.session_state.pop("staging_result", None)
            st.rerun()


# ── Detail Panel (session state overlay) ─────────────────────────────────────
if "detail_id" in st.session_state:
    image_id = st.session_state["detail_id"]
    analysis = api_get(f"/api/v1/analysis/{image_id}")

    if analysis:
        st.divider()
        st.subheader(f"🔍 Analysis: `{image_id}`")

        img_url = f"{API}{analysis.get('image_url', '')}"
        dc1, dc2 = st.columns([1, 2])

        with dc1:
            if analysis.get("image_url"):
                st.image(img_url, use_container_width=True)
            depth_url = f"{API}/viz/depth_maps/{image_id}_depth.png"
            st.image(depth_url, caption="Depth Map", use_container_width=True)

        with dc2:
            t1, t2, t3, t4 = st.tabs(["🏠 Spatial", "🛡️ Authenticity",
                                        "♿ Accessibility", "⭐ Quality"])
            with t1:
                s = analysis["spatial"]
                st.metric("Room Type",    s["room_type"].replace("_", " ").title())
                st.metric("Style",        s["style"].replace("_", " ").title())
                st.metric("Spaciousness", f"{s['spaciousness_score']:.1f}/100")
                st.metric("Clutter",      f"{s['clutter_score']:.1f}/100")
                st.metric("Lighting",     f"{s['lighting_quality']:.1f}/100")

            with t2:
                a = analysis["authenticity"]
                if a["is_ai_generated"]:
                    st.error("⚠️ AI-Generated image detected")
                else:
                    st.success("✅ Verified authentic photograph")
                st.metric("Trust Score",  f"{a['trust_score']:.1f}/100")
                st.metric("Confidence",   f"{a['detection_confidence']:.2f}")
                st.metric("EXIF Valid",   "Yes" if a["exif_valid"] else "No")
                if a["artifacts_detected"]:
                    st.caption("Artifacts: " + ", ".join(a["artifacts_detected"]))

            with t3:
                ac = analysis["accessibility"]
                st.metric("Accessibility Score", f"{ac['accessibility_score']:.1f}/100")
                st.metric("Door Width",          f"{ac['estimated_door_width_cm']} cm")
                if ac["has_grab_bar"]:  st.success("✅ Grab bar detected")
                if ac["has_stairs"]:    st.warning("⚠️ Stairs detected")
                if ac["is_wheelchair_accessible"]: st.success("✅ Wheelchair accessible")
                if ac["features_detected"]:
                    st.caption("Features: " + ", ".join(ac["features_detected"]))

            with t4:
                q = analysis["quality"]
                st.metric("Overall Score",   f"{q['overall_score']:.1f}/100")
                st.metric("Sharpness",       f"{q['sharpness_score']:.1f}/100")
                st.metric("Composition",     f"{q['composition_score']:.1f}/100")
                st.metric("Resolution",      f"{q['resolution_score']:.1f}/100")
                if q["recommendations"]:
                    st.subheader("Recommendations")
                    for rec in q["recommendations"]:
                        st.info(f"💡 {rec}")

        if st.button("✕ Close", type="secondary"):
            del st.session_state["detail_id"]
            st.rerun()
