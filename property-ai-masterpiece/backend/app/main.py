"""
Property AI Masterpiece — FastAPI Backend
Run from project root: uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
"""

import os, sys, json, uuid, glob
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# Paths & env
# ---------------------------------------------------------------------------
ROOT = Path(__file__).parent.parent.parent
load_dotenv(ROOT / "backend" / ".env")
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT)

DATASET       = ROOT / "dataset"
RESULTS_DIR   = DATASET / "analysis_results"
UPLOADS_DIR   = DATASET / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(title="Property AI Masterpiece API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── v2 Routes ────────────────────────────────────────────────────────────────
from app.routes.auth_routes   import router as auth_router
from app.routes.buyer_routes  import router as buyer_router
from app.routes.seller_routes import router as seller_router
from app.routes.admin_routes  import router as admin_router
from app.routes.ai_routes     import router as ai_router

app.include_router(auth_router,   prefix="/api/v1/auth",   tags=["Auth"])
app.include_router(buyer_router,  prefix="/api/v1/buyer",  tags=["Buyer"])
app.include_router(seller_router, prefix="/api/v1/seller", tags=["Seller"])
app.include_router(admin_router,  prefix="/api/v1/admin",  tags=["Admin"])
app.include_router(ai_router,     prefix="/api/v1/ai",     tags=["AI"])

# Static file mounts
STAGED_DIR = DATASET / "staged"
STAGED_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/images/real",   StaticFiles(directory=str(DATASET / "real")),   name="real_images")
app.mount("/images/fake",   StaticFiles(directory=str(DATASET / "fake")),   name="fake_images")
app.mount("/images/uploads",StaticFiles(directory=str(UPLOADS_DIR)),        name="uploads")
app.mount("/uploads",       StaticFiles(directory="backend/app/uploads", check_dir=False), name="seller_uploads")
app.mount("/images/staged", StaticFiles(directory=str(STAGED_DIR)),         name="staged")
app.mount("/viz",           StaticFiles(directory=str(DATASET / "visualizations")), name="viz")

# ---------------------------------------------------------------------------
# Lazy-loaded singletons
# ---------------------------------------------------------------------------
_analyzer = None
_indexer  = None

def get_analyzer():
    global _analyzer
    if _analyzer is None:
        from app.services.analysis_pipeline import get_analyzer as _ga
        _analyzer = _ga()
    return _analyzer

def get_indexer():
    global _indexer
    if _indexer is None:
        from app.services.vector_indexer import _get_index
        _indexer = _get_index()
    return _indexer

# ---------------------------------------------------------------------------
# Helper: resolve image URL from analysis JSON
# ---------------------------------------------------------------------------
def _image_url(stem: str, analysis: dict) -> str:
    label = analysis.get("authenticity", {}).get("ground_truth_label", "real")
    img_path = analysis.get("image_path", "")
    if label == "fake" or "fake" in img_path:
        fname = Path(img_path).name if img_path else f"{stem}.jpg"
        return f"/images/fake/{fname}"
    # real: category subdir
    cat = Path(img_path).parent.name if img_path else ""
    fname = Path(img_path).name if img_path else f"{stem}.jpg"
    return f"/images/real/{cat}/{fname}" if cat else f"/images/real/{fname}"

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/")
async def root():
    return {"message": "Property AI Masterpiece API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
async def health():
    return {"status": "ok"}


# Pre-warm reverse search embedding cache in background
@app.on_event("startup")
async def warmup_embedding_cache():
    import asyncio, threading
    def _warm():
        try:
            from app.services.reverse_search import _get_cached_embedding
            from app.database.connection import fetchall
            from pathlib import Path
            rows = fetchall(
                "SELECT i.image_path FROM images i "
                "JOIN listings l ON l.id=i.listing_id "
                "WHERE l.status='published' AND i.is_primary=1", ()
            )
            for row in rows:
                p = Path("dataset/uploads") / row["image_path"]
                if p.exists():
                    _get_cached_embedding(str(p))
            print(f"[warmup] Cached embeddings for {len(rows)} listing images")
        except Exception as e:
            print(f"[warmup] Skipped: {e}")
    threading.Thread(target=_warm, daemon=True).start()


# ── Upload & Analyze ────────────────────────────────────────────────────────
@app.post("/api/v1/upload")
async def upload_image(files: list[UploadFile] = File(...)):
    image_ids = []
    for file in files:
        file_id   = str(uuid.uuid4())
        file_path = str(UPLOADS_DIR / f"{file_id}_{file.filename}")
        with open(file_path, "wb") as buf:
            buf.write(await file.read())

        result = get_analyzer().analyze(file_path)

        # Save analysis (strip embedding — too large for JSON response)
        save = {k: v for k, v in result.items() if k != "embedding"}
        (RESULTS_DIR / f"{file_id}_analysis.json").write_text(json.dumps(save, indent=2))

        # Index to Pinecone
        from app.services.vector_indexer import index_image
        index_image(file_id, result["embedding"], {
            "filename":          file.filename,
            "label":             "upload",
            "category":          "upload",
            "room_type":         str(result["spatial"].get("room_type", "")),
            "style":             str(result["spatial"].get("style", "")),
            "overall_score":     float(result["quality"].get("overall_score", 0)),
            "is_ai_generated":   bool(result["authenticity"].get("is_ai_generated", False)),
            "trust_score":       float(result["authenticity"].get("trust_score", 0)),
            "accessibility_score": float(result["accessibility"].get("accessibility_score", 0)),
        })
        image_ids.append({"id": file_id, "filename": file.filename,
                          "analysis": save})

    return {"status": "success", "count": len(image_ids), "images": image_ids}


# ── Semantic Search ─────────────────────────────────────────────────────────
@app.get("/api/v1/search")
async def search(
    query: str              = Query(...),
    min_trust_score: float  = Query(0),
    accessibility_required: bool = Query(False),
    limit: int              = Query(20),
):
    from app.models.clip_model import get_text_embedding
    from app.services.vector_indexer import search as vec_search

    emb     = get_text_embedding(query).tolist()
    matches = vec_search(emb, top_k=min(limit * 2, 100))  # over-fetch then filter

    results = []
    for m in matches:
        meta = m.get("metadata", {}) if isinstance(m, dict) else (m.metadata or {})
        mid  = m.get("id") if isinstance(m, dict) else m.id
        score = m.get("score", 0) if isinstance(m, dict) else m.score

        if float(meta.get("trust_score", 0)) < min_trust_score:
            continue
        if accessibility_required and not meta.get("is_wheelchair_accessible", False):
            continue

        # Load analysis for image URL
        analysis_file = RESULTS_DIR / f"{mid}_analysis.json"
        img_url = ""
        if analysis_file.exists():
            analysis = json.loads(analysis_file.read_text())
            img_url  = _image_url(mid, analysis)

        results.append({
            "id":                  mid,
            "image_url":           img_url,
            "room_type":           meta.get("room_type", ""),
            "style":               meta.get("style", ""),
            "trust_score":         float(meta.get("trust_score", 0)),
            "overall_score":       float(meta.get("overall_score", 0)),
            "accessibility_score": float(meta.get("accessibility_score", 0)),
            "is_ai_generated":     bool(meta.get("is_ai_generated", False)),
            "label":               meta.get("label", "real"),
            "similarity":          round(float(score), 4),
        })
        if len(results) >= limit:
            break

    return {"query": query, "count": len(results), "results": results}


# ── Get Analysis ─────────────────────────────────────────────────────────────
@app.get("/api/v1/analysis/{image_id}")
async def get_analysis(image_id: str):
    path = RESULTS_DIR / f"{image_id}_analysis.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Analysis not found for {image_id}")
    analysis = json.loads(path.read_text())
    analysis["image_url"] = _image_url(image_id, analysis)
    return analysis


# ── List Images ──────────────────────────────────────────────────────────────
@app.get("/api/v1/images")
async def list_images(
    label:    Optional[str] = Query(None),   # real | fake
    category: Optional[str] = Query(None),
    page:     int           = Query(1),
    per_page: int           = Query(24),
):
    files = sorted(RESULTS_DIR.glob("*_analysis.json"))
    items = []
    for f in files:
        try:
            d    = json.loads(f.read_text())
            lbl  = d.get("authenticity", {}).get("ground_truth_label", "real")
            cat  = Path(d.get("image_path", "")).parent.name
            if label    and lbl != label:    continue
            if category and cat != category: continue
            stem = f.stem.replace("_analysis", "")
            items.append({
                "id":            stem,
                "image_url":     _image_url(stem, d),
                "label":         lbl,
                "category":      cat,
                "room_type":     d.get("spatial", {}).get("room_type", ""),
                "overall_score": d.get("quality",  {}).get("overall_score", 0),
                "trust_score":   d.get("authenticity", {}).get("trust_score", 0),
            })
        except Exception:
            continue

    total  = len(items)
    start  = (page - 1) * per_page
    paged  = items[start:start + per_page]
    return {"total": total, "page": page, "per_page": per_page, "items": paged}


# ── Stats ────────────────────────────────────────────────────────────────────
@app.get("/api/v1/stats")
async def get_stats():
    files = list(RESULTS_DIR.glob("*_analysis.json"))
    real = fake = 0
    q_scores = []
    t_scores = []
    room_counts: dict = {}
    style_counts: dict = {}

    for f in files:
        try:
            d     = json.loads(f.read_text())
            label = d.get("authenticity", {}).get("ground_truth_label", "real")
            if label == "fake": fake += 1
            else:               real += 1
            q_scores.append(float(d.get("quality",       {}).get("overall_score", 0)))
            t_scores.append(float(d.get("authenticity",  {}).get("trust_score",   0)))
            rt = d.get("spatial", {}).get("room_type", "unknown")
            st = d.get("spatial", {}).get("style",     "unknown")
            room_counts[rt]  = room_counts.get(rt, 0)  + 1
            style_counts[st] = style_counts.get(st, 0) + 1
        except Exception:
            continue

    n = max(len(files), 1)
    return {
        "total_images":    len(files),
        "real_images":     real,
        "fake_images":     fake,
        "avg_quality_score": round(sum(q_scores) / n, 1),
        "avg_trust_score":   round(sum(t_scores) / n, 1),
        "room_type_distribution":  dict(sorted(room_counts.items(),  key=lambda x: -x[1])),
        "style_distribution":      dict(sorted(style_counts.items(), key=lambda x: -x[1])),
    }


# ── Virtual Staging ──────────────────────────────────────────────────────────
STAGING_STYLES = {
    "modern":       {"name": "Modern",       "description": "Clean lines, minimalist, neutral tones"},
    "scandinavian": {"name": "Scandinavian", "description": "Light wood, cozy textiles, white walls"},
    "industrial":   {"name": "Industrial",   "description": "Exposed brick, metal fixtures, dark wood"},
    "rustic":       {"name": "Rustic",       "description": "Farmhouse warmth, vintage furniture"},
    "luxury":       {"name": "Luxury",       "description": "High-end finishes, marble, gold accents"},
}


@app.get("/api/v1/staging-styles")
async def get_staging_styles():
    return {"styles": [{"id": k, **v} for k, v in STAGING_STYLES.items()]}


@app.get("/api/v1/staging-samples")
async def get_staging_samples(limit: int = Query(9)):
    """Return a curated list of images suitable for staging (small/cluttered rooms)."""
    candidates = []
    for cat in ("small_cramped", "cluttered", "old_outdated", "clean_modern"):
        cat_dir = DATASET / "real" / cat
        if cat_dir.exists():
            for img in sorted(cat_dir.glob("*.jpg"))[:3]:
                stem = img.stem
                analysis_file = RESULTS_DIR / f"{stem}_analysis.json"
                room_type = cat.replace("_", " ")
                if analysis_file.exists():
                    try:
                        d = json.loads(analysis_file.read_text())
                        room_type = d.get("spatial", {}).get("room_type", room_type)
                    except Exception:
                        pass
                candidates.append({
                    "id":        stem,
                    "image_url": f"/images/real/{cat}/{img.name}",
                    "category":  cat,
                    "room_type": room_type,
                })
    return {"samples": candidates[:limit]}


@app.get("/api/v1/staging-changes/{image_id}/{style}")
async def get_staging_changes(image_id: str, style: str):
    from app.services.staging_service import STYLE_CHANGES, PRESERVED_ELEMENTS, STYLE_PROMPTS
    if style not in STYLE_PROMPTS:
        raise HTTPException(status_code=400, detail="Unknown style")
    return {
        "image_id":           image_id,
        "style":              style,
        "structure_preserved": True,
        "changes_made":       STYLE_CHANGES[style],
        "preserved_elements": PRESERVED_ELEMENTS,
        "modifications": {
            "furniture":  "Added/updated per style",
            "materials":  "Flooring and wall colours adjusted",
            "decor":      "Artwork, plants, textiles added",
            "lighting":   "Brightness and warmth adjusted",
        },
    }


@app.post("/api/v1/stage")
async def stage_image(
    image_id: str = Query(...),
    style: str    = Query(None),
    custom_prompt: str = Query(None),
    mode: str = Query("furnish", regex="^(furnish|unfurnish)$"),
):
    """
    Virtual staging endpoint supporting both furnishing and unfurnishing.
    
    Modes:
    - furnish: Add/update furniture (default)
    - unfurnish: Remove furniture, show empty room
    
    For furnish mode: Either 'style' or 'custom_prompt' must be provided
    For unfurnish mode: No style/prompt needed
    """
    # Validate parameters based on mode
    if mode == "furnish" and not style and not custom_prompt:
        raise HTTPException(status_code=400,
                            detail="For furnish mode, either 'style' or 'custom_prompt' must be provided")
    
    if mode == "furnish" and style and style not in STAGING_STYLES:
        raise HTTPException(status_code=400,
                            detail=f"Style must be one of: {list(STAGING_STYLES)}")

    # First try to find in database (seller uploaded images)
    from app.database.connection import fetchone
    db_img = fetchone("SELECT image_path FROM images WHERE id=?", (image_id,))
    if db_img:
        img_path = UPLOADS_DIR / db_img["image_path"]
        if not img_path.exists():
            raise HTTPException(status_code=404, detail=f"Image file not found: {db_img['image_path']}")
    else:
        # Fallback: check dataset images (real/fake categories)
        img_path = None
        for cat_dir in (DATASET / "real").iterdir():
            candidate = cat_dir / f"{image_id}.jpg"
            if candidate.exists():
                img_path = candidate
                break
        if img_path is None:
            candidate = DATASET / "fake" / f"{image_id}.jpg"
            if candidate.exists():
                img_path = candidate
        if img_path is None:
            # Try uploads by glob
            matches = list(UPLOADS_DIR.glob(f"*{image_id}*"))
            if matches:
                img_path = matches[0]
        if img_path is None:
            raise HTTPException(status_code=404, detail=f"Image not found: {image_id}")

    from app.services.staging_service import get_staging_service
    result = get_staging_service().stage_image(
        str(img_path), 
        style=style, 
        custom_prompt=custom_prompt,
        mode=mode
    )

    # Resolve original image URL
    if db_img:
        result["original_image_url"] = f"/images/uploads/{db_img['image_path']}"
    else:
        label = "fake" if "fake" in str(img_path) else "real"
        if label == "real":
            cat   = img_path.parent.name
            result["original_image_url"] = f"/images/real/{cat}/{img_path.name}"
        else:
            result["original_image_url"] = f"/images/fake/{img_path.name}"

    result["image_id"] = image_id
    result["mode"] = mode
    return result
