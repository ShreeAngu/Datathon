#!/usr/bin/env python3
"""
Collect fake (and optionally real) images from:
  FatimahEmadEldin/genai-manipulation-detection-interior

Dataset: 2000 images — 1000 real + 1000 fake
Fake categories: frequency_manipulation, smoothness_anomaly,
                 splicing, physical_impossibility, compression_artifact

Usage:
  python scripts/collect_fake_images_fatimah.py            # fake only (default)
  python scripts/collect_fake_images_fatimah.py --also-real # fake + real
  python scripts/collect_fake_images_fatimah.py --limit 500 # cap at 500 fakes
"""

import os, sys, json, argparse
from pathlib import Path
from io import BytesIO

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env
env_path = project_root / "backend" / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

import pandas as pd
from PIL import Image

DATASET    = "FatimahEmadEldin/genai-manipulation-detection-interior"
FAKE_DIR   = project_root / "dataset" / "fake"
REAL_DIR   = project_root / "dataset" / "real" / "interior_fatimah"
META_DIR   = project_root / "dataset" / "metadata"
CHECKPOINT = project_root / "dataset" / "fatimah_checkpoint.json"

FAKE_DIR.mkdir(parents=True, exist_ok=True)
REAL_DIR.mkdir(parents=True, exist_ok=True)
META_DIR.mkdir(parents=True, exist_ok=True)

TOKEN = os.environ.get("HF_TOKEN", "")


def load_checkpoint() -> set:
    if CHECKPOINT.exists():
        return set(json.loads(CHECKPOINT.read_text()))
    return set()


def save_checkpoint(seen: set):
    CHECKPOINT.write_text(json.dumps(list(seen), indent=2))


def save_image(img: Image.Image, dest: Path, meta: dict) -> bool:
    if dest.exists():
        return False
    try:
        img = img.convert("RGB")
        if img.width < 100 or img.height < 100:
            return False
        img.save(str(dest), "JPEG", quality=93)
        if dest.stat().st_size < 5_000:
            dest.unlink()
            return False
        (META_DIR / f"{dest.stem}.json").write_text(json.dumps(meta, indent=2))
        return True
    except Exception as e:
        print(f"  ⚠  Save error {dest.name}: {e}")
        return False


import requests
from concurrent.futures import ThreadPoolExecutor, as_completed

SESSION = requests.Session()
if TOKEN:
    SESSION.headers.update({"Authorization": f"Bearer {TOKEN}"})


def fetch_image(hf_path: str) -> Image.Image | None:
    """Fetch image bytes from HuggingFace dataset repo."""
    url = f"https://huggingface.co/datasets/{DATASET}/resolve/main/{hf_path}"
    try:
        r = SESSION.get(url, timeout=30)
        if r.status_code == 200:
            return Image.open(BytesIO(r.content))
        return None
    except Exception:
        return None


def fetch_and_save(row, dest: Path, meta: dict, seen: set, uid: str):
    """Worker: fetch one image and save it. Returns (uid, success)."""
    if uid in seen or dest.exists():
        return uid, "skip"
    img = fetch_image(row["image_path"])
    if img is None:
        return uid, "fail"
    ok = save_image(img, dest, meta)
    return uid, "ok" if ok else "fail"


def collect(limit_fake: int, also_real: bool):
    seen = load_checkpoint()

    print(f"📋 Loading annotations from {DATASET}...")
    df = pd.read_csv(f"hf://datasets/{DATASET}/annotations.csv",
                     storage_options={"token": TOKEN} if TOKEN else {})

    fakes = df[df["label"] == "fake"].reset_index(drop=True)
    reals = df[df["label"] == "real"].reset_index(drop=True)

    print(f"   Dataset: {len(df)} total  |  {len(reals)} real  |  {len(fakes)} fake")
    print(f"   Fake categories: {fakes['manipulation_category'].value_counts().to_dict()}")

    WORKERS = 8  # parallel download threads

    def _run_batch(rows_df, dest_dir, prefix, label, limit, extra_meta_fn):
        """Download a batch in parallel, return count collected."""
        collected = 0

        # Build work list (skip already seen)
        work = []
        for _, row in rows_df.iterrows():
            if collected + len(work) >= limit:
                break
            uid  = f"fatimah_{label}_{row['image_id']}"
            dest = dest_dir / f"{prefix}_{row['image_id']:06d}.jpg"
            if uid in seen or dest.exists():
                collected += 1
                continue
            meta = extra_meta_fn(row)
            work.append((row, dest, meta, uid))

        if not work:
            return collected

        with ThreadPoolExecutor(max_workers=WORKERS) as ex:
            futures = {
                ex.submit(fetch_and_save, row, dest, meta, seen, uid): uid
                for row, dest, meta, uid in work
            }
            for future in as_completed(futures):
                uid, status = future.result()
                if status == "ok":
                    seen.add(uid)
                    collected += 1
                    save_checkpoint(seen)
                    if collected % 50 == 0:
                        print(f"  ✅ {label} {collected}/{limit}")
                if collected >= limit:
                    break

        return collected

    # ── Collect fake images ──────────────────────────────────────────────────
    print(f"\n🤖 Collecting fake images (limit={limit_fake}, workers={WORKERS})...")

    def fake_meta(row):
        return {
            "source":                 DATASET,
            "type":                   "fake",
            "label":                  "fake",
            "manipulation_category":  row["manipulation_category"],
            "manipulation_technique": row["manipulation_technique"],
            "pair_id":                int(row["pair_id"]),
        }

    fake_collected = _run_batch(fakes, FAKE_DIR, "fake_fatimah", "fake", limit_fake, fake_meta)
    print(f"  ✅ Fake done: {fake_collected}")

    # ── Optionally collect real images ───────────────────────────────────────
    real_collected = 0
    if also_real:
        print(f"\n📷 Collecting real images (workers={WORKERS})...")

        def real_meta(row):
            return {
                "source":   DATASET,
                "type":     "real",
                "label":    "real",
                "category": "interior_fatimah",
                "pair_id":  int(row["pair_id"]),
            }

        real_collected = _run_batch(reals, REAL_DIR, "real_fatimah", "real", len(reals), real_meta)
        print(f"  ✅ Real done: {real_collected}")

    # ── Summary ──────────────────────────────────────────────────────────────
    total_fake = sum(1 for _ in FAKE_DIR.rglob("*.jpg"))
    total_real = sum(1 for _ in (project_root / "dataset" / "real").rglob("*.jpg"))

    print(f"\n{'=' * 60}")
    print(f"✅ COLLECTION COMPLETE")
    print(f"   Fake collected this run : {fake_collected}")
    print(f"   Real collected this run : {real_collected}")
    print(f"   Total fake on disk      : {total_fake}")
    print(f"   Total real on disk      : {total_real}")
    print(f"   Grand total             : {total_fake + total_real}")
    print(f"{'=' * 60}")

    if total_fake >= 900 and total_real >= 1000:
        print("🎯 Dataset targets met — ready to retrain!")
        print("   Run: python scripts/retrain_fake_detector.py")
    else:
        if total_fake < 900:
            print(f"  ⚠  Need {900 - total_fake} more fake images")
        if total_real < 1000:
            print(f"  ⚠  Need {1000 - total_real} more real images")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit",     type=int,  default=1000,
                        help="Max fake images to collect (default: 1000)")
    parser.add_argument("--also-real", action="store_true",
                        help="Also collect real images from this dataset")
    args = parser.parse_args()
    collect(limit_fake=args.limit, also_real=args.also_real)
