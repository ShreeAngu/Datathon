#!/usr/bin/env python3
"""
Validate collected dataset — quality, balance, and readiness for training.
Usage: python scripts/validate_dataset.py
"""

import sys, json
from pathlib import Path
from PIL import Image
from collections import Counter

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

DATASET_DIR = project_root / "dataset"
REAL_DIR    = DATASET_DIR / "real"
FAKE_DIR    = DATASET_DIR / "fake"
META_DIR    = DATASET_DIR / "metadata"


def validate_image(path: Path) -> bool:
    try:
        img = Image.open(path)
        img.verify()
        img = Image.open(path)
        if img.width < 200 or img.height < 200:
            return False
        if path.stat().st_size < 5_000:
            return False
        return True
    except Exception:
        return False


def validate_dataset():
    print("🔍 Validating Dataset...")
    print("=" * 60)

    real_imgs = list(REAL_DIR.rglob("*.jpg"))
    fake_imgs = list(FAKE_DIR.rglob("*.jpg"))

    print(f"📷 Real images found : {len(real_imgs)}")
    print(f"🤖 Fake images found : {len(fake_imgs)}")

    # Quality check
    print("\n📊 Quality validation (this may take a minute)...")
    bad = []
    for p in real_imgs + fake_imgs:
        if not validate_image(p):
            bad.append(p)

    valid_count = len(real_imgs) + len(fake_imgs) - len(bad)
    print(f"✅ Valid  : {valid_count}")
    print(f"❌ Invalid: {len(bad)}")
    if bad:
        print("  Bad files (first 10):")
        for p in bad[:10]:
            print(f"    {p.relative_to(project_root)}")

    # Category breakdown (real)
    print("\n📂 Real image categories:")
    cats = Counter(p.parent.name for p in real_imgs)
    for cat, cnt in cats.most_common():
        bar = "█" * (cnt // 5)
        print(f"  {cat:<20} {cnt:>4}  {bar}")

    # Source breakdown (fake via metadata)
    print("\n🤖 Fake image sources:")
    sources = Counter()
    for p in fake_imgs:
        meta_path = META_DIR / f"{p.stem}.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text())
                sources[meta.get("source", "unknown")] += 1
            except Exception:
                sources["unknown"] += 1
        else:
            sources["no_metadata"] += 1
    for src, cnt in sources.most_common():
        print(f"  {src:<45} {cnt:>4}")

    # Summary
    total = len(real_imgs) + len(fake_imgs)
    print(f"\n{'=' * 60}")
    print(f"📊 DATASET SUMMARY")
    print(f"{'=' * 60}")
    print(f"Total  : {total}")
    if total:
        print(f"Real   : {len(real_imgs)} ({len(real_imgs)/total*100:.1f}%)")
        print(f"Fake   : {len(fake_imgs)} ({len(fake_imgs)/total*100:.1f}%)")
        print(f"Valid  : {valid_count} ({valid_count/total*100:.1f}%)")

    print(f"\n💡 RECOMMENDATIONS:")
    if len(real_imgs) < 1000:
        print(f"  ⚠  Need {1000 - len(real_imgs)} more real images  → run collect_real_images.py")
    else:
        print(f"  ✅ Real images target met")
    if len(fake_imgs) < 900:
        print(f"  ⚠  Need {900 - len(fake_imgs)} more fake images  → run collect_fake_images.py")
    else:
        print(f"  ✅ Fake images target met")
    if len(real_imgs) >= 1000 and len(fake_imgs) >= 900:
        print(f"\n  🚀 Dataset ready — run: python scripts/retrain_fake_detector.py")

    return {"total": total, "real": len(real_imgs), "fake": len(fake_imgs),
            "valid": valid_count, "bad": len(bad)}


if __name__ == "__main__":
    validate_dataset()
