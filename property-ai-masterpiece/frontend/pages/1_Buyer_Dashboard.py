"""Buyer Dashboard — Search, Reverse Image, Investment, Neighborhood, Compare."""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import utils.api_client as api
from utils.styling import inject_css, palette_swatches
from components.property_card import render_property_card
from components.investment_chart import render_investment_chart

st.set_page_config(page_title="Buyer Dashboard", page_icon="🔍", layout="wide")
inject_css()

# ── Header ────────────────────────────────────────────────────────────────────
hc1, hc2 = st.columns([4, 1])
with hc1:
    st.title("🔍 Buyer Dashboard")
with hc2:
    if st.session_state.get("token"):
        st.caption(f"👤 {st.session_state.get('name')}")
        if st.button("Logout", key="buyer_logout"):
            api.logout()
    else:
        if st.button("Login"):
            st.switch_page("pages/4_Auth.py")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="sidebar-title">🔎 Search Filters</div>',
                unsafe_allow_html=True)

    # Keyword search
    st.markdown("**🔤 Keyword Search**")
    keyword_query = st.text_input(
        "Search listings",
        placeholder="e.g. modern kitchen, waterfront, cozy",
        key="keyword_search"
    )
    semantic_rank = st.checkbox(
        "🧠 Smart Ranking",
        value=False,
        help="Use AI to rank results by relevance (slower but smarter)"
    )
    
    st.markdown("---")
    st.markdown("**📍 Location**")
    city  = st.text_input("City", placeholder="e.g. Seattle")
    state = st.text_input("State", placeholder="e.g. WA")

    st.markdown("---")
    st.markdown("**💰 Price & Size**")
    price_min, price_max = st.slider(
        "Price Range ($)", 0, 3_000_000, (0, 1_500_000), step=10_000,
        format="$%d")

    ptype = st.selectbox("Property Type",
                         ["Any", "house", "apartment", "condo", "townhouse", "land"])
    min_beds  = st.slider("Min Bedrooms",  0, 6, 0)
    min_baths = st.slider("Min Bathrooms", 0, 5, 0)

    st.markdown("---")
    st.markdown("**✨ Quality**")
    min_quality   = st.slider("Min Quality Score", 0, 100, 0)
    verified_only = st.checkbox("Verified Authentic Only")

    st.markdown("---")
    st.markdown("**📷 Reverse Image Search**")
    rev_file = st.file_uploader("Upload a photo to find similar",
                                type=["jpg", "jpeg", "png", "webp"],
                                key="rev_upload")
    top_k    = st.slider("Max results", 5, 30, 10)
    min_sim  = st.slider("Min similarity", 0.0, 1.0, 0.25, 0.05)

    if rev_file:
        if st.button("🔍 Find Similar", type="primary", use_container_width=True):
            with st.spinner("Searching by image... (first search may take ~20s while AI loads)"):
                result = api.reverse_image_search(rev_file, top_k=top_k,
                                                  min_similarity=min_sim)
            if result:
                st.session_state["rev_results"] = result
                st.session_state["active_tab"]  = "reverse"
                st.rerun()

    st.markdown("---")
    if st.button("🔎 Apply Filters", type="primary", use_container_width=True):
        st.session_state["active_tab"] = "search"
        st.rerun()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_search, tab_rev, tab_staging, tab_fav, tab_hist, tab_compare = st.tabs(
    ["🔎 Search", "📷 Reverse Search", "🎨 Virtual Staging", "❤️ Favorites", "🕐 History", "⚖️ Compare"])

# ── SEARCH TAB ────────────────────────────────────────────────────────────────
with tab_search:
    params = dict(
        query=keyword_query or None,
        semantic_rank=semantic_rank if keyword_query else False,
        min_price=price_min, max_price=price_max,
        min_beds=min_beds if min_beds else None,
        min_baths=min_baths if min_baths else None,
        city=city or None, state=state or None,
        property_type=ptype if ptype != "Any" else None,
        min_quality=min_quality if min_quality else None,
        verified_only=verified_only if verified_only else None,
        per_page=18,
    )
    
    # Show search info
    if keyword_query:
        search_mode = "🧠 Smart Search" if semantic_rank else "🔤 Keyword Search"
        st.info(f"{search_mode}: \"{keyword_query}\"")
    
    with st.spinner("Loading listings..."):
        data = api.advanced_search(**params)

    if data:
        total = data.get("total", 0)
        pages = data.get("pages", 1)
        listings = data.get("listings", [])
        semantic_enabled = data.get("semantic_ranking_enabled", False)
        
        # Show results header
        result_text = f"Found **{total}** listing(s)"
        if semantic_enabled:
            result_text += " (ranked by AI relevance)"
        st.caption(result_text)

        if listings:
            cols = st.columns(3)
            for i, prop in enumerate(listings):
                with cols[i % 3]:
                    # Show semantic score if available
                    if prop.get("semantic_score"):
                        st.caption(f"🎯 Relevance: {prop['semantic_score']:.2%}")
                    
                    if render_property_card(prop, key_prefix="srch"):
                        st.session_state["detail_prop"] = prop
                        st.rerun()
        else:
            st.info("No listings match your filters. Try widening the search.")
    else:
        st.info("Adjust filters and click Apply Filters.")

# ── REVERSE SEARCH TAB ────────────────────────────────────────────────────────
with tab_rev:
    rev = st.session_state.get("rev_results")
    if not rev:
        st.info("Upload a photo in the sidebar and click 'Find Similar' to search by image.")
    else:
        # Style + palette header
        style_hint = rev.get("query_style", "")
        palette    = rev.get("query_palette", [])
        rc1, rc2 = st.columns([3, 1])
        with rc1:
            st.markdown(f"**Detected style:** `{style_hint}`  ·  "
                        f"**{rev.get('total_found', 0)}** matches  ·  "
                        f"⏱ {rev.get('search_time_ms', 0):.0f}ms")
            if palette:
                st.markdown(
                    "**Color palette:** " + palette_swatches(palette),
                    unsafe_allow_html=True)
        with rc2:
            if st.button("Clear", key="clear_rev"):
                st.session_state.pop("rev_results", None)
                st.rerun()

        matches = rev.get("matches", [])
        if matches:
            cols = st.columns(3)
            for i, m in enumerate(matches):
                with cols[i % 3]:
                    if render_property_card(m, key_prefix="rev"):
                        st.session_state["detail_prop"] = m
                        st.rerun()
        else:
            st.warning("No similar properties found. Try lowering the similarity threshold.")

# ── VIRTUAL STAGING TAB ───────────────────────────────────────────────────────
with tab_staging:
    st.markdown("### 🎨 Virtual Staging")
    st.caption("Visualize how any property could look with different staging styles")
    
    # Get all published listings
    params = dict(per_page=100)
    with st.spinner("Loading properties..."):
        data = api.advanced_search(**params)
    
    if data and data.get("listings"):
        listings = data["listings"]
        
        # Select property - filter for listings with images
        listing_opts = {f"{l['title']} - {l.get('city', '')}, {l.get('state', '')} (${l.get('price', 0):,.0f})": l 
                       for l in listings if l.get("image_url")}
        
        if not listing_opts:
            st.info("No properties with images available for staging.")
        else:
            selected_label = st.selectbox("Select property to stage", 
                                         list(listing_opts.keys()),
                                         key="buyer_staging_listing")
            selected_listing = listing_opts[selected_label]
            
            # Get full listing details with all images
            lid = selected_listing.get("id")
            with st.spinner("Loading property images..."):
                listing_detail = api.get_listing_detail(lid)
            
            if listing_detail and listing_detail.get("images"):
                images = listing_detail["images"]
                
                # Select image to stage
                img_opts = {f"Image {i+1} ({img['original_filename'][:30]})": img 
                           for i, img in enumerate(images)}
                
                if not img_opts:
                    st.info("This property has no images available for staging.")
                else:
                    selected_img_label = st.selectbox("Select image to stage", 
                                                     list(img_opts.keys()),
                                                     key="buyer_staging_image")
                    selected_img = img_opts[selected_img_label]
                    image_id = selected_img["id"]
                    # Show original image
                    sc1, sc2 = st.columns([1, 1])
                    with sc1:
                        st.markdown("**Original Image**")
                        try:
                            st.image(f"http://localhost:8000{selected_img['image_url']}",
                                    use_container_width=True)
                        except Exception:
                            st.error("Could not load image")
                    
                    with sc2:
                        st.markdown("**Staging Options**")
                        
                        # Mode selector: Furnish or Unfurnish
                        staging_action = st.radio(
                            "Action",
                            ["Add/Update Furniture", "Remove Furniture (Empty Room)"],
                            key="buyer_staging_action",
                            horizontal=True
                        )
                        
                        if staging_action == "Add/Update Furniture":
                            # Mode selector: Predefined styles or Custom prompt
                            staging_mode = st.radio(
                                "Choose mode",
                                ["Predefined Styles", "Custom Prompt"],
                                key="buyer_staging_mode",
                                horizontal=True
                            )
                            
                            if staging_mode == "Predefined Styles":
                                styles = {
                                    "modern": "Modern — Clean lines, minimalist, neutral tones",
                                    "scandinavian": "Scandinavian — Light wood, cozy textiles, white walls",
                                    "industrial": "Industrial — Exposed brick, metal fixtures, dark wood",
                                    "rustic": "Rustic — Farmhouse warmth, vintage furniture",
                                    "luxury": "Luxury — High-end finishes, marble, gold accents",
                                }
                                selected_style = st.selectbox("Choose style", list(styles.keys()),
                                                             format_func=lambda x: styles[x],
                                                             key="buyer_staging_style")
                                custom_prompt = None
                                mode = "furnish"
                            else:
                                selected_style = None
                                custom_prompt = st.text_area(
                                    "Describe your staging vision",
                                    placeholder="e.g., coastal beach house with light blues and whites, "
                                               "or art deco with geometric patterns and gold accents",
                                    height=100,
                                    key="buyer_custom_prompt"
                                )
                                st.caption("💡 Tip: Be specific about furniture, colors, and decor style")
                                mode = "furnish"
                        else:
                            # Unfurnish mode
                            selected_style = None
                            custom_prompt = None
                            mode = "unfurnish"
                            st.info("🏗️ This will remove all furniture and show the empty room structure")
                        
                        # Generate button
                        if staging_action == "Add/Update Furniture":
                            can_generate = (staging_mode == "Predefined Styles") or (custom_prompt and len(custom_prompt.strip()) > 10)
                        else:
                            can_generate = True  # Always can unfurnish
                        
                        if st.button("🎨 Generate Staged Version", type="primary",
                                    use_container_width=True, disabled=not can_generate):
                            with st.spinner("AI is staging the image... (this may take 30-60s)"):
                                result = api.stage_image(
                                    image_id, 
                                    style=selected_style,
                                    custom_prompt=custom_prompt,
                                    mode=mode
                                )
                            
                            if result:
                                st.session_state["buyer_staged_result"] = result
                                st.rerun()
                    
                    # Show staged result if available
                    if "buyer_staged_result" in st.session_state:
                        st.divider()
                        result = st.session_state["buyer_staged_result"]
                        
                        rc1, rc2 = st.columns([1, 1])
                        with rc1:
                            st.markdown("**Original**")
                            try:
                                st.image(f"http://localhost:8000{result.get('original_image_url', '')}",
                                        use_container_width=True)
                            except Exception:
                                pass
                        
                        with rc2:
                            mode_display = result.get('mode', 'furnish')
                            if mode_display == "unfurnish":
                                style_display = "Empty Room"
                            elif result.get('custom_prompt'):
                                style_display = "Custom"
                            else:
                                style_display = result.get('style', '').title()
                            
                            st.markdown(f"**Staged ({style_display})**")
                            try:
                                st.image(f"http://localhost:8000{result.get('staged_image_url', '')}",
                                        use_container_width=True)
                            except Exception:
                                st.error("Staged image not available")
                        
                        if result.get('mode') == 'unfurnish':
                            st.success("🏗️ Furniture removed - showing empty room structure")
                        elif result.get('custom_prompt'):
                            st.markdown("**Your Custom Prompt:**")
                            st.info(result.get('custom_prompt'))
                        
                        st.markdown("**Changes Made:**")
                        changes = result.get("changes_made", [])
                        if changes:
                            for change in changes:
                                st.write(f"• {change}")
                        
                        st.markdown("**Preserved Elements:**")
                        preserved = result.get("preserved_elements", [])
                        if preserved:
                            for elem in preserved:
                                st.write(f"• {elem}")
                        
                        st.caption(f"⏱ Processing time: {result.get('processing_time', 0):.1f}s  ·  "
                                  f"Method: {result.get('tier', 'AI Generated')}")
                        
                        if st.button("Clear Result"):
                            st.session_state.pop("buyer_staged_result", None)
                            st.rerun()
            else:
                st.info("This property has no images available for staging.")
    else:
        st.info("No properties available. Check back later!")

# ── FAVORITES TAB ─────────────────────────────────────────────────────────────
with tab_fav:
    if not st.session_state.get("token"):
        st.info("Login to view your saved properties.")
    else:
        favs = api.get_favorites()
        if favs:
            st.caption(f"{len(favs)} saved properties")
            for f in favs:
                fc1, fc2, fc3 = st.columns([4, 1, 1])
                with fc1:
                    st.write(f"**{f.get('title', 'Untitled')}** — "
                             f"{f.get('city', '')}, {f.get('state', '')}")
                    try:
                        qs = float(f.get('overall_quality_score') or 0)
                        st.caption(f"💰 ${f.get('price', 0):,.0f}  ·  ⭐ {qs:.0f}")
                    except (TypeError, ValueError):
                        st.caption(f"💰 ${f.get('price', 0):,.0f}")
                with fc2:
                    st.caption(f.get("collection_name", "Default"))
                with fc3:
                    if st.button("Remove", key=f"rmfav_{f['id']}"):
                        api.remove_favorite(f["id"])
                        st.rerun()
        else:
            st.info("No favorites yet. Search and save properties!")

# ── HISTORY TAB ───────────────────────────────────────────────────────────────
with tab_hist:
    if not st.session_state.get("token"):
        st.info("Login to view your history.")
    else:
        hist = api.get_history()
        if hist:
            for h in hist:
                st.write(f"**{h.get('title', 'Unknown')}** — {h.get('city', '')}  "
                         f"·  💰 ${h.get('price', 0):,.0f}  "
                         f"·  🕐 {str(h.get('viewed_at', ''))[:16]}")
        else:
            st.info("No viewing history yet.")

# ── COMPARE TAB ───────────────────────────────────────────────────────────────
with tab_compare:
    st.caption("Enter up to 4 listing IDs (comma-separated) to compare side-by-side")
    ids_input = st.text_input("Listing IDs", placeholder="abc123, def456, ghi789")

    if st.button("Compare", type="primary") and ids_input:
        ids = [i.strip() for i in ids_input.split(",") if i.strip()][:4]
        if len(ids) < 2:
            st.error("Enter at least 2 IDs")
        else:
            with st.spinner("Loading comparison..."):
                cmp = api.get_comparison(ids)
            if cmp and cmp.get("listings"):
                listings = cmp["listings"]
                cols = st.columns(len(listings))
                for i, prop in enumerate(listings):
                    with cols[i]:
                        img = api.image_url(prop.get("image_url", ""))
                        if img:
                            try:
                                st.image(img, use_container_width=True)
                            except Exception:
                                pass
                        st.markdown(f"**{prop.get('title', 'Property')}**")
                        st.write(f"📍 {prop.get('city', '')}, {prop.get('state', '')}")
                        st.metric("Price", f"${prop.get('price', 0):,.0f}")
                        st.metric("Quality",
                                  f"{prop.get('overall_quality_score') or 0:.0f}/100")
                        ns = prop.get("neighborhood_score")
                        st.metric("Neighborhood",
                                  f"{ns:.0f}/100" if ns else "N/A")
                        inv = prop.get("investment")
                        if inv:
                            st.metric("Inv. Score",
                                      f"{inv.get('roi_percent', 0):.1f}% ROI")
                        st.caption(f"🛏 {prop.get('bedrooms', '?')}  "
                                   f"🚿 {prop.get('bathrooms', '?')}  "
                                   f"📐 {prop.get('square_feet', '?')} sqft")

# ── Property Detail Panel ─────────────────────────────────────────────────────
if "detail_prop" in st.session_state:
    prop = st.session_state["detail_prop"]
    lid  = prop.get("id") or prop.get("listing_id", "")
    st.divider()
    st.subheader(f"📍 {prop.get('title', 'Property Details')}")

    dc1, dc2 = st.columns([2, 1])
    with dc1:
        img = api.image_url(prop.get("image_url", ""))
        if img:
            try:
                st.image(img, use_container_width=True)
            except Exception:
                pass

        dt1, dt2, dt3 = st.tabs(["📊 AI Scores", "💰 Investment", "🏘️ Neighborhood"])
        with dt1:
            s1, s2, s3, s4 = st.columns(4)
            try:
                s1.metric("Quality",  f"{float(prop.get('overall_quality_score') or prop.get('overall_score') or 0):.0f}/100")
            except (TypeError, ValueError):
                s1.metric("Quality", "N/A")
            try:
                s2.metric("Trust",    f"{float(prop.get('trust_score') or 0):.0f}/100")
            except (TypeError, ValueError):
                s2.metric("Trust", "N/A")
            try:
                s3.metric("Access.",  f"{float(prop.get('accessibility_score') or 0):.0f}/100")
            except (TypeError, ValueError):
                s3.metric("Access.", "N/A")
            s4.metric("Verified", "✅" if prop.get("authenticity_verified") else "⚠️")
        with dt2:
            if lid:
                with st.spinner("Loading investment data..."):
                    inv = api.get_investment(lid)
                render_investment_chart(inv)
            else:
                st.info("Investment data requires a listing ID.")
        with dt3:
            if lid:
                with st.spinner("Loading neighborhood data..."):
                    ns = api.get_neighborhood_score(lid)
                if ns:
                    nc1, nc2 = st.columns(2)
                    nc1.metric("Overall",    f"{ns.get('overall_score', 0):.0f}/100")
                    nc1.metric("Walkability",
                               f"{ns['breakdown']['walkability']['score']:.0f}/100")
                    nc2.metric("Transit",
                               f"{ns['breakdown']['transit']['score']:.0f}/100")
                    nc2.metric("Safety",
                               f"{ns['breakdown']['safety']['score']:.0f}/100")
                    st.caption(ns.get("noise_level", ""))
                    for h in ns.get("neighborhood_highlights", []):
                        st.write(h)
            else:
                st.info("Neighborhood data requires a listing ID.")

    with dc2:
        st.markdown(f"### {prop.get('title', 'Property')}")
        st.write(f"📍 {prop.get('city', '')}, {prop.get('state', '')}")
        try:
            price = float(prop.get("price") or 0)
            if price:
                st.markdown(f"## ${price:,.0f}")
        except (TypeError, ValueError):
            pass
        try:
            beds  = prop.get('bedrooms', '?')
            baths = prop.get('bathrooms', '?')
            sqft  = prop.get('square_feet', '?')
            sqft_str = f"{int(float(sqft)):,}" if sqft and sqft != '?' else '?'
        except (TypeError, ValueError):
            beds, baths, sqft_str = '?', '?', '?'
        st.write(f"🛏 {beds} beds  ·  🚿 {baths} baths  ·  📐 {sqft_str} sqft")
        ptype_val = prop.get("property_type", "")
        if ptype_val:
            st.caption(f"Type: {ptype_val.title()}")

        st.markdown("---")
        if st.session_state.get("token") and lid:
            if st.button("❤️ Save to Favorites", use_container_width=True):
                api.add_favorite(lid)
                st.toast("Saved to favorites!")

            with st.expander("📞 Contact Seller"):
                subj = st.text_input("Subject", "Interested in your property")
                msg  = st.text_area("Message", "Hi, I'm interested in this property...")
                if st.button("Send Message"):
                    r = api.contact_seller(lid, subj, msg)
                    if r:
                        st.success("Message sent!")

        if st.button("❌ Close", use_container_width=True):
            st.session_state.pop("detail_prop", None)
            st.rerun()
