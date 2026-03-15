import sys
import os
from pathlib import Path

# Add both project root AND backend so 'app.*' imports resolve
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from backend.app.services.authenticity_service import verify_authenticity

real_correct = 0
fake_correct = 0
real_total = 0
fake_total = 0

print("🔍 Testing Authenticity Detector...")
print("-" * 50)

# Test real images — rglob handles subdirectories
print("Testing REAL images...")
real_imgs = list(Path("dataset/real").rglob("*.jpg"))[:50]
for img_path in real_imgs:
    try:
        result = verify_authenticity(str(img_path))
        real_total += 1
        if not result.get('is_ai_generated', False):
            real_correct += 1
        else:
            print(f"  ❌ False positive: {img_path.name}")
    except Exception as e:
        print(f"  ⚠ Error on {img_path.name}: {e}")

# Test fake images
print("Testing FAKE images...")
fake_imgs = list(Path("dataset/fake").rglob("*.jpg"))[:50]
for img_path in fake_imgs:
    try:
        result = verify_authenticity(str(img_path))
        fake_total += 1
        if result.get('is_ai_generated', False):
            fake_correct += 1
        else:
            print(f"  ❌ False negative: {img_path.name}")
    except Exception as e:
        print(f"  ⚠ Error on {img_path.name}: {e}")

print("\n" + "=" * 50)
print("📊 AUTHENTICITY DETECTOR RESULTS")
print("=" * 50)

if real_total:
    print(f"Real Images: {real_correct}/{real_total} correctly identified ({real_correct/real_total*100:.1f}%)")
else:
    print("Real Images: no data")

if fake_total:
    print(f"Fake Images: {fake_correct}/{fake_total} correctly identified ({fake_correct/fake_total*100:.1f}%)")
else:
    print("Fake Images: no data")

total = real_total + fake_total
if total:
    overall = (real_correct + fake_correct) / total * 100
    print(f"Overall Accuracy: {overall:.1f}%")
    print("-" * 50)
    if overall < 85:
        print("⚠️  Accuracy < 85% - Consider upgrading to DL model")
    else:
        print("✅ Accuracy good enough for demo!")
