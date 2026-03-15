"""Seller Dashboard — Upload & Validate, Listings, Analytics, Messages."""
import streamlit as st
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import utils.api_client as api
from utils.styling import inject_css
from components.validation_card import render_validation_card

st.set_page_config(page_title="Seller Dashboard", page_icon="🏠", layout="wide")
inject_css()

# ── Header ────────────────────────────────────────────────────────────────────
hc1, hc2 = st.columns([4, 1])
with hc1:
    st.title("🏠 Seller Dashboard")
with hc2:
    if st.session_state.get("token"):
        st.caption(f"👤 {st.session_state.get('name')}")
        if st.button("Logout", key="seller_logout"):
            api.logout()
    else:
        if st.button("Login"):
            st.switch_page("pages/4_Auth.py")

if not st.session_state.get("token"):
    st.warning("Please login to access the Seller Dashboard.")
    if st.button("Go to Login", type="primary"):
        st.switch_page("pages/4_Auth.py")
    st.stop()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab_upload, tab_analyze, tab_listings, tab_new, tab_staging, tab_analytics, tab_messages = st.tabs(
    ["📤 Upload & Validate", "🔍 Analyze Images", "📋 My Listings", "➕ New Listing",
     "🎨 Virtual Staging", "📊 Analytics", "✉️ Messages"])

# ── UPLOAD & VALIDATE ─────────────────────────────────────────────────────────
with tab_upload:
    st.markdown("### Upload Property Photos for AI Validation")
    st.caption("Images are validated by AI then attached directly to your chosen listing.")

    # Pick listing first
    all_listings = api.get_my_listings()
    listing_options = {"— Create listing first —": None}
    if all_listings:
        listing_options = {f"{l['title']} ({l['id'][:8]}…)": l["id"]
                           for l in all_listings}

    uc1, uc2 = st.columns([3, 1])
    with uc1:
        selected_label = st.selectbox("Attach images to listing", list(listing_options.keys()))
        target_lid = listing_options[selected_label]
    with uc2:
        expected_room = st.selectbox(
            "Expected room",
            ["(auto-detect)", "kitchen", "bedroom", "bathroom",
             "living_room", "dining_room", "home_office", "exterior"])

    if not target_lid:
        st.warning("Create a listing first in the ➕ New Listing tab, then come back here.")

    uploaded_files = st.file_uploader(
        "Choose property images",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="seller_uploader",
    )

    if uploaded_files:
        st.success(f"✅ {len(uploaded_files)} file(s) ready")
        thumb_cols = st.columns(min(5, len(uploaded_files)))
        for i, f in enumerate(uploaded_files[:5]):
            with thumb_cols[i]:
                st.image(f, caption=f.name[:20], use_container_width=True)
        if len(uploaded_files) > 5:
            st.caption(f"...and {len(uploaded_files) - 5} more")

        if st.button("🤖 Validate & Attach to Listing", type="primary",
                     disabled=not target_lid):
            room_arg = None if expected_room == "(auto-detect)" else expected_room
            passed, failed = [], []

            for f in uploaded_files:
                with st.spinner(f"Analysing {f.name}..."):
                    result = api.validate_upload(f, expected_room=room_arg)

                if result:
                    render_validation_card(result, file_bytes=f.getvalue())

                    # Auto-enhance if needed
                    iid = result.get("temp_image_id", "")
                    if result.get("auto_enhance_available") and iid:
                        if st.button(f"✨ Auto-Enhance {f.name}", key=f"enh_{iid}"):
                            with st.spinner("Enhancing..."):
                                enh = api.enhance_upload(iid)
                            if enh:
                                st.success("Enhanced!")

                    # Track for attachment
                    quality = result.get("overall_quality", 0)
                    is_fake = result.get("is_ai_generated", False)
                    if is_fake:
                        failed.append(f.name)
                    else:
                        passed.append(f)

            # Attach all passed images to the listing in one call
            if passed and target_lid:
                with st.spinner(f"Uploading {len(passed)} real image(s) to listing..."):
                    r = api.upload_listing_images(target_lid, passed)
                
                if r:
                    accepted = r.get("accepted_count", 0)
                    rejected_list = r.get("rejected_images", [])
                    
                    if accepted > 0:
                        avg_q = r.get("avg_quality_score")
                        msg = f"✅ {accepted} REAL image(s) uploaded to **{selected_label}**"
                        if avg_q is not None:
                            msg += f"  ·  Quality score: **{avg_q:.0f}/100**"
                        st.success(msg)
                    
                    if rejected_list:
                        st.error(f"🚫 {len(rejected_list)} AI-generated image(s) REJECTED:")
                        for rej in rejected_list:
                            st.warning(f"   • {rej['filename']} - {rej['reason']} ({rej['ai_probability']:.0f}% AI)")
                    
                    if accepted > 0:
                        st.rerun()  # refresh My Listings tab to show updated score
                else:
                    st.error("Upload failed — check backend logs")

            if failed:
                st.info(f"ℹ️ {len(failed)} image(s) detected as AI-generated during validation: "
                        f"{', '.join(failed)}")

# ── ANALYZE IMAGES ────────────────────────────────────────────────────────────
with tab_analyze:
    st.markdown("### 🔍 Analyze & Review Images")
    st.caption("Review AI detection results for all uploaded images and accept/reject them")
    
    # Get all listings
    all_listings = api.get_my_listings()
    if not all_listings:
        st.info("No listings yet. Create a listing first.")
    else:
        # Select listing
        listing_opts = {f"{l['title']} ({l['id'][:8]}…)": l["id"] for l in all_listings}
        selected_label = st.selectbox("Select listing to analyze", 
                                      list(listing_opts.keys()),
                                      key="analyze_listing")
        selected_lid = listing_opts[selected_label]
        
        # Get analysis data
        with st.spinner("Loading analysis..."):
            analysis_data = api.get_listing_analysis(selected_lid)
        
        if analysis_data and analysis_data.get("analyses"):
            analyses = analysis_data["analyses"]
            st.success(f"Found {len(analyses)} image(s) with analysis data")
            
            # Show each image with analysis
            for idx, item in enumerate(analyses):
                img = item.get("image", {})
                analysis = item.get("analysis", {})
                
                if not analysis:
                    continue
                
                st.divider()
                
                # Create columns for image and analysis
                col1, col2 = st.columns([1, 2])
                
                with col1:
                    # Display image
                    img_url = img.get("image_url")
                    if img_url:
                        try:
                            st.image(f"http://localhost:8000{img_url}",
                                   caption=img.get("original_filename", "Image"),
                                   use_container_width=True)
                        except Exception:
                            st.error("Could not load image")
                
                with col2:
                    st.markdown(f"**{img.get('original_filename', 'Image')}**")
                    
                    # AI Detection Results
                    is_ai = analysis.get("is_ai_generated") == 1
                    ai_prob = analysis.get("ai_probability", 0)
                    trust_score = analysis.get("trust_score", 0)
                    
                    # Only show confidence if >= 70%
                    confidence_threshold = 70
                    show_confidence = max(ai_prob, 100 - ai_prob) >= confidence_threshold
                    
                    if is_ai:
                        st.error(f"⚠️ AI-GENERATED DETECTED")
                        if show_confidence:
                            st.metric("AI Probability", f"{ai_prob:.1f}%")
                    else:
                        st.success(f"✅ AUTHENTIC IMAGE")
                        if show_confidence:
                            st.metric("Trust Score", f"{trust_score:.1f}/100")
                    
                    # Quality metrics
                    mc1, mc2, mc3, mc4 = st.columns(4)
                    with mc1:
                        overall_q = analysis.get("overall_quality_score", 0)
                        st.metric("Quality", f"{overall_q:.0f}/100")
                    with mc2:
                        lighting = analysis.get("lighting_quality_score", 0)
                        st.metric("Lighting", f"{lighting:.0f}/100")
                    with mc3:
                        clutter = analysis.get("clutter_score", 0)
                        st.metric("Clutter", f"{clutter:.0f}/100")
                    with mc4:
                        room = analysis.get("room_type", "unknown")
                        st.metric("Room", room.replace("_", " ").title())
                    
                    # Recommendations
                    recs = analysis.get("recommendations")
                    if recs:
                        try:
                            import json
                            recs_list = json.loads(recs) if isinstance(recs, str) else recs
                            if recs_list:
                                with st.expander("📋 Recommendations"):
                                    for rec in recs_list[:3]:
                                        priority = rec.get("priority", "medium")
                                        icon = "🔴" if priority == "high" else "🟡" if priority == "medium" else "🟢"
                                        st.write(f"{icon} {rec.get('action', '')}")
                        except Exception:
                            pass
                    
                    # Accept/Reject buttons
                    st.markdown("---")
                    btn_col1, btn_col2 = st.columns(2)
                    
                    with btn_col1:
                        if st.button("✅ Accept & Keep", 
                                   key=f"accept_{img['id']}",
                                   type="primary" if not is_ai else "secondary",
                                   use_container_width=True):
                            # Image is already in listing, just show confirmation
                            st.success("Image accepted and kept in listing")
                            st.rerun()
                    
                    with btn_col2:
                        if st.button("❌ Reject & Remove", 
                                   key=f"reject_{img['id']}",
                                   type="primary" if is_ai else "secondary",
                                   use_container_width=True):
                            # Delete the image
                            with st.spinner("Removing image..."):
                                # Call delete image endpoint
                                result = api.delete_listing_image(selected_lid, img['id'])
                            if result:
                                st.success("Image removed from listing")
                                st.rerun()
                            else:
                                st.error("Failed to remove image")
        else:
            st.info("No images with analysis data found. Upload images in the 📤 Upload & Validate tab first.")

# ── MY LISTINGS ───────────────────────────────────────────────────────────────
with tab_listings:
    listings = api.get_my_listings()
    if listings:
        st.caption(f"{len(listings)} listing(s)")
        for l in listings:
            icon = "🟢" if l["status"] == "published" else "🟡"
            with st.expander(
                    f"{icon} {l['title']} — ${l.get('price', 0):,.0f}  [{l['status']}]"):
                lc1, lc2, lc3, lc4 = st.columns([3, 1, 1, 1])
                with lc1:
                    st.write(f"📍 {l.get('city', '')}, {l.get('state', '')}")
                    st.caption(f"Type: {l.get('property_type','—')}  "
                               f"Beds: {l.get('bedrooms','—')}  "
                               f"Baths: {l.get('bathrooms','—')}  "
                               f"Sqft: {l.get('square_feet','—')}")
                    
                    # Show primary image if available
                    img_url = l.get("primary_image_url")
                    if img_url:
                        try:
                            st.image(f"http://localhost:8000{img_url}",
                                     width=200, caption="Primary photo")
                        except Exception:
                            pass
                    
                    # Show AI detection status for all images
                    try:
                        analysis_data = api.get_listing_analysis(l["id"])
                        if analysis_data and analysis_data.get("analyses"):
                            st.markdown("**📸 Images:**")
                            for item in analysis_data["analyses"]:
                                img = item.get("image", {})
                                analysis = item.get("analysis", {})
                                if analysis:
                                    is_ai = analysis.get("is_ai_generated") == 1
                                    ai_prob = analysis.get("ai_probability", 0)
                                    filename = img.get("original_filename", "Image")[:30]
                                    
                                    # Only show confidence if >= 70%
                                    show_confidence = max(ai_prob, 100 - ai_prob) >= 70
                                    
                                    if is_ai:
                                        if show_confidence:
                                            st.caption(f"🤖 {filename} - AI Generated ({ai_prob:.0f}%)")
                                        else:
                                            st.caption(f"❓ {filename} - Uncertain")
                                    else:
                                        if show_confidence:
                                            st.caption(f"✅ {filename} - Real ({100-ai_prob:.0f}%)")
                                        else:
                                            st.caption(f"❓ {filename} - Uncertain")
                    except Exception as e:
                        # Silently fail if analysis not available
                        pass
                
                with lc2:
                    qs = l.get("overall_quality_score")
                    try:
                        st.metric("Quality", f"{float(qs):.0f}/100" if qs is not None else "N/A")
                    except (TypeError, ValueError):
                        st.metric("Quality", "N/A")
                with lc3:
                    if l["status"] != "published":
                        if st.button("Publish", key=f"pub_{l['id']}"):
                            api.publish_listing(l["id"])
                            st.rerun()
                with lc4:
                    if st.button("Delete", key=f"del_{l['id']}"):
                        api.delete_listing(l["id"])
                        st.rerun()

                st.divider()
                # Inline edit form
                with st.form(key=f"edit_{l['id']}"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        new_title = st.text_input("Title", l.get("title", ""),
                                                  key=f"et_{l['id']}")
                        new_price = st.number_input("Price", value=float(l.get("price", 0)),
                                                    key=f"ep_{l['id']}")
                        new_city  = st.text_input("City", l.get("city", ""),
                                                  key=f"ec_{l['id']}")
                        new_state = st.text_input("State", l.get("state", ""),
                                                  key=f"es_{l['id']}")
                    with ec2:
                        new_beds  = st.number_input("Bedrooms",
                                                    value=int(l.get("bedrooms") or 0),
                                                    key=f"eb_{l['id']}")
                        new_baths = st.number_input("Bathrooms",
                                                    value=float(l.get("bathrooms") or 0),
                                                    step=0.5, key=f"eba_{l['id']}")
                        new_sqft  = st.number_input("Sq Ft",
                                                    value=int(l.get("square_feet") or 0),
                                                    key=f"esq_{l['id']}")
                        types = ["house", "apartment", "condo", "townhouse", "land"]
                        cur   = l.get("property_type", "house")
                        new_type = st.selectbox("Type", types,
                                                index=types.index(cur) if cur in types else 0,
                                                key=f"ety_{l['id']}")
                    new_desc = st.text_area("Description", l.get("description", ""),
                                            key=f"ed_{l['id']}")
                    if st.form_submit_button("💾 Save Changes"):
                        res = api.update_listing(l["id"], {
                            "title": new_title, "description": new_desc,
                            "city": new_city, "state": new_state,
                            "price": new_price, "property_type": new_type,
                            "bedrooms": int(new_beds), "bathrooms": float(new_baths),
                            "square_feet": int(new_sqft),
                        })
                        if res:
                            st.success("Updated!")
                            st.rerun()

                # Investment analysis
                st.markdown("**💰 Investment Analysis**")
                if st.button("Load Investment Data", key=f"inv_{l['id']}"):
                    if not l.get("price") or l.get("price", 0) == 0:
                        st.warning("Set a price for this listing to get investment analysis.")
                    else:
                        with st.spinner("Loading..."):
                            inv = api.seller_investment(l["id"])
                        if inv:
                            from components.investment_chart import render_investment_chart
                            render_investment_chart(inv)
                            if not l.get("square_feet"):
                                st.caption("💡 Add square footage for price/sqft comparison")
    else:
        st.info("No listings yet. Create one in the ➕ New Listing tab.")

# ── NEW LISTING ───────────────────────────────────────────────────────────────
with tab_new:
    st.markdown("### Create New Listing")

    # ── Step 1: upload photos for AI pre-fill ────────────────────────────────
    st.markdown("**Step 1 — Upload photos (optional) to auto-fill fields from AI**")
    prefill_files = st.file_uploader(
        "Upload property photos for AI analysis",
        type=["jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        key="prefill_uploader",
    )

    if prefill_files:
        if st.button("🤖 Analyse & Pre-fill", type="primary"):
            with st.spinner("Running AI analysis on your images..."):
                info = api.extract_listing_info(prefill_files)
            if info:
                st.session_state["prefill"] = info
                rooms = info.get("detected_rooms", {})
                st.success(
                    f"Detected: {', '.join(f'{v}× {k}' for k,v in rooms.items() if k != 'unknown') or 'rooms'}"
                    f"  ·  Style: {info.get('style','—')}"
                    f"  ·  Type: {info.get('property_type','—')}"
                )

    pf = st.session_state.get("prefill", {})
    if pf:
        st.info("✅ Fields pre-filled from AI — review and adjust before saving.")

    st.divider()
    st.markdown("**Step 2 — Review and complete the listing details**")

    # ── Form with AI-prefilled defaults ──────────────────────────────────────
    types = ["house", "apartment", "condo", "townhouse", "land"]
    pf_type = pf.get("property_type", "house")
    pf_type_idx = types.index(pf_type) if pf_type in types else 0

    with st.form("new_listing_form"):
        nc1, nc2 = st.columns(2)
        with nc1:
            title   = st.text_input("Title *", placeholder="Modern 3BR in Downtown")
            price   = st.number_input("Price ($) *", min_value=0.0, step=1000.0)
            address = st.text_input("Address")
            city    = st.text_input("City")
            state   = st.text_input("State")
            zipcode = st.text_input("ZIP Code")
        with nc2:
            ptype = st.selectbox("Property Type", types, index=pf_type_idx)
            beds  = st.number_input("Bedrooms",  min_value=0, max_value=20,
                                    value=int(pf.get("bedrooms") or 0))
            baths = st.number_input("Bathrooms", min_value=0.0, max_value=20.0,
                                    step=0.5,
                                    value=float(pf.get("bathrooms") or 0))
            sqft  = st.number_input("Square Feet", min_value=0)
            year  = st.number_input("Year Built", min_value=1800, max_value=2026,
                                    value=2000)
        desc = st.text_area("Description", value=pf.get("description", ""),
                            height=100,
                            help="Auto-generated from AI — edit as needed")

        if st.form_submit_button("✅ Create Listing", type="primary"):
            if not title:
                st.error("Title is required")
            else:
                res = api.create_listing({
                    "title": title, "description": desc, "address": address,
                    "city": city, "state": state, "zip_code": zipcode,
                    "price": price, "property_type": ptype,
                    "bedrooms": int(beds), "bathrooms": float(baths),
                    "square_feet": int(sqft), "year_built": int(year),
                })
                if res:
                    st.success(f"Listing created! ID: `{res.get('listing_id', '')}`")
                    st.session_state.pop("prefill", None)
                    st.info("Go to 📋 My Listings to upload images and publish.")

# ── VIRTUAL STAGING ──────────────────────────────────────────────────────────
with tab_staging:
    st.markdown("### 🎨 Virtual Staging")
    st.caption("Transform your property photos with AI-powered virtual staging")
    
    # Get seller's listings with images
    listings = api.get_my_listings()
    if not listings:
        st.info("Create a listing and upload images first to use virtual staging.")
    else:
        # Select listing
        listing_opts = {f"{l['title']} ({l['id'][:8]}…)": l["id"] for l in listings}
        selected_label = st.selectbox("Select listing", list(listing_opts.keys()),
                                      key="staging_listing")
        selected_lid = listing_opts[selected_label]
        
        # Get listing details with images
        listing_detail = api.get_listing_detail(selected_lid)
        if listing_detail and listing_detail.get("images"):
            images = listing_detail["images"]
            
            # Select image to stage
            img_opts = {f"Image {i+1} ({img['original_filename'][:30]})": img 
                       for i, img in enumerate(images)}
            selected_img_label = st.selectbox("Select image to stage", 
                                             list(img_opts.keys()),
                                             key="staging_image")
            selected_img = img_opts[selected_img_label]
            
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
                    key="seller_staging_action",
                    horizontal=True
                )
                
                if staging_action == "Add/Update Furniture":
                    # Mode selector: Predefined styles or Custom prompt
                    staging_mode = st.radio(
                        "Choose mode",
                        ["Predefined Styles", "Custom Prompt"],
                        key="seller_staging_mode",
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
                                                     key="staging_style")
                        custom_prompt = None
                        mode = "furnish"
                    else:
                        selected_style = None
                        custom_prompt = st.text_area(
                            "Describe your staging vision",
                            placeholder="e.g., bohemian style with plants and colorful textiles, "
                                       "or minimalist Japanese zen with natural materials",
                            height=100,
                            key="seller_custom_prompt"
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
                    with st.spinner("AI is staging your image... (this may take 30-60s)"):
                        result = api.stage_image(
                            selected_img["id"], 
                            style=selected_style,
                            custom_prompt=custom_prompt,
                            mode=mode
                        )
                    
                    if result:
                        st.session_state["staged_result"] = result
                        st.rerun()
            
            # Show staged result if available
            if "staged_result" in st.session_state:
                st.divider()
                result = st.session_state["staged_result"]
                
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
                
                if st.button("Clear Result"):
                    st.session_state.pop("staged_result", None)
                    st.rerun()
        else:
            st.info("This listing has no images. Upload images first in the 📤 Upload & Validate tab.")

# ── ANALYTICS ─────────────────────────────────────────────────────────────────
with tab_analytics:
    data = api.seller_analytics()
    if data:
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Total Listings", data.get("total_listings", 0))
        k2.metric("Published",      data.get("published", 0))
        k3.metric("Total Views",    data.get("total_views", 0))
        k4.metric("Total Saves",    data.get("total_saves", 0))
        k5.metric("Contacts",       data.get("total_contacts", 0))

        st.divider()
        listings = data.get("listings", [])
        if listings:
            st.markdown("#### Per-Listing Performance")
            for l in listings:
                ac1, ac2, ac3 = st.columns([4, 1, 1])
                with ac1:
                    st.write(f"**{l['title']}**  —  {l['status']}  —  "
                             f"${l.get('price', 0):,.0f}")
                with ac2:
                    qs = l.get("overall_quality_score")
                    try:
                        st.metric("Quality", f"{float(qs):.0f}/100" if qs is not None else "N/A")
                    except (TypeError, ValueError):
                        st.metric("Quality", "N/A")
                with ac3:
                    st.metric("Views", l.get("views", 0))
    else:
        st.info("No analytics data yet.")

# ── MESSAGES ──────────────────────────────────────────────────────────────────
with tab_messages:
    data = api.seller_messages()
    if data:
        unread = data.get("unread", 0)
        if unread:
            st.warning(f"📬 {unread} unread message(s)")
        else:
            st.success("✅ All messages read")

        msgs = data.get("messages", [])
        if msgs:
            for m in msgs:
                is_unread = m.get("status") == "sent"
                with st.expander(
                        f"{'📩' if is_unread else '📧'} "
                        f"**{m.get('subject', '(no subject)')}** "
                        f"— from {m.get('sender_name', 'Unknown')}"):
                    st.caption(f"Listing: {m.get('listing_title', '—')}  ·  "
                               f"{str(m.get('created_at', ''))[:16]}")
                    st.write(m.get("message", ""))
                    with st.form(key=f"reply_{m['id']}"):
                        reply_text = st.text_area("Reply", key=f"rt_{m['id']}")
                        if st.form_submit_button("Send Reply"):
                            res = api.reply_message(m["id"], reply_text)
                            if res:
                                st.success("Reply sent!")
                                st.rerun()
        else:
            st.info("No messages yet.")
    else:
        st.info("No messages yet.")
