#!/usr/bin/env python3
"""
Collect fake/AI-generated images from HuggingFace datasets.
Target: 900+ fake images (up from 100).
Usage: python scripts/collect_fake_images.py

Tested working datasets (as of 2025):
  - dima806/real_vs_fake_images_detection  (label=1 → fake)
  - Hemg/fake-and-real-images              (label=0 → fake)
  - competitions/aiornot                   (label='ai' → fake)
"""

import os, sys, json, time
from pathlib import Path
from PIL import Image

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env
env_path = project_root / "backend" / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

FAKE_DIR     = project_root / "dataset" / "fake"
METADATA_DIR = project_root / "dataset" / "metadata"
CHECKPOINT   = project_root / "dataset" / "fake_collection_checkpoint.json"
FAKE_DIR.mkdir(parents=True, exist_ok=True)
METADATA_DIR.mkdir(parents=True, exist_ok=True)

HF_TOKEN = os.environ.get("HF_TOKEN", "")


def load_checkpoint() -> set:
    if CHECKPOINT.exists():
        return set(json.loads(CHECKPOINT.read_text()))
    return set()


def save_checkpoint(seen: set):
    CHECKPOINT.write_text(json.dumps(list(seen), indent=2))


def save_image(img: Image.Image, filename: str, meta: dict) -> bool:
    dest = FAKE_DIR / filename
    if dest.exists():
        return False
    try:
        img = img.convert("RGB")
        if img.width < 200 or img.height < 200:
            return False
        img.save(str(dest), "JPEG", quality=92)
        if dest.stat().st_size < 5_000:
            dest.unlink()
            return False
        (METADATA_DIR / f"{dest.stem}.json").write_text(json.dumps(meta, indent=2))
        return True
    except Exception as e:
        print(f"    ⚠  Save error: {e}")
        return False


# ---------------------------------------------------------------------------
# Dataset configs — (name, split, fake_label_value, label_key, image_key)
# ---------------------------------------------------------------------------
DATASETS = [
    {
        "name":       "dima806/real_vs_fake_images_detection",
        "split":      "train",
        "image_key":  "image",
        "label_key":  "label",
        "fake_value": 1,          # 0=real, 1=fake
        "target":     400,
        "prefix":     "dima806",
    },
    {
        "name":       "Hemg/fake-and-real-images",
        "split":      "train",
        "image_key":  "image",
        "label_key":  "label",
        "fake_value": 0,          # 0=fake, 1=real  (reversed!)
        "target":     300,
        "prefix":     "hemg",
    },
    {
        "name":       "competitions/aiornot",
        "split":      "train",
        "image_key":  "image",
        "label_key":  "label",
        "fake_value": "ai",       # string label
        "target":     200,
        "prefix":     "aiornot",
    },
]


def collect_from_hf(cfg: dict, seen: set) -> int:
    from datasets import load_dataset

    name      = cfg["name"]
    target    = cfg["target"]
    prefix    = cfg["prefix"]
    img_key   = cfg["image_key"]
    lbl_key   = cfg["label_key"]
    fake_val  = cfg["fake_value"]

    print(f"\n🤖 {name}  (target: {target})")

    try:
        ds = load_dataset(
            name,
            split=cfg["split"],
            streaming=True,
            token=HF_TOKEN or None,
            trust_remote_code=True,
        )
    except Exception as e:
        print(f"  ❌ Load failed: {e}")
        return 0

    collected = 0
    for i, item in enumerate(ds):
        if collected >= target:
            break

        label = item.get(lbl_key)
        if label != fake_val:
            continue

        img = item.get(img_key)
        if img is None:
            continue

        uid      = f"{prefix}_{i:05d}"
        filename = f"fake_{uid}.jpg"

        if uid in seen:
            collected += 1   # already on disk
            continue

        meta = {
            "source":    name,
            "type":      "fake",
            "generator": item.get("generator", item.get("model", "unknown")),
            "label":     str(label),
        }

        if save_image(img, filename, meta):
            seen.add(uid)
            collected += 1
            save_checkpoint(seen)
            if collected % 50 == 0:
                print(f"  ✅ {collected}/{target}")

    print(f"  ✅ Done: {collected} images from {name}")
    return collected


def collect_all():
    seen = load_checkpoint()
    print("🚀 Fake Image Collection")
    print("=" * 60)
    print(f"   HF token: {'set ✅' if HF_TOKEN else 'MISSING ❌'}")
    print(f"   Already on disk: {sum(1 for _ in FAKE_DIR.glob('*.jpg'))}")

    total_new = 0
    for cfg in DATASETS:
        try:
            n = collect_from_hf(cfg, seen)
            total_new += n
        except Exception as e:
            print(f"  ⚠  Skipping {cfg['name']}: {e}")

    total = sum(1 for _ in FAKE_DIR.glob("*.jpg"))
    print(f"\n{'=' * 60}")
    print(f"✅ FAKE COLLECTION COMPLETE")
    print(f"   New this run : {total_new}")
    print(f"   Total on disk: {total}")
    print(f"{'=' * 60}")
    return total


if __name__ == "__main__":
    collect_all()
