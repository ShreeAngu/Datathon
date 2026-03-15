"""
reindex_pinecone.py — Re-upload all embeddings from saved analysis JSONs to Pinecone.
Run from property-ai-masterpiece/:
    python scripts/reindex_pinecone.py
"""
import os, sys, json
from pathlib import Path
from tqdm import tqdm

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "backend"))
os.chdir(ROOT)

from dotenv import load_dotenv
load_dotenv(ROOT / "backend" / ".env")

RESULTS_DIR = ROOT / "dataset" / "analysis_results"

# ── Load all analysis JSONs + their embeddings ──────────────────────────────
# Embeddings were NOT saved in the analysis JSON (stripped before write).
# We need to re-run CLIP on each image to get the embedding.
# But that's slow — instead we saved them to Pinecone during the run.
# Since only 90 made it, we re-run CLIP only on the missing ones.

from pinecone import Pinecone
pc    = Pinecone(api_key=os.getenv("PINECONE_API_KEY", ""))
index = pc.Index("property-ai")

# Find which IDs are already in Pinecone
print("Fetching existing Pinecone IDs...")
stats = index.describe_index_stats()
existing_count = stats.total_vector_count
print(f"  Currently indexed: {existing_count}")

# Collect all image stems from analysis results
all_jsons = sorted(RESULTS_DIR.glob("*_analysis.json"))
print(f"  Analysis JSONs found: {len(all_jsons)}")

# Check which are missing by fetching in batches of 100
all_stems = [j.stem.replace("_analysis", "") for j in all_jsons]

print("Checking which vectors are missing from Pinecone...")
missing_stems = []
batch_size = 100
for i in range(0, len(all_stems), batch_size):
    batch = all_stems[i:i+batch_size]
    try:
        resp = index.fetch(ids=batch)
        fetched = set(resp.vectors.keys())
    except Exception:
        fetched = set()
    for stem in batch:
        if stem not in fetched:
            missing_stems.append(stem)

print(f"  Missing from Pinecone: {len(missing_stems)}")

if not missing_stems:
    print("All vectors already indexed. Done.")
    sys.exit(0)

# ── Re-run CLIP on missing images and upsert ────────────────────────────────
from app.models.clip_model import get_image_embedding

# Build stem → image path map
img_map = {}
for label_dir in (ROOT / "dataset" / "real").iterdir():
    if label_dir.is_dir():
        for img in label_dir.glob("*.jpg"):
            img_map[img.stem] = (img, "real")
for img in (ROOT / "dataset" / "fake").glob("*.jpg"):
    img_map[img.stem] = (img, "fake")

print(f"  Image map built: {len(img_map)} images")

vectors_batch = []
failed = 0

def flush_batch(batch):
    try:
        index.upsert(vectors=batch)
    except Exception as e:
        print(f"  [Pinecone] batch upsert failed: {e}")

with tqdm(total=len(missing_stems), desc="Re-indexing", unit="vec") as pbar:
    for stem in missing_stems:
        if stem not in img_map:
            failed += 1
            pbar.update(1)
            continue

        img_path, label = img_map[stem]
        analysis_path   = RESULTS_DIR / f"{stem}_analysis.json"

        try:
            analysis = json.loads(analysis_path.read_text())
            emb      = get_image_embedding(str(img_path)).tolist()

            meta = {
                "filename":          img_path.name,
                "label":             label,
                "category":          str(img_path.parent.name),
                "room_type":         str(analysis["spatial"].get("room_type", "")),
                "style":             str(analysis["spatial"].get("style", "")),
                "overall_score":     float(analysis["quality"].get("overall_score", 0)),
                "is_ai_generated":   bool(analysis["authenticity"].get("is_ai_generated", False)),
                "trust_score":       float(analysis["authenticity"].get("trust_score", 0)),
                "accessibility_score": float(analysis["accessibility"].get("accessibility_score", 0)),
            }

            vectors_batch.append({"id": stem, "values": emb, "metadata": meta})

            if len(vectors_batch) >= 100:
                flush_batch(vectors_batch)
                vectors_batch.clear()

        except Exception as e:
            tqdm.write(f"  Failed {stem}: {e}")
            failed += 1

        pbar.update(1)

if vectors_batch:
    flush_batch(vectors_batch)

# ── Final stats ──────────────────────────────────────────────────────────────
final_stats = index.describe_index_stats()
print(f"\nDone. Pinecone vectors: {final_stats.total_vector_count} / 570")
print(f"Failed: {failed}")
