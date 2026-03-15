"""Debug the HF model directly to see what it returns."""
import sys
sys.path.insert(0, "backend")
import os
os.chdir(".")

from pathlib import Path

# Test directly
from app.models.authenticity_hf_model import detect_ai_generated

real_imgs = list(Path("dataset/real").glob("*.jpg"))[:3]
fake_imgs = list(Path("dataset/fake").glob("*.jpg"))[:3]

print("=== REAL IMAGES ===")
for img in real_imgs:
    r = detect_ai_generated(str(img))
    print(f"  {img.name}: AI={r['is_ai_generated']} ai_prob={r['ai_probability']:.4f} real_prob={r['real_probability']:.4f}")

print("\n=== FAKE IMAGES ===")
for img in fake_imgs:
    r = detect_ai_generated(str(img))
    print(f"  {img.name}: AI={r['is_ai_generated']} ai_prob={r['ai_probability']:.4f} real_prob={r['real_probability']:.4f}")
