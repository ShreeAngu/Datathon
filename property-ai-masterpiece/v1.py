# scripts/diagnose_accuracy_drop.py
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.app.models.fake_detector_inference import get_local_fake_detector
import os

detector = get_local_fake_detector()

print("\n🔍 DIAGNOSING ACCURACY DROP")
print("=" * 70)

# Test on OLD fake images (from original training)
print("\n📁 Testing on ORIGINAL Fake Images:")
old_fake_correct = 0
old_fake_total = 0
for filename in os.listdir("dataset/fake")[:30]:
    if filename.endswith(".jpg"):
        filepath = f"dataset/fake/{filename}"
        result = detector.detect(filepath)
        old_fake_total += 1
        if result['is_ai_generated']:
            old_fake_correct += 1

print(f"Original Fake Detection: {old_fake_correct}/{old_fake_total} ({old_fake_correct/old_fake_total*100:.1f}%)")

# Test on NEW fake images (from new dataset)
print("\n📁 Testing on NEW Fake Images:")
new_fake_correct = 0
new_fake_total = 0
new_fake_dir = "dataset/new_fake"  # Adjust path if different
if os.path.exists(new_fake_dir):
    for filename in os.listdir(new_fake_dir)[:30]:
        if filename.endswith(".jpg"):
            filepath = f"{new_fake_dir}/{filename}"
            result = detector.detect(filepath)
            new_fake_total += 1
            if result['is_ai_generated']:
                new_fake_correct += 1
            else:
                print(f"  ❌ MISSED: {filename} (AI Prob: {result['ai_probability']:.1f}%)")
    print(f"New Fake Detection: {new_fake_correct}/{new_fake_total} ({new_fake_correct/new_fake_total*100:.1f}%)")
else:
    print("⚠️  New fake directory not found")

# Test on NEW real images
print("\n📁 Testing on NEW Real Images:")
new_real_correct = 0
new_real_total = 0
new_real_dir = "dataset/new_real"  # Adjust path if different
if os.path.exists(new_real_dir):
    for filename in os.listdir(new_real_dir)[:30]:
        if filename.endswith(".jpg"):
            filepath = f"{new_real_dir}/{filename}"
            result = detector.detect(filepath)
            new_real_total += 1
            if not result['is_ai_generated']:
                new_real_correct += 1
            else:
                print(f"  ❌ FALSE POSITIVE: {filename} (Real Prob: {result['real_probability']:.1f}%)")
    print(f"New Real Detection: {new_real_correct}/{new_real_total} ({new_real_correct/new_real_total*100:.1f}%)")
else:
    print("⚠️  New real directory not found")

print("\n" + "=" * 70)
print("📊 DIAGNOSIS SUMMARY")
print("=" * 70)
print(f"Original Dataset Accuracy: ~82%")
print(f"New Dataset Accuracy: ~63%")
print(f"Drop: ~19%")
print("\n🔍 LIKELY CAUSES:")
print("1. New fake images are from different AI generators (newer SDXL, Midjourney v6)")
print("2. Model wasn't trained on new data distribution")
print("3. Possible label noise (some images misclassified)")