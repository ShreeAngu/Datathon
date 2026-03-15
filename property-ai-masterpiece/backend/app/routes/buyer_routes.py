"""Buyer routes — favorites, history, alerts, messages."""

import uuid, json
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from pydantic import BaseModel
from typing import Optional

from app.database.connection import fetchall, fetchone, execute, get_db
from app.auth.auth import get_current_user

router = APIRouter()


# ── Favorites ────────────────────────────────────────────────────────────────

@router.post("/favorites")
def add_favorite(listing_id: str, collection: str = "Default",
                 current=Depends(get_current_user)):
    fid = str(uuid.uuid4()).replace("-", "")
    try:
        execute("INSERT INTO favorites(id,buyer_id,listing_id,collection_name) VALUES(?,?,?,?)",
                (fid, current["sub"], listing_id, collection))
    except Exception:
        raise HTTPException(409, "Already in favorites")
    return {"status": "saved", "id": fid}


@router.get("/favorites")
def list_favorites(current=Depends(get_current_user)):
    rows = fetchall(
        """SELECT f.id, f.listing_id, f.collection_name, f.created_at,
                  l.title, l.city, l.state, l.price, l.overall_quality_score
           FROM favorites f LEFT JOIN listings l ON l.id=f.listing_id
           WHERE f.buyer_id=? ORDER BY f.created_at DESC""",
        (current["sub"],),
    )
    return {"favorites": rows, "count": len(rows)}


@router.delete("/favorites/{fav_id}")
def remove_favorite(fav_id: str, current=Depends(get_current_user)):
    execute("DELETE FROM favorites WHERE id=? AND buyer_id=?", (fav_id, current["sub"]))
    return {"status": "removed"}


# ── Viewing History ───────────────────────────────────────────────────────────

@router.post("/history/{listing_id}")
def record_view(listing_id: str, current=Depends(get_current_user)):
    hid = str(uuid.uuid4()).replace("-", "")
    execute("INSERT INTO viewing_history(id,user_id,listing_id) VALUES(?,?,?)",
            (hid, current["sub"], listing_id))
    # bump analytics
    from datetime import date
    today = date.today().isoformat()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO listing_analytics(id,listing_id,date,views)
               VALUES(?,?,?,1)
               ON CONFLICT(listing_id,date) DO UPDATE SET views=views+1""",
            (str(uuid.uuid4()).replace("-",""), listing_id, today),
        )
    return {"status": "recorded"}


@router.get("/history")
def get_history(limit: int = 20, current=Depends(get_current_user)):
    rows = fetchall(
        """SELECT vh.listing_id, vh.viewed_at, l.title, l.city, l.price
           FROM viewing_history vh LEFT JOIN listings l ON l.id=vh.listing_id
           WHERE vh.user_id=? ORDER BY vh.viewed_at DESC LIMIT ?""",
        (current["sub"], limit),
    )
    return {"history": rows}


# ── Smart Alerts ──────────────────────────────────────────────────────────────

class AlertBody(BaseModel):
    name: str
    search_criteria: dict
    frequency: str = "daily"


@router.post("/alerts")
def create_alert(body: AlertBody, current=Depends(get_current_user)):
    aid = str(uuid.uuid4()).replace("-", "")
    execute("INSERT INTO smart_alerts(id,user_id,name,search_criteria,frequency) VALUES(?,?,?,?,?)",
            (aid, current["sub"], body.name, json.dumps(body.search_criteria), body.frequency))
    return {"status": "created", "id": aid}


@router.get("/alerts")
def list_alerts(current=Depends(get_current_user)):
    rows = fetchall("SELECT * FROM smart_alerts WHERE user_id=? AND is_active=1",
                    (current["sub"],))
    return {"alerts": rows}


@router.delete("/alerts/{alert_id}")
def delete_alert(alert_id: str, current=Depends(get_current_user)):
    execute("UPDATE smart_alerts SET is_active=0 WHERE id=? AND user_id=?",
            (alert_id, current["sub"]))
    return {"status": "deleted"}


# ── Contact Seller ────────────────────────────────────────────────────────────

class MessageBody(BaseModel):
    listing_id: str
    subject: str
    message: str


@router.post("/contact")
def contact_seller(body: MessageBody, current=Depends(get_current_user)):
    listing = fetchone("SELECT seller_id FROM listings WHERE id=?", (body.listing_id,))
    if not listing:
        raise HTTPException(404, "Listing not found")
    mid = str(uuid.uuid4()).replace("-", "")
    execute(
        "INSERT INTO messages(id,listing_id,sender_id,recipient_id,subject,message) VALUES(?,?,?,?,?,?)",
        (mid, body.listing_id, current["sub"], listing["seller_id"],
         body.subject, body.message),
    )
    # Notify seller
    nid = str(uuid.uuid4()).replace("-", "")
    execute(
        "INSERT INTO notifications(id,user_id,type,title,content) VALUES(?,?,?,?,?)",
        (nid, listing["seller_id"], "message", "New message from buyer", body.subject),
    )
    return {"status": "sent", "message_id": mid}


# ── Notifications ─────────────────────────────────────────────────────────────

@router.get("/notifications")
def get_notifications(current=Depends(get_current_user)):
    rows = fetchall(
        "SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 50",
        (current["sub"],),
    )
    return {"notifications": rows,
            "unread": sum(1 for r in rows if not r["is_read"])}


@router.post("/notifications/{nid}/read")
def mark_read(nid: str, current=Depends(get_current_user)):
    execute("UPDATE notifications SET is_read=1 WHERE id=? AND user_id=?",
            (nid, current["sub"]))
    return {"status": "read"}


# ── Reverse Image Search ──────────────────────────────────────────────────────

@router.post("/reverse-search")
async def reverse_image_search(
    file: UploadFile = File(...),
    top_k: int = Query(10, ge=1, le=50),
    min_similarity: float = Query(0.3, ge=0.0, le=1.0),
    current=Depends(get_current_user),
):
    """Upload an image to find visually similar listings."""
    fid  = str(uuid.uuid4()).replace("-", "")
    dest = Path("dataset/uploads") / f"{fid}_{file.filename}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as buf:
        buf.write(await file.read())

    from app.services.reverse_search import reverse_search
    result = reverse_search(str(dest), top_k=top_k, min_similarity=min_similarity)
    return result


# ── Investment Analysis ───────────────────────────────────────────────────────

@router.get("/listings/{listing_id}/investment")
def get_investment_analysis(
    listing_id: str,
    current=Depends(get_current_user),
):
    """Get investment metrics for any published listing."""
    row = fetchone("SELECT * FROM listings WHERE id=? AND status='published'",
                   (listing_id,))
    if not row:
        raise HTTPException(404, "Listing not found or not published")
    from app.services.investment_analyzer import analyze_investment
    return analyze_investment(listing_id=listing_id)


# ── Neighborhood Score ────────────────────────────────────────────────────────

@router.get("/properties/{listing_id}/neighborhood-score")
def get_neighborhood_score(listing_id: str, current=Depends(get_current_user)):
    """Return neighborhood walkability, transit, safety, amenities scores."""
    row = fetchone("SELECT * FROM listings WHERE id=?", (listing_id,))
    if not row:
        raise HTTPException(404, "Listing not found")

    # Check cache
    cached = fetchone("SELECT score_data FROM neighborhood_scores WHERE listing_id=?",
                      (listing_id,))
    if cached:
        return json.loads(cached["score_data"])

    from app.services.neighborhood_scorer import get_neighborhood_scorer
    result = get_neighborhood_scorer().score_neighborhood(dict(row))

    # Cache it
    nid = str(uuid.uuid4()).replace("-", "")
    execute(
        """INSERT OR REPLACE INTO neighborhood_scores
           (id, listing_id, overall_score, walkability, transit, safety, amenities, score_data)
           VALUES (?,?,?,?,?,?,?,?)""",
        (nid, listing_id,
         result["overall_score"],
         result["breakdown"]["walkability"]["score"],
         result["breakdown"]["transit"]["score"],
         result["breakdown"]["safety"]["score"],
         result["breakdown"]["amenities"]["score"],
         json.dumps(result)),
    )
    return result


# ── Reverse Image Search (enriched) ──────────────────────────────────────────

@router.post("/search/reverse-image")
async def reverse_image_search_enriched(
    file: UploadFile = File(...),
    top_k: int = Query(10, ge=1, le=50),
    min_similarity: float = Query(0.3, ge=0.0, le=1.0),
    current=Depends(get_current_user),
):
    """Upload an image to find visually similar listings with style + palette analysis."""
    fid  = str(uuid.uuid4()).replace("-", "")
    dest = Path("dataset/uploads") / f"{fid}_{file.filename}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    with open(dest, "wb") as buf:
        buf.write(await file.read())

    from app.services.reverse_search import reverse_search
    result = reverse_search(str(dest), top_k=top_k, min_similarity=min_similarity)

    # Log search history
    hid = str(uuid.uuid4()).replace("-", "")
    execute(
        "INSERT INTO search_history(id,user_id,query,filters,result_count) VALUES(?,?,?,?,?)",
        (hid, current["sub"], f"reverse_image:{file.filename}",
         json.dumps({"top_k": top_k, "min_similarity": min_similarity}),
         result.get("total_found", 0)),
    )
    return result


# ── Advanced Search ───────────────────────────────────────────────────────────

@router.get("/search/advanced")
def advanced_search(
    query:         Optional[str]   = Query(None),
    city:          Optional[str]   = Query(None),
    state:         Optional[str]   = Query(None),
    min_price:     Optional[float] = Query(None),
    max_price:     Optional[float] = Query(None),
    min_beds:      Optional[int]   = Query(None),
    max_beds:      Optional[int]   = Query(None),
    min_baths:     Optional[float] = Query(None),
    property_type: Optional[str]   = Query(None),
    min_sqft:      Optional[int]   = Query(None),
    max_sqft:      Optional[int]   = Query(None),
    min_quality:   Optional[float] = Query(None),
    verified_only: bool            = Query(False),
    semantic_rank: bool            = Query(False),
    page:          int             = Query(1, ge=1),
    per_page:      int             = Query(20, ge=1, le=100),
    current=Depends(get_current_user),
):
    """
    Hybrid search: SQL filters + keyword matching + optional semantic ranking.
    
    - query: Text search in title/description (keyword) + semantic ranking (if enabled)
    - semantic_rank: If True, uses CLIP embeddings to rank results by relevance
    - Other params: Standard SQL filters
    """
    conditions = ["l.status = 'published'"]
    params: list = []

    # Keyword search in title and description
    if query:
        conditions.append("(LOWER(l.title) LIKE ? OR LOWER(l.description) LIKE ?)")
        query_pattern = f"%{query.lower()}%"
        params.extend([query_pattern, query_pattern])

    if city:          conditions.append("LOWER(l.city) LIKE ?");          params.append(f"%{city.lower()}%")
    if state:         conditions.append("LOWER(l.state) LIKE ?");         params.append(f"%{state.lower()}%")
    if min_price:     conditions.append("l.price >= ?");                  params.append(min_price)
    if max_price:     conditions.append("l.price <= ?");                  params.append(max_price)
    if min_beds:      conditions.append("l.bedrooms >= ?");               params.append(min_beds)
    if max_beds:      conditions.append("l.bedrooms <= ?");               params.append(max_beds)
    if min_baths:     conditions.append("l.bathrooms >= ?");              params.append(min_baths)
    if property_type: conditions.append("l.property_type = ?");           params.append(property_type)
    if min_sqft:      conditions.append("l.square_feet >= ?");            params.append(min_sqft)
    if max_sqft:      conditions.append("l.square_feet <= ?");            params.append(max_sqft)
    if min_quality:   conditions.append("l.overall_quality_score >= ?");  params.append(min_quality)
    if verified_only: conditions.append("l.authenticity_verified = 1")

    where = " AND ".join(conditions)
    total_row = fetchone(f"SELECT COUNT(*) as cnt FROM listings l WHERE {where}", tuple(params))
    total = total_row["cnt"] if total_row else 0

    # Fetch all matching listings (before pagination for semantic ranking)
    rows = fetchall(
        f"""SELECT l.*, u.name as seller_name
            FROM listings l LEFT JOIN users u ON u.id = l.seller_id
            WHERE {where} ORDER BY l.published_at DESC""",
        tuple(params),
    )

    # Enrich each listing with primary image URL
    from pathlib import Path as _Path
    result_listings = []
    for r in rows:
        d = dict(r)
        primary = fetchone(
            "SELECT image_path FROM images WHERE listing_id=? AND is_primary=1 LIMIT 1",
            (d["id"],),
        )
        if primary:
            fname = _Path(primary["image_path"]).name
            d["image_url"] = f"/images/uploads/{fname}"
        else:
            d["image_url"] = None
        result_listings.append(d)

    # Semantic ranking if requested and query provided
    if semantic_rank and query and result_listings:
        try:
            from app.models.clip_model import get_text_embedding
            import numpy as np
            
            # Get query embedding
            query_emb = get_text_embedding(query)
            
            # Calculate semantic similarity for each listing
            for listing in result_listings:
                # Create text representation of listing
                listing_text = f"{listing.get('title', '')} {listing.get('description', '')} {listing.get('city', '')} {listing.get('property_type', '')}"
                
                # Get listing embedding
                listing_emb = get_text_embedding(listing_text)
                
                # Calculate cosine similarity
                similarity = float(np.dot(query_emb, listing_emb) / 
                                 (np.linalg.norm(query_emb) * np.linalg.norm(listing_emb)))
                listing["semantic_score"] = round(similarity, 4)
            
            # Sort by semantic score (descending)
            result_listings.sort(key=lambda x: x.get("semantic_score", 0), reverse=True)
            
        except Exception as e:
            print(f"[Semantic ranking failed] {e}")
            # Continue without semantic ranking

    # Apply pagination after semantic ranking
    offset = (page - 1) * per_page
    paginated_listings = result_listings[offset:offset + per_page]

    # Log search history
    hid = str(uuid.uuid4()).replace("-", "")
    execute(
        "INSERT INTO search_history(id,user_id,query,filters,result_count) VALUES(?,?,?,?,?)",
        (hid, current["sub"], query or "",
         json.dumps({"city": city, "state": state, "min_price": min_price,
                     "max_price": max_price, "property_type": property_type,
                     "semantic_rank": semantic_rank}),
         total),
    )

    return {
        "total": total, "page": page, "per_page": per_page,
        "pages": max(1, (total + per_page - 1) // per_page),
        "listings": paginated_listings,
        "semantic_ranking_enabled": semantic_rank and query is not None,
    }


# ── Property Comparison ───────────────────────────────────────────────────────

class CompareBody(BaseModel):
    listing_ids: list[str]


@router.post("/properties/compare")
def save_comparison(body: CompareBody, current=Depends(get_current_user)):
    """Save a set of listing IDs for comparison."""
    if len(body.listing_ids) < 2:
        raise HTTPException(400, "Provide at least 2 listing IDs to compare")
    if len(body.listing_ids) > 4:
        raise HTTPException(400, "Maximum 4 listings can be compared at once")

    cid = str(uuid.uuid4()).replace("-", "")
    execute(
        "INSERT INTO user_comparisons(id,user_id,listing_ids) VALUES(?,?,?)",
        (cid, current["sub"], json.dumps(body.listing_ids)),
    )
    return {"comparison_id": cid, "listing_ids": body.listing_ids}


@router.get("/comparison")
def get_comparison(
    listing_ids: str = Query(..., description="Comma-separated listing IDs"),
    current=Depends(get_current_user),
):
    """Return side-by-side comparison data for up to 4 listings."""
    ids = [i.strip() for i in listing_ids.split(",") if i.strip()][:4]
    if len(ids) < 2:
        raise HTTPException(400, "Provide at least 2 listing IDs")

    results = []
    for lid in ids:
        row = fetchone(
            """SELECT l.*, u.name as seller_name
               FROM listings l LEFT JOIN users u ON u.id=l.seller_id
               WHERE l.id=?""",
            (lid,),
        )
        if not row:
            continue
        d = dict(row)

        # Attach neighborhood score if cached
        ns = fetchone("SELECT overall_score FROM neighborhood_scores WHERE listing_id=?", (lid,))
        d["neighborhood_score"] = ns["overall_score"] if ns else None

        # Attach investment summary if cached
        inv = fetchone("SELECT roi_percent, rental_yield, cap_rate FROM investment_analysis WHERE listing_id=?", (lid,))
        d["investment"] = dict(inv) if inv else None

        results.append(d)

    return {"count": len(results), "listings": results}


@router.get("/listings/{listing_id}")
def get_listing_detail(listing_id: str, current=Depends(get_current_user)):
    """Get full listing details including all images for buyers."""
    import pathlib
    row = fetchone(
        """SELECT l.*, u.name as seller_name, u.email as seller_email
           FROM listings l LEFT JOIN users u ON u.id=l.seller_id
           WHERE l.id=? AND l.status='published'""",
        (listing_id,),
    )
    if not row:
        raise HTTPException(404, "Listing not found or not published")
    
    # Get all images
    images = fetchall(
        "SELECT * FROM images WHERE listing_id=? ORDER BY upload_order",
        (listing_id,),
    )
    for img in images:
        fname = pathlib.Path(img["image_path"]).name
        img["image_url"] = f"/images/uploads/{fname}"
    
    result = dict(row)
    result["images"] = images
    return result
