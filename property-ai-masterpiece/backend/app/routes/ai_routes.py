"""AI routes — on-demand analysis, staging, price prediction."""

import uuid, json
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional

from app.database.connection import fetchall, fetchone, execute
from app.auth.auth import get_current_user

router = APIRouter()
UPLOADS = Path("dataset/uploads")
UPLOADS.mkdir(parents=True, exist_ok=True)


# ── On-demand image analysis ──────────────────────────────────────────────────

@router.post("/analyze-image")
async def analyze_image(file: UploadFile = File(...),
                        current=Depends(get_current_user)):
    fid  = str(uuid.uuid4()).replace("-", "")
    dest = UPLOADS / f"{fid}_{file.filename}"
    with open(dest, "wb") as buf:
        buf.write(await file.read())

    from app.services.analysis_pipeline import get_analyzer
    result = get_analyzer().analyze(str(dest))
    return {k: v for k, v in result.items() if k != "embedding"}


# ── Virtual staging ───────────────────────────────────────────────────────────

@router.post("/stage-image")
async def stage_image_ai(file: UploadFile = File(...),
                         style: str = Query("modern"),
                         current=Depends(get_current_user)):
    fid  = str(uuid.uuid4()).replace("-", "")
    dest = UPLOADS / f"{fid}_{file.filename}"
    with open(dest, "wb") as buf:
        buf.write(await file.read())

    from app.services.staging_service import get_staging_service
    result = get_staging_service().stage_image(str(dest), style)
    result["original_image_url"] = f"/images/uploads/{dest.name}"
    return result


# ── Price prediction ──────────────────────────────────────────────────────────

class PricePredictBody(BaseModel):
    city: Optional[str] = None
    state: Optional[str] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    square_feet: Optional[int] = None
    year_built: Optional[int] = None
    property_type: str = "house"
    overall_quality_score: Optional[float] = None


@router.post("/predict-price")
def predict_price(body: PricePredictBody, current=Depends(get_current_user)):
    """Simple regression-based price estimate from comparable listings."""
    rows = fetchall(
        """SELECT price, square_feet, bedrooms, bathrooms, overall_quality_score
           FROM listings WHERE status='published' AND price > 0""",
    )

    if not rows:
        # Fallback heuristic
        base = 250_000
        if body.square_feet:
            base = body.square_feet * 200
        if body.bedrooms:
            base += body.bedrooms * 15_000
        return {"predicted_price": round(base, -3),
                "confidence": 0.4, "method": "heuristic", "comparables": 0}

    # Weighted average of comparables
    prices = [r["price"] for r in rows if r["price"]]
    avg    = sum(prices) / len(prices)

    # Adjust for sqft
    if body.square_feet and any(r["square_feet"] for r in rows):
        sqft_prices = [r["price"] / r["square_feet"]
                       for r in rows if r["square_feet"] and r["price"]]
        if sqft_prices:
            ppsf = sum(sqft_prices) / len(sqft_prices)
            avg  = ppsf * body.square_feet

    # Quality adjustment
    if body.overall_quality_score:
        adj = (body.overall_quality_score - 70) / 100 * 0.15
        avg *= (1 + adj)

    return {
        "predicted_price": round(avg, -3),
        "confidence":      min(0.85, 0.5 + len(rows) / 200),
        "method":          "comparable_average",
        "comparables":     len(rows),
        "price_range":     {"low": round(avg * 0.9, -3), "high": round(avg * 1.1, -3)},
    }


# ── Duplicate detection ───────────────────────────────────────────────────────

@router.post("/detect-duplicates")
async def detect_duplicates(file: UploadFile = File(...),
                            current=Depends(get_current_user)):
    fid  = str(uuid.uuid4()).replace("-", "")
    dest = UPLOADS / f"{fid}_{file.filename}"
    with open(dest, "wb") as buf:
        buf.write(await file.read())

    from app.models.clip_model import get_image_embedding
    from app.services.vector_indexer import search as vec_search

    emb     = get_image_embedding(str(dest)).tolist()
    matches = vec_search(emb, top_k=5)

    dupes = []
    for m in matches:
        score = m.get("score", 0) if isinstance(m, dict) else m.score
        if float(score) > 0.92:
            mid = m.get("id") if isinstance(m, dict) else m.id
            dupes.append({"id": mid, "similarity": round(float(score), 4)})

    return {"duplicates_found": len(dupes) > 0,
            "count": len(dupes), "matches": dupes}
