"""Test Hugging Face SDXL detector for authenticity detection."""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

print("Testing Hugging Face Organika/sdxl-detector model\n")
print("="*60)

# Test 1: Load model
print("TEST 1: Loading HF Model")
print("="*60)
try:
    from app.models.authenticity_hf_model import detect_ai_generated
    print("✓ Model import successful")
except Exception as e:
    print(f"✗ Model import failed: {e}")
    exit(1)

# Test 2: Test on a real image
print("\n" + "="*60)
print("TEST 2: Detect on Real Image")
print("="*60)

# Find a real image from dataset
real_images = list(Path("dataset/real").rglob("*.jpg"))
if real_images:
    test_image = str(real_images[0])
    print(f"Testing image: {Path(test_image).name}")
    
    result = detect_ai_generated(test_image)
    print(f"\n✓ Detection complete!")
    print(f"  Is AI Generated: {result['is_ai_generated']}")
    print(f"  Trust Score: {result['trust_score']}/100")
    print(f"  Confidence: {result['confidence']:.2%}")
    print(f"  Real Probability: {result['real_probability']:.2%}")
    print(f"  AI Probability: {result['ai_probability']:.2%}")
    print(f"  Model Available: {result['model_available']}")
    if 'model_name' in result:
        print(f"  Model: {result['model_name']}")
else:
    print("✗ No real images found in dataset/real/")

# Test 3: Test on a fake image
print("\n" + "="*60)
print("TEST 3: Detect on AI-Generated Image")
print("="*60)

fake_images = list(Path("dataset/fake").glob("*.jpg"))
if fake_images:
    test_image = str(fake_images[0])
    print(f"Testing image: {Path(test_image).name}")
    
    result = detect_ai_generated(test_image)
    print(f"\n✓ Detection complete!")
    print(f"  Is AI Generated: {result['is_ai_generated']}")
    print(f"  Trust Score: {result['trust_score']}/100")
    print(f"  Confidence: {result['confidence']:.2%}")
    print(f"  Real Probability: {result['real_probability']:.2%}")
    print(f"  AI Probability: {result['ai_probability']:.2%}")
else:
    print("✗ No fake images found in dataset/fake/")

# Test 4: Test authenticity service integration
print("\n" + "="*60)
print("TEST 4: Authenticity Service Integration")
print("="*60)

try:
    from app.services.authenticity_service import verify_authenticity
    
    if real_images:
        result = verify_authenticity(str(real_images[0]))
        print(f"✓ Service integration working!")
        print(f"  Trust Score: {result['trust_score']}/100")
        print(f"  Is AI Generated: {result['is_ai_generated']}")
        print(f"  Detection Method: {result['detection_method']}")
        print(f"  Confidence Level: {result['confidence_level']}")
        print(f"  Model Available: {result.get('model_available', False)}")
except Exception as e:
    print(f"✗ Service integration failed: {e}")

print("\n" + "="*60)
print("✓ All tests complete!")
print("="*60)
print("\nModel Info:")
print("  Name: Organika/sdxl-detector")
print("  Purpose: Detect SDXL-generated images")
print("  Type: Hugging Face Transformers")
print("  Output: Binary classification (real/ai-generated)")
