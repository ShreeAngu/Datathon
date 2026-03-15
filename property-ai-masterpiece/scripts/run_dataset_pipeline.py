#!/usr/bin/env python3
"""
One-shot dataset expansion + retrain pipeline.
Runs all steps in sequence with progress reporting.

Usage: python scripts/run_dataset_pipeline.py
       python scripts/run_dataset_pipeline.py --skip-collect   # retrain only
       python scripts/run_dataset_pipeline.py --skip-retrain   # collect only
"""

import sys, argparse, subprocess
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

SCRIPTS = project_root / "scripts"


def run(script: str, label: str):
    print(f"\n{'=' * 60}")
    print(f"▶  {label}")
    print(f"{'=' * 60}")
    result = subprocess.run(
        [sys.executable, str(SCRIPTS / script)],
        cwd=str(project_root),
    )
    if result.returncode != 0:
        print(f"⚠  {script} exited with code {result.returncode} — continuing...")
    return result.returncode == 0


def count_images():
    real = sum(1 for _ in (project_root / "dataset" / "real").rglob("*.jpg"))
    fake = sum(1 for _ in (project_root / "dataset" / "fake").rglob("*.jpg"))
    return real, fake


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-collect", action="store_true",
                        help="Skip image collection, go straight to retrain")
    parser.add_argument("--skip-retrain", action="store_true",
                        help="Only collect images, skip retraining")
    args = parser.parse_args()

    real_before, fake_before = count_images()
    print(f"📊 Starting dataset: {real_before} real + {fake_before} fake = {real_before+fake_before} total")

    if not args.skip_collect:
        run("collect_real_images.py",  "Step 1/4 — Collect real images (Unsplash)")
        run("collect_fake_images.py",  "Step 2/4 — Collect fake images (HuggingFace)")
        run("validate_dataset.py",     "Step 3/4 — Validate dataset")

    real_after, fake_after = count_images()
    print(f"\n📊 Dataset after collection: {real_after} real + {fake_after} fake = {real_after+fake_after} total")
    print(f"   Added: +{real_after-real_before} real, +{fake_after-fake_before} fake")

    if not args.skip_retrain:
        if real_after + fake_after < 500:
            print("⚠  Dataset too small to retrain — collect more images first")
        else:
            run("retrain_fake_detector.py", "Step 4/4 — Retrain EfficientNet-B0")
            run("test_authenticity.py",     "Step 5/4 — Final accuracy test")

    print(f"\n{'=' * 60}")
    print("✅ Pipeline complete")
    print(f"{'=' * 60}")
