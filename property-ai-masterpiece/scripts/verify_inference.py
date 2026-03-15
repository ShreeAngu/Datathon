#!/usr/bin/env python3
"""Verify inference wrapper loads correctly and runs on a sample image."""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from app.models.fake_detector_inference import get_local_fake_detector

detector = get_local_fake_detector()

# Test on one real and one fake
real_imgs = list((project_root / "dataset" / "real").rglob("*.jpg"))[:3]
fake_imgs = list((project_root / "dataset" / "fake").rglob("*.jpg"))[:3]

print("\n--- Real images ---")
for p in real_imgs:
    r = detector.detect(str(p))
    tag = "✅ CORRECT" if not r["is_ai_generated"] else "❌ WRONG"
    print(f"  {tag}  real_prob={r['real_probability']:.1f}%  ai_prob={r['ai_probability']:.1f}%  {p.name}")

print("\n--- Fake images ---")
for p in fake_imgs:
    r = detector.detect(str(p))
    tag = "✅ CORRECT" if r["is_ai_generated"] else "❌ WRONG"
    print(f"  {tag}  real_prob={r['real_probability']:.1f}%  ai_prob={r['ai_probability']:.1f}%  {p.name}")
