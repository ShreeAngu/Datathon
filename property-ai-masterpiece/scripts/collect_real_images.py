#!/usr/bin/env python3
"""
Collect real property images from Unsplash API.
Target: 400+ images across 8 categories.
Usage: python scripts/collect_real_images.py
"""

import os, sys, json, time, requests, hashlib
from pathlib import Path
from PIL import Image
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

BASE_DIR      = project_root / "dataset" / "real"
METADATA_DIR  = project_root / "dataset" / "metadata"
CHECKPOINT    = project_root / "dataset" / "real_collection_checkpoint.json"

CATEGORIES = {
    "living_room":  ["modern living room interior", "contemporary living room", "luxury living room"],
    "bedroom":      ["modern bedroom interior", "minimalist bedroom", "cozy bedroom design"],
    "kitchen":      ["modern kitchen interior", "contemporary kitchen", "luxury kitchen design"],
    "bathroom":     ["modern bathroom interior", "luxury bathroom", "spa bathroom"],
    "dining_room":  ["dining room interior", "modern dining room", "formal dining room"],
    "home_office":  ["home office interior", "modern workspace", "study room design"],
    "cluttered":    ["messy room interior", "cluttered living space", "untidy room"],
    "empty":        ["empty room interior", "unfurnished room", "vacant apartment room"],
}


def load_checkpoint():
    if CHECKPOINT.exists():
        return json.loads(CHECKPOINT.read_text())
    return {"unsplash": 0, "collected_ids": [], "images": []}


def save_checkpoint(data):
    CHECKPOINT.write_text(json.dumps(data, indent=2))


def download_image(url: str, dest: Path) -> bool:
    try:
        r = requests.get(url, timeout=30)
        if r.status_code != 200:
            return False
        img = Image.open(BytesIO(r.content))
        if img.width < 500 or img.height < 400:
            return False
        img = img.convert("RGB")
        img.save(str(dest), "JPEG", quality=92)
        if dest.stat().st_size < 10_000:
            dest.unlink()
            return False
        return True
    except Exception as e:
        print(f"    ⚠  Download error: {e}")
        return False


def collect_unsplash(target: int = 400):
    key = os.environ.get("UNSPLASH_ACCESS_KEY", "")
    if not key:
        print("❌ UNSPLASH_ACCESS_KEY not set in backend/.env")
        return 0

    checkpoint = load_checkpoint()
    collected  = checkpoint["unsplash"]
    seen_ids   = set(checkpoint["collected_ids"])

    print(f"\n📷 Unsplash — target: {target}  already have: {collected}")
    headers = {"Authorization": f"Client-ID {key}"}

    for category, queries in CATEGORIES.items():
        cat_dir = BASE_DIR / category
        cat_dir.mkdir(parents=True, exist_ok=True)
        METADATA_DIR.mkdir(parents=True, exist_ok=True)

        for query in queries:
            if collected >= target:
                break

            for page in range(1, 6):          # up to 5 pages × 30 = 150 per query
                if collected >= target:
                    break

                try:
                    r = requests.get(
                        "https://api.unsplash.com/search/photos",
                        headers=headers,
                        params={"query": query, "per_page": 30,
                                "page": page, "orientation": "landscape"},
                        timeout=15,
                    )
                    if r.status_code == 403:
                        print("  ⚠  Rate limited — sleeping 60s")
                        time.sleep(60)
                        continue
                    if r.status_code != 200:
                        break

                    photos = r.json().get("results", [])
                    if not photos:
                        break

                    for photo in photos:
                        if collected >= target:
                            break
                        pid = photo["id"]
                        if pid in seen_ids:
                            continue

                        url      = photo["urls"]["regular"]
                        filename = f"unsplash_{category}_{pid}.jpg"
                        dest     = cat_dir / filename

                        if dest.exists():
                            seen_ids.add(pid)
                            collected += 1
                            continue

                        if download_image(url, dest):
                            seen_ids.add(pid)
                            collected += 1
                            checkpoint["images"].append(str(dest.relative_to(project_root)))
                            checkpoint["collected_ids"] = list(seen_ids)
                            checkpoint["unsplash"] = collected
                            save_checkpoint(checkpoint)

                            meta = {
                                "source": "unsplash", "category": category,
                                "type": "real", "photographer": photo["user"]["name"],
                                "width": photo["width"], "height": photo["height"],
                            }
                            (METADATA_DIR / f"{dest.stem}.json").write_text(
                                json.dumps(meta, indent=2))

                            print(f"  ✅ [{collected}/{target}] {filename}")
                            time.sleep(0.4)

                    time.sleep(1.5)

                except Exception as e:
                    print(f"  ⚠  Query error ({query}): {e}")
                    time.sleep(5)

    print(f"\n✅ Unsplash done: {collected} images")
    return collected


if __name__ == "__main__":
    total = collect_unsplash(target=400)
    real_total = sum(1 for _ in BASE_DIR.rglob("*.jpg"))
    print(f"\n📊 Total real images on disk: {real_total}")
