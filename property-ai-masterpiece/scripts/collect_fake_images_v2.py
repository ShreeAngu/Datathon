#!/usr/bin/env python3
"""
Collect fake/AI-generated property images via direct HTTP downloads.
Sources:
  1. This-X-Does-Not-Exist APIs (free, no auth)
  2. Picsum + image manipulation to simulate AI artifacts
  3. Pre-curated public AI image URLs from known open sources

Target: 900 fake images (up from 100)
Run: python scripts/collect_fake_images_v2.py
"""

import os, sys, json, time, hashlib, random, requests
from pathlib import Path
from io import BytesIO
from PIL import Image, ImageFilter, ImageEnhance

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

env_path = project_root / "backend" / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

FAKE_DIR     = project_root / "dataset" / "fake"
METADATA_DIR = project_root / "dataset" / "metadata"
CHECKPOINT   = project_root / "dataset" / "fake_v2_checkpoint.json"
FAKE_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)

UNSPLASH_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")


def load_checkpoint() -> set:
    if CHECKPOINT.exists():
        return set(json.loads(CHECKPOINT.read_text()))
    return set()


def save_checkpoint(seen: set):
    CHECKPOINT.write_text(json.dumps(list(seen), indent=2))


def save_fake(img: Image.Image, filename: str, source: str, generator: str) -> bool:
    dest = FAKE_DIR / filename
    if dest.exists():
        return False
    try:
        img = img.convert("RGB")
        if img.width < 300 or img.height < 200:
            return False
        img.save(str(dest), "JPEG", quality=92)
        if dest.stat().st_size < 8_000:
            dest.unlink()
            return False
        meta = {"source": source, "type": "fake", "generator": generator}
        (METADATA_DIR / f"{dest.stem}.json").write_text(json.dumps(meta, indent=2))
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Source 1: thispersondoesnotexist / thisxdoesnotexist style APIs
# These return AI-generated images directly
# ---------------------------------------------------------------------------
THISDOESNOTEXIST_SOURCES = [
    # (url_template, name, count)
    # Each call returns a unique AI-generated image
    ("https://picsum.photos/seed/{seed}/800/600", "picsum_base", 0),  # real, skip
]

# ---------------------------------------------------------------------------
# Source 2: Lexica.art public API — real AI-generated images, no auth needed
# ---------------------------------------------------------------------------
LEXICA_QUERIES = [
    "luxury modern living room interior photorealistic",
    "contemporary bedroom interior design photorealistic",
    "modern kitchen interior photorealistic render",
    "luxury bathroom interior photorealistic",
    "modern home office interior photorealistic",
    "contemporary dining room interior photorealistic",
    "minimalist bedroom scandinavian design photorealistic",
    "open concept living room modern design photorealistic",
    "luxury master bedroom interior design photorealistic",
    "modern apartment interior photorealistic render",
]


def collect_lexica(target: int, seen: set) -> int:
    """Collect AI-generated interior images from Lexica.art public API."""
    print(f"\n🎨 Lexica.art (target: {target})")
    collected = 0

    for query in LEXICA_QUERIES:
        if collected >= target:
            break
        try:
            r = requests.get(
                "https://lexica.art/api/v1/search",
                params={"q": query},
                timeout=15,
                headers={"User-Agent": "Mozilla/5.0"},
            )
            if r.status_code != 200:
                print(f"  ⚠  Lexica returned {r.status_code} for: {query}")
                time.sleep(2)
                continue

            results = r.json().get("images", [])
            for item in results:
                if collected >= target:
                    break

                img_url = item.get("src", "")
                img_id  = item.get("id", hashlib.md5(img_url.encode()).hexdigest()[:8])

                if img_id in seen:
                    continue

                try:
                    ir = requests.get(img_url, timeout=20,
                                      headers={"User-Agent": "Mozilla/5.0"})
                    if ir.status_code != 200:
                        continue
                    img = Image.open(BytesIO(ir.content))
                    filename = f"fake_lexica_{img_id}.jpg"
                    if save_fake(img, filename, "lexica.art", "stable-diffusion"):
                        seen.add(img_id)
                        collected += 1
                        save_checkpoint(seen)
                        if collected % 25 == 0:
                            print(f"  ✅ {collected}/{target}")
                        time.sleep(0.3)
                except Exception:
                    continue

            time.sleep(1.5)

        except Exception as e:
            print(f"  ⚠  Error: {e}")
            time.sleep(3)

    print(f"  ✅ Lexica done: {collected}")
    return collected


# ---------------------------------------------------------------------------
# Source 3: Unsplash — collect MORE real images, then apply AI-style transforms
# to create a "hard negative" set that trains the model on edge cases
# ---------------------------------------------------------------------------
UNSPLASH_AI_QUERIES = [
    "3d render interior design",
    "CGI room visualization",
    "architectural visualization interior",
    "3d rendered living room",
    "computer generated interior",
    "virtual staging interior design",
    "3d render bedroom design",
    "architectural render kitchen",
]


def collect_unsplash_renders(target: int, seen: set) -> int:
    """Collect CGI/render images from Unsplash (labeled as fake — they are AI/CG generated)."""
    if not UNSPLASH_KEY:
        print("  ⚠  No UNSPLASH_ACCESS_KEY — skipping renders")
        return 0

    print(f"\n🖥  Unsplash CGI renders (target: {target})")
    collected = 0
    headers = {"Authorization": f"Client-ID {UNSPLASH_KEY}"}

    for query in UNSPLASH_AI_QUERIES:
        if collected >= target:
            break
        try:
            r = requests.get(
                "https://api.unsplash.com/search/photos",
                headers=headers,
                params={"query": query, "per_page": 30, "orientation": "landscape"},
                timeout=15,
            )
            if r.status_code != 200:
                time.sleep(5)
                continue

            for photo in r.json().get("results", []):
                if collected >= target:
                    break
                pid = photo["id"]
                if pid in seen:
                    continue

                url = photo["urls"]["regular"]
                try:
                    ir = requests.get(url, timeout=20)
                    if ir.status_code != 200:
                        continue
                    img = Image.open(BytesIO(ir.content))
                    filename = f"fake_render_{pid}.jpg"
                    if save_fake(img, filename, "unsplash_cgi", "3d_render"):
                        seen.add(pid)
                        collected += 1
                        save_checkpoint(seen)
                        if collected % 25 == 0:
                            print(f"  ✅ {collected}/{target}")
                        time.sleep(0.4)
                except Exception:
                    continue

            time.sleep(2)

        except Exception as e:
            print(f"  ⚠  Error: {e}")
            time.sleep(5)

    print(f"  ✅ Unsplash renders done: {collected}")
    return collected


# ---------------------------------------------------------------------------
# Source 4: Pexels free API (if key available)
# ---------------------------------------------------------------------------
def collect_pexels_renders(target: int, seen: set) -> int:
    pexels_key = os.environ.get("PEXELS_API_KEY", "")
    if not pexels_key:
        print("\n  ℹ  No PEXELS_API_KEY — skipping Pexels renders")
        return 0

    print(f"\n📷 Pexels CGI renders (target: {target})")
    collected = 0
    headers = {"Authorization": pexels_key}
    queries = ["3d render interior", "CGI room", "architectural visualization",
               "virtual staging", "3d rendered bedroom"]

    for query in queries:
        if collected >= target:
            break
        try:
            r = requests.get(
                "https://api.pexels.com/v1/search",
                headers=headers,
                params={"query": query, "per_page": 40, "orientation": "landscape"},
                timeout=15,
            )
            if r.status_code != 200:
                continue
            for photo in r.json().get("photos", []):
                if collected >= target:
                    break
                pid = str(photo["id"])
                if pid in seen:
                    continue
                url = photo["src"]["large"]
                try:
                    ir = requests.get(url, timeout=20)
                    img = Image.open(BytesIO(ir.content))
                    filename = f"fake_pexels_render_{pid}.jpg"
                    if save_fake(img, filename, "pexels_cgi", "3d_render"):
                        seen.add(pid)
                        collected += 1
                        save_checkpoint(seen)
                        time.sleep(0.3)
                except Exception:
                    continue
            time.sleep(1)
        except Exception as e:
            print(f"  ⚠  {e}")

    print(f"  ✅ Pexels renders done: {collected}")
    return collected


# ---------------------------------------------------------------------------
# Source 5: HuggingFace Hub direct parquet download (bypass datasets library)
# ---------------------------------------------------------------------------
def collect_hf_parquet(target: int, seen: set) -> int:
    """
    Download fake images directly from HuggingFace parquet files,
    bypassing the broken datasets library script support.
    Uses: Heem2/AI-vs-Human-Generated-Dataset
    """
    import io
    token = os.environ.get("HF_TOKEN", "")
    if not token:
        print("\n  ⚠  No HF_TOKEN — skipping HF parquet download")
        return 0

    print(f"\n🤗 HuggingFace parquet direct download (target: {target})")

    # Known parquet URLs for AI image datasets
    parquet_urls = [
        "https://huggingface.co/datasets/Heem2/AI-vs-Human-Generated-Dataset/resolve/main/data/train-00000-of-00001.parquet",
        "https://huggingface.co/datasets/tonyassi/ai-generated-images/resolve/main/data/train-00000-of-00001.parquet",
    ]

    collected = 0
    headers = {"Authorization": f"Bearer {token}"}

    for url in parquet_urls:
        if collected >= target:
            break
        try:
            print(f"  Downloading parquet: {url.split('/')[-3]}...")
            r = requests.get(url, headers=headers, timeout=60, stream=True)
            if r.status_code != 200:
                print(f"  ⚠  HTTP {r.status_code}")
                continue

            import pandas as pd
            content = BytesIO(r.content)
            df = pd.read_parquet(content)
            print(f"  Columns: {list(df.columns)}  rows: {len(df)}")

            # Find image and label columns
            img_col = next((c for c in df.columns if "image" in c.lower()), None)
            lbl_col = next((c for c in df.columns if "label" in c.lower()), None)

            if not img_col:
                print(f"  ⚠  No image column found")
                continue

            for idx, row in df.iterrows():
                if collected >= target:
                    break

                # Skip real images if label available
                if lbl_col:
                    lbl = row[lbl_col]
                    # 0 or 'real' = real, skip
                    if str(lbl).lower() in ("0", "real", "human"):
                        continue

                img_data = row[img_col]
                uid = f"hf_parquet_{idx}"
                if uid in seen:
                    continue

                try:
                    if isinstance(img_data, dict) and "bytes" in img_data:
                        img = Image.open(BytesIO(img_data["bytes"]))
                    elif isinstance(img_data, bytes):
                        img = Image.open(BytesIO(img_data))
                    else:
                        continue

                    filename = f"fake_hf_{idx:05d}.jpg"
                    if save_fake(img, filename, "huggingface_parquet", "ai_generated"):
                        seen.add(uid)
                        collected += 1
                        save_checkpoint(seen)
                        if collected % 50 == 0:
                            print(f"  ✅ {collected}/{target}")
                except Exception:
                    continue

        except Exception as e:
            print(f"  ⚠  Parquet error: {e}")

    print(f"  ✅ HF parquet done: {collected}")
    return collected


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    seen = load_checkpoint()
    current = sum(1 for _ in FAKE_DIR.glob("*.jpg"))
    target_total = 900

    print("🚀 Fake Image Collection v2")
    print("=" * 60)
    print(f"   Already on disk : {current}")
    print(f"   Target total    : {target_total}")
    print(f"   Need to collect : {max(0, target_total - current)}")

    if current >= target_total:
        print(f"\n✅ Already have {current} fake images — target met!")
        return current

    remaining = target_total - current

    # Run sources in order
    n1 = collect_lexica(min(400, remaining), seen)
    remaining -= n1

    if remaining > 0:
        n2 = collect_unsplash_renders(min(300, remaining), seen)
        remaining -= n2

    if remaining > 0:
        n3 = collect_pexels_renders(min(150, remaining), seen)
        remaining -= n3

    if remaining > 0:
        n4 = collect_hf_parquet(min(remaining, 200), seen)

    total = sum(1 for _ in FAKE_DIR.glob("*.jpg"))
    print(f"\n{'=' * 60}")
    print(f"✅ FAKE COLLECTION COMPLETE")
    print(f"   Total on disk: {total}")
    if total >= target_total:
        print(f"   🎯 Target met!")
    else:
        print(f"   ⚠  Still need {target_total - total} more")
    print(f"{'=' * 60}")
    return total


if __name__ == "__main__":
    main()
