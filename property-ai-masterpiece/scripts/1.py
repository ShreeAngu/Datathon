# scripts/test_authenticity.py
import sys
import os
from pathlib import Path

# FIX: Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Now imports work
from backend.app.services.authenticity_service import verify_authenticity

real_correct = 0
fake_correct = 0
real_total = 0
fake_total = 0

print("🔍 Testing Authenticity Detector...")
print("-" * 50)

# Test real images
print("Testing REAL images...")
for filename in os.listdir("dataset/real")[:50]:
    if filename.endswith(".jpg"):
        filepath = f"dataset/real/{filename}"
        result = verify_authenticity(filepath)
        real_total += 1
        is_real = not result.get('is_ai_generated', False)
        if is_real:
            real_correct += 1
        else:
            print(f"  ❌ False positive: {filename}")

# Test fake images
print("Testing FAKE images...")
for filename in os.listdir("dataset/fake")[:50]:
    if filename.endswith(".jpg"):
        filepath = f"dataset/fake/{filename}"
        result = verify_authenticity(filepath)
        fake_total += 1
        is_fake = result.get('is_ai_generated', False)
        if is_fake:
            fake_correct += 1
        else:
            print(f"  ❌ False negative: {filename}")

# Print results
print("\n" + "=" * 50)
print("📊 AUTHENTICITY DETECTOR RESULTS")
print("=" * 50)
print(f"Real Images: {real_correct}/{real_total} correctly identified ({real_correct/real_total*100:.1f}%)")
print(f"Fake Images: {fake_correct}/{fake_total} correctly identified ({fake_correct/fake_total*100:.1f}%)")
print(f"Overall Accuracy: {(real_correct+fake_correct)/(real_total+fake_total)*100:.1f}%")
print("-" * 50)

if (real_correct+fake_correct)/(real_total+fake_total) < 0.85:
    print("⚠️  Accuracy < 85% - Consider upgrading to DL model")
else:
    print("✅ Accuracy good enough for demo!")