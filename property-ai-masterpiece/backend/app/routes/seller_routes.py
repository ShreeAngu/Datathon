"""Seller routes — listings CRUD, image upload, analytics, messages."""

import uuid, json, shutil, pathlib
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from pydantic import BaseModel
from typing import Optional

from app.database.connection import fetchall, fetchone, execute
from app.auth.auth import get_current_user

router = APIRouter()

UPLOADS = Path("dataset/uploads")
UPLOADS.mkdir(parents=True, exist_ok=True)


# ── Helper Functions ──────────────────────────────────────────────────────────

def _generate_keywords(description: str) -> list:
    """Extract keywords from description using simple NLP."""
    if not description:
        return []
    
    # Common stop words to filter out
    stop_words = {
        'a', 'an', 'and', 'are', 'as', 'at', 'be', 'by', 'for', 'from', 'has', 'he',
        'in', 'is', 'it', 'its', 'of', 'on', 'that', 'the', 'to', 'was', 'will', 'with',
        'this', 'but', 'they', 'have', 'had', 'what', 'when', 'where', 'who', 'which',
        'their', 'been', 'were', 'said', 'can', 'all', 'would', 'there', 'more', 'if',
        'no', 'out', 'so', 'up', 'or', 'just', 'about', 'into', 'than', 'them', 'some',
        'could', 'other', 'then', 'now', 'only', 'may', 'also', 'over', 'such', 'our',
        'very', 'any', 'these', 'most', 'your', 'his', 'her', 'my', 'me', 'we', 'us'
    }
    
    # Property-specific keywords to prioritize
    property_keywords = {
        'modern', 'luxury', 'spacious', 'updated', 'renovated', 'new', 'beautiful',
        'stunning', 'elegant', 'contemporary', 'traditional', 'classic', 'charming',
        'cozy', 'bright', 'open', 'large', 'private', 'quiet', 'convenient', 'prime',
        'kitchen', 'bedroom', 'bathroom', 'living', 'dining', 'garage', 'yard', 'garden',
        'pool', 'deck', 'patio', 'balcony', 'fireplace', 'hardwood', 'granite', 'marble',
        'stainless', 'appliances', 'downtown', 'waterfront', 'view', 'location', 'neighborhood',
        'school', 'park', 'shopping', 'transit', 'walkable', 'accessible', 'furnished',
        'unfurnished', 'pet-friendly', 'parking', 'storage', 'laundry', 'utilities'
    }
    
    # Clean and tokenize
    import re
    text = description.lower()
    text = re.sub(r'[^\w\s-]', ' ', text)  # Remove punctuation except hyphens
    words = text.split()
    
    # Extract keywords
    keywords = []
    word_freq = {}
    
    for word in words:
        word = word.strip('-')
        if len(word) < 3:  # Skip very short words
            continue
        if word in stop_words:
            continue
        
        # Count frequency
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Prioritize property-specific keywords
    for word in property_keywords:
        if word in word_freq:
            keywords.append(word)
    
    # Add other frequent words (appearing 2+ times)
    for word, freq in sorted(word_freq.items(), key=lambda x: x[1], reverse=True):
        if word not in keywords and freq >= 2:
            keywords.append(word)
        if len(keywords) >= 20:  # Limit to 20 keywords
            break
    
    # Add remaining single-occurrence words if we have space
    for word in word_freq:
        if word not in keywords and len(word) > 4:  # Only longer words
            keywords.append(word)
        if len(keywords) >= 30:  # Max 30 keywords
            break
    
    return keywords[:30]  # Return top 30 keywords


# ── Listing CRUD ──────────────────────────────────────────────────────────────

class ListingBody(BaseModel):
    title: str
    description: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    price: float = 0
    property_type: str = "house"
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_feet: Optional[int] = None
    year_built: Optional[int] = None


@router.post("/listings")
def create_listing(body: ListingBody, current=Depends(get_current_user)):
    lid = str(uuid.uuid4()).replace("-", "")
    
    # Generate keywords from description
    keywords = _generate_keywords(body.description or "")
    
    execute(
        """INSERT INTO listings(id,seller_id,title,description,address,city,state,
           zip_code,price,property_type,bedrooms,bathrooms,square_feet,year_built)
           VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (lid, current["sub"], body.title, body.description, body.address,
         body.city, body.state, body.zip_code, body.price, body.property_type,
         body.bedrooms, body.bathrooms, body.square_feet, body.year_built),
    )
    
    return {"status": "created", "listing_id": lid, "keywords": keywords}


@router.get("/listings")
def list_my_listings(current=Depends(get_current_user)):
    rows = fetchall(
        "SELECT * FROM listings WHERE seller_id=? ORDER BY created_at DESC",
        (current["sub"],),
    )
    for row in rows:
        primary = fetchone(
            "SELECT image_path FROM images WHERE listing_id=? AND is_primary=1 LIMIT 1",
            (row["id"],),
        )
        if primary:
            fname = pathlib.Path(primary["image_path"]).name
            row["primary_image_url"] = f"/images/uploads/{fname}"
        else:
            row["primary_image_url"] = None
    return {"listings": rows, "count": len(rows)}


@router.get("/listings/{lid}")
def get_listing(lid: str, current=Depends(get_current_user)):
    row = fetchone("SELECT * FROM listings WHERE id=? AND seller_id=?",
                   (lid, current["sub"]))
    if not row:
        raise HTTPException(404, "Listing not found")
    images = fetchall("SELECT * FROM images WHERE listing_id=? ORDER BY upload_order",
                      (lid,))
    for img in images:
        fname = pathlib.Path(img["image_path"]).name
        img["image_url"] = f"/images/uploads/{fname}"
    row["images"] = images
    return row


@router.put("/listings/{lid}")
def update_listing(lid: str, body: ListingBody, current=Depends(get_current_user)):
    row = fetchone("SELECT id FROM listings WHERE id=? AND seller_id=?",
                   (lid, current["sub"]))
    if not row:
        raise HTTPException(404, "Listing not found")
    execute(
        """UPDATE listings SET title=?,description=?,address=?,city=?,state=?,
           zip_code=?,price=?,property_type=?,bedrooms=?,bathrooms=?,
           square_feet=?,year_built=? WHERE id=?""",
        (body.title, body.description, body.address, body.city, body.state,
         body.zip_code, body.price, body.property_type, body.bedrooms,
         body.bathrooms, body.square_feet, body.year_built, lid),
    )
    return {"status": "updated"}


@router.delete("/listings/{lid}")
def delete_listing(lid: str, current=Depends(get_current_user)):
    execute("DELETE FROM listings WHERE id=? AND seller_id=?", (lid, current["sub"]))
    return {"status": "deleted"}


@router.post("/listings/{lid}/publish")
def publish_listing(lid: str, current=Depends(get_current_user)):
    execute(
        "UPDATE listings SET status='published', published_at=CURRENT_TIMESTAMP WHERE id=? AND seller_id=?",
        (lid, current["sub"]),
    )
    return {"status": "published"}


# ── Image Upload ──────────────────────────────────────────────────────────────

@router.post("/listings/{lid}/images")
async def upload_images(lid: str, files: list[UploadFile] = File(...),
                        current=Depends(get_current_user)):
    if not fetchone("SELECT id FROM listings WHERE id=? AND seller_id=?",
                    (lid, current["sub"])):
        raise HTTPException(404, "Listing not found")

    from app.services.image_validator import get_image_validator
    validator = get_image_validator()

    saved = []
    rejected = []
    validation_results = []  # Store full validation results for each image

    for i, f in enumerate(files):
        iid  = str(uuid.uuid4()).replace("-", "")
        dest = UPLOADS / f"{iid}_{f.filename}"
        with open(dest, "wb") as buf:
            buf.write(await f.read())

        stored_path = dest.name

        # Run SAME validation as /upload/validate endpoint
        try:
            # Use exact same validation logic
            v = validator.validate_upload(str(dest), listing_id=lid)
            
            # Store validation result
            validation_results.append({
                "filename": f.filename,
                "validation": v
            })
            
            is_ai = v.get("is_ai_generated", False)
            ai_prob = v.get("ai_probability", 0)
            overall_quality = v.get("overall_quality", 0)
            
            # Only accept REAL images (not AI-generated)
            if is_ai:
                # Reject AI-generated image
                rejected.append({
                    "filename": f.filename,
                    "reason": "AI-generated image detected",
                    "ai_probability": ai_prob,
                    "real_probability": v.get("real_probability", 0),
                    "trust_score": 100 - ai_prob,
                    "overall_quality": overall_quality
                })
                # Delete the uploaded file
                try:
                    dest.unlink()
                except Exception:
                    pass
                continue  # Skip this image
            
            # Image is REAL - proceed with upload
            # Insert image record first (needed for foreign key)
            execute(
                "INSERT INTO images(id,listing_id,image_path,original_filename,upload_order,is_primary) VALUES(?,?,?,?,?,?)",
                (iid, lid, stored_path, f.filename, len(saved), 1 if len(saved) == 0 else 0),
            )

            # Save analysis data
            analysis_id = str(uuid.uuid4()).replace("-", "")
            execute(
                """INSERT OR IGNORE INTO image_analysis
                   (id, image_id, room_type, style_category, lighting_quality_score,
                    clutter_score, trust_score, is_ai_generated, ai_probability,
                    overall_quality_score, recommendations)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (analysis_id, iid,
                 v.get("verified_room_type"),
                 None,
                 v.get("lighting_score"),
                 v.get("clutter_score"),
                 100 - ai_prob,
                 0,  # is_ai_generated = 0 (real image)
                 ai_prob,
                 overall_quality,
                 json.dumps(v.get("recommendations", []))),
            )
            
            saved.append({
                "id": iid,
                "filename": f.filename,
                "image_url": f"/images/uploads/{stored_path}",
                "overall_quality": overall_quality,
                "room_type": v.get("verified_room_type"),
                "is_ai_generated": False,
                "ai_probability": ai_prob
            })
            
        except Exception as e:
            print(f"⚠️  Image validation failed for {f.filename}: {e}")
            # Delete the uploaded file on error
            try:
                dest.unlink()
            except Exception:
                pass
            rejected.append({
                "filename": f.filename,
                "reason": f"Validation error: {str(e)}",
                "ai_probability": 0
            })

    # Update listing overall_quality_score = average of all accepted images
    if saved:
        avg_quality = round(sum(img["overall_quality"] for img in saved) / len(saved), 1)
        # All accepted images are real (we rejected AI ones)
        execute(
            """UPDATE listings SET overall_quality_score=?,
               authenticity_verified=? WHERE id=?""",
            (avg_quality, 1, lid),
        )
    else:
        # No images accepted
        avg_quality = None

    response = {
        "status": "uploaded",
        "accepted_count": len(saved),
        "rejected_count": len(rejected),
        "images": saved,
        "rejected_images": rejected,
        "validation_results": validation_results,  # Include full validation data
        "avg_quality_score": avg_quality
    }
    
    return response


@router.delete("/listings/{lid}/images/{image_id}")
def delete_listing_image(lid: str, image_id: str, current=Depends(get_current_user)):
    """Delete an image from a listing and recalculate quality score."""
    if not fetchone("SELECT id FROM listings WHERE id=? AND seller_id=?",
                    (lid, current["sub"])):
        raise HTTPException(404, "Listing not found")
    
    # Get image info
    img = fetchone("SELECT * FROM images WHERE id=? AND listing_id=?", (image_id, lid))
    if not img:
        raise HTTPException(404, "Image not found")
    
    # Delete image file
    try:
        img_path = UPLOADS / img["image_path"]
        if img_path.exists():
            img_path.unlink()
    except Exception as e:
        print(f"⚠️  Failed to delete image file: {e}")
    
    # Delete from database
    execute("DELETE FROM image_analysis WHERE image_id=?", (image_id,))
    execute("DELETE FROM images WHERE id=?", (image_id,))
    
    # Recalculate listing quality score
    remaining_analyses = fetchall(
        """SELECT ia.overall_quality_score, ia.is_ai_generated
           FROM image_analysis ia
           JOIN images i ON ia.image_id = i.id
           WHERE i.listing_id=?""",
        (lid,)
    )
    
    if remaining_analyses:
        avg_quality = sum(a["overall_quality_score"] or 0 for a in remaining_analyses) / len(remaining_analyses)
        all_authentic = not any(a["is_ai_generated"] == 1 for a in remaining_analyses)
        execute(
            """UPDATE listings SET overall_quality_score=?,
               authenticity_verified=? WHERE id=?""",
            (round(avg_quality, 1), 1 if all_authentic else 0, lid),
        )
    else:
        # No images left, reset scores
        execute(
            """UPDATE listings SET overall_quality_score=NULL,
               authenticity_verified=0 WHERE id=?""",
            (lid,)
        )
    
    return {"status": "deleted", "image_id": image_id}


# ── AI Analysis for a Listing ─────────────────────────────────────────────────

@router.get("/listings/{lid}/analysis")
def listing_analysis(lid: str, current=Depends(get_current_user)):
    if not fetchone("SELECT id FROM listings WHERE id=? AND seller_id=?",
                    (lid, current["sub"])):
        raise HTTPException(404, "Listing not found")
    images = fetchall("SELECT * FROM images WHERE listing_id=?", (lid,))
    results = []
    for img in images:
        a = fetchone("SELECT * FROM image_analysis WHERE image_id=?", (img["id"],))
        results.append({"image": img, "analysis": a})
    return {"listing_id": lid, "image_count": len(images), "analyses": results}


# ── Analytics ─────────────────────────────────────────────────────────────────

@router.get("/analytics")
def seller_analytics(current=Depends(get_current_user)):
    listings = fetchall(
        "SELECT id, title, status, price, overall_quality_score FROM listings WHERE seller_id=?",
        (current["sub"],),
    )
    total_views = total_saves = total_contacts = 0
    enriched = []
    for l in listings:
        agg = fetchone(
            "SELECT SUM(views) v, SUM(saves) s, SUM(contacts) c FROM listing_analytics WHERE listing_id=?",
            (l["id"],),
        )
        views    = (agg["v"] or 0) if agg else 0
        saves    = (agg["s"] or 0) if agg else 0
        contacts = (agg["c"] or 0) if agg else 0
        total_views    += views
        total_saves    += saves
        total_contacts += contacts
        d = dict(l)
        d["views"]    = views
        d["saves"]    = saves
        d["contacts"] = contacts
        enriched.append(d)

    return {
        "total_listings": len(enriched),
        "published":      sum(1 for l in enriched if l["status"] == "published"),
        "total_views":    total_views,
        "total_saves":    total_saves,
        "total_contacts": total_contacts,
        "listings":       enriched,
    }


# ── Messages ──────────────────────────────────────────────────────────────────

@router.get("/messages")
def seller_messages(current=Depends(get_current_user)):
    rows = fetchall(
        """SELECT m.*, u.name sender_name, l.title listing_title
           FROM messages m
           LEFT JOIN users u ON u.id=m.sender_id
           LEFT JOIN listings l ON l.id=m.listing_id
           WHERE m.recipient_id=? ORDER BY m.created_at DESC""",
        (current["sub"],),
    )
    return {"messages": rows, "unread": sum(1 for r in rows if r["status"] == "sent")}


@router.post("/messages/{mid}/reply")
def reply_message(mid: str, message: str, current=Depends(get_current_user)):
    orig = fetchone("SELECT * FROM messages WHERE id=?", (mid,))
    if not orig:
        raise HTTPException(404, "Message not found")
    rid = str(uuid.uuid4()).replace("-", "")
    execute(
        "INSERT INTO messages(id,listing_id,sender_id,recipient_id,subject,message) VALUES(?,?,?,?,?,?)",
        (rid, orig["listing_id"], current["sub"], orig["sender_id"],
         f"Re: {orig['subject']}", message),
    )
    execute("UPDATE messages SET status='read', read_at=CURRENT_TIMESTAMP WHERE id=?", (mid,))
    return {"status": "replied", "message_id": rid}


# ── Image Validation ──────────────────────────────────────────────────────────

@router.post("/upload/validate")
async def validate_upload(file: UploadFile = File(...),
                          expected_room: Optional[str] = Query(None),
                          current=Depends(get_current_user)):
    """Validate a seller image before attaching to any listing."""
    allowed = {"jpg", "jpeg", "png", "webp"}
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in allowed:
        raise HTTPException(400, f"File type must be one of {allowed}")

    iid  = str(uuid.uuid4()).replace("-", "")
    dest = UPLOADS / f"{iid}.{ext}"
    with open(dest, "wb") as buf:
        buf.write(await file.read())

    from app.services.image_validator import get_image_validator
    result = get_image_validator().validate_upload(str(dest), expected_room=expected_room)
    result["temp_image_id"] = iid
    result["temp_path"] = str(dest)
    return result


@router.post("/upload/{image_id}/enhance")
async def enhance_upload(image_id: str, current=Depends(get_current_user)):
    """Auto-enhance a previously validated upload (CLAHE + saturation)."""
    from glob import glob
    matches = glob(str(UPLOADS / f"{image_id}.*"))
    if not matches:
        raise HTTPException(404, "Image not found — validate first via /upload/validate")
    from app.services.image_validator import get_image_validator
    return get_image_validator().auto_enhance(matches[0])


@router.post("/listings/{lid}/validate-image")
async def validate_listing_image(lid: str, file: UploadFile = File(...),
                                  expected_room_type: Optional[str] = Query(None),
                                  current=Depends(get_current_user)):
    """Validate an image in the context of a specific listing (duplicate check uses listing_id)."""
    if not fetchone("SELECT id FROM listings WHERE id=? AND seller_id=?",
                    (lid, current["sub"])):
        raise HTTPException(404, "Listing not found")

    iid  = str(uuid.uuid4()).replace("-", "")
    dest = UPLOADS / f"{iid}_{file.filename}"
    with open(dest, "wb") as buf:
        buf.write(await file.read())

    from app.services.image_validator import get_image_validator
    result = get_image_validator().validate_upload(
        str(dest), expected_room=expected_room_type, listing_id=lid
    )
    result["temp_path"] = str(dest)
    return result


# ── Extract Listing Info from Images ─────────────────────────────────────────

@router.post("/upload/extract-listing-info")
async def extract_listing_info(
    files: list[UploadFile] = File(...),
    current=Depends(get_current_user),
):
    """
    Analyse multiple uploaded images and return pre-fillable listing fields:
    property_type, bedrooms, bathrooms, description, detected_rooms, style.
    """
    from app.services.spatial_service import analyze_spatial

    room_counts: dict = {}
    styles: list = []
    temp_paths: list = []

    for f in files:
        iid  = str(uuid.uuid4()).replace("-", "")
        ext  = f.filename.rsplit(".", 1)[-1].lower() or "jpg"
        dest = UPLOADS / f"{iid}.{ext}"
        with open(dest, "wb") as buf:
            buf.write(await f.read())
        temp_paths.append(str(dest))

        try:
            spatial = analyze_spatial(str(dest))
            room = spatial.get("room_type", "unknown").lower()
            room_counts[room] = room_counts.get(room, 0) + 1
            style = spatial.get("style", "")
            if style:
                styles.append(style)
        except Exception:
            pass

    # Infer property_type from room mix
    has_bedroom  = room_counts.get("bedroom", 0)
    has_bathroom = room_counts.get("bathroom", 0)
    has_kitchen  = room_counts.get("kitchen", 0)
    has_living   = room_counts.get("living room", 0)

    if has_bedroom >= 3 or (has_bedroom and has_kitchen and has_living):
        property_type = "house"
    elif has_bedroom >= 1 and (has_bathroom or has_kitchen):
        property_type = "apartment"
    elif has_kitchen and not has_bedroom:
        property_type = "commercial"
    else:
        property_type = "house"  # safe default

    # Dominant style
    dominant_style = max(set(styles), key=styles.count) if styles else ""
    # Normalise style label
    style_map = {
        "modern minimalist": "modern", "luxury contemporary": "luxury",
        "scandinavian": "scandinavian", "industrial": "industrial",
        "farmhouse": "rustic", "traditional classic": "traditional",
    }
    style_clean = style_map.get(dominant_style, dominant_style)

    # Auto-generate description
    rooms_listed = ", ".join(
        f"{v} {k}" for k, v in sorted(room_counts.items()) if k != "unknown"
    )
    style_phrase = f"{style_clean.title()} style" if style_clean else "Well-presented"
    description = (
        f"{style_phrase} property featuring {rooms_listed}. "
        f"Professionally photographed with {len(temp_paths)} image(s)."
        if rooms_listed else
        f"{style_phrase} property. {len(temp_paths)} image(s) provided."
    )

    return {
        "property_type":   property_type,
        "bedrooms":        has_bedroom or None,
        "bathrooms":       has_bathroom or None,
        "style":           style_clean,
        "description":     description,
        "detected_rooms":  room_counts,
        "image_count":     len(temp_paths),
    }

@router.get("/listings/{lid}/investment")
def listing_investment(lid: str, current=Depends(get_current_user)):
    """Get investment metrics for a listing."""
    row = fetchone("SELECT * FROM listings WHERE id=? AND seller_id=?",
                   (lid, current["sub"]))
    if not row:
        raise HTTPException(404, "Listing not found")
    from app.services.investment_analyzer import analyze_investment
    return analyze_investment(listing_id=lid)
