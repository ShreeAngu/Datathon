import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "backend"))

from backend.app.models.authenticity_dl_model import get_fake_detector

detector = get_fake_detector()
print(f"\n🧪 Testing DL Fake Image Detector — {detector.model_name}")
print("=" * 60)

fake_correct = fake_total = 0
real_correct = real_total = 0

print("\nTesting FAKE images:")
for img_path in sorted(Path("dataset/fake").rglob("*.jpg"))[:20]:
    result = detector.detect(str(img_path))
    fake_total += 1
    if result["is_ai_generated"]:
        fake_correct += 1
        print(f"  ✅ {img_path.name}: {result['ai_probability']:.1f}% AI")
    else:
        print(f"  ❌ {img_path.name}: {result['ai_probability']:.1f}% AI (MISSED)")

print(f"\nFake Detection: {fake_correct}/{fake_total} ({fake_correct/fake_total*100:.1f}%)")

print("\nTesting REAL images:")
for img_path in sorted(Path("dataset/real").rglob("*.jpg"))[:20]:
    result = detector.detect(str(img_path))
    real_total += 1
    if not result["is_ai_generated"]:
        real_correct += 1
        print(f"  ✅ {img_path.name}: {result['real_probability']:.1f}% Real")
    else:
        print(f"  ❌ {img_path.name}: {result['real_probability']:.1f}% Real (FALSE POS)")

print(f"\nReal Detection: {real_correct}/{real_total} ({real_correct/real_total*100:.1f}%)")

overall = (fake_correct + real_correct) / (fake_total + real_total) * 100
print(f"\n{'=' * 60}")
print(f"OVERALL ACCURACY: {overall:.1f}%")
print("=" * 60)
if overall >= 85:
    print("✅ EXCELLENT! Ready for demo!")
elif overall >= 75:
    print("⚠️  Good, but could improve")
else:
    print("❌ Needs improvement")
