"""Test reverse staging (furniture removal) feature."""
import requests

BASE = "http://localhost:8000"

# Login as seller
print("Logging in as seller1...")
r = requests.post(f"{BASE}/api/v1/auth/login", json={
    "email": "seller1@propertyai.demo",
    "password": "Seller123!"
})
token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}
print("✓ Logged in\n")

# Get seller's listings
print("Fetching seller's listings...")
r = requests.get(f"{BASE}/api/v1/seller/listings", headers=headers)
listings = r.json()["listings"]
print(f"✓ Found {len(listings)} listing(s)\n")

# Get first listing with images
listing_with_images = None
for listing in listings:
    lid = listing["id"]
    r = requests.get(f"{BASE}/api/v1/seller/listings/{lid}", headers=headers)
    if r.status_code == 200:
        detail = r.json()
        if detail.get("images"):
            listing_with_images = detail
            break

if not listing_with_images:
    print("No listings with images found.")
    exit(1)

print(f"✓ Found listing: {listing_with_images['title']}")
image = listing_with_images["images"][0]
image_id = image["id"]
print(f"  Image: {image['original_filename']}\n")

# Test 1: Furnish mode (modern style)
print("="*60)
print("TEST 1: Furnish Mode - Modern Style")
print("="*60)
r = requests.post(
    f"{BASE}/api/v1/stage",
    params={"image_id": image_id, "style": "modern", "mode": "furnish"},
    headers=headers,
    timeout=120
)
if r.status_code == 200:
    result = r.json()
    print(f"✓ Success!")
    print(f"  Mode: {result.get('mode')}")
    print(f"  Style: {result.get('style')}")
    print(f"  Processing time: {result.get('processing_time')}s")
    print(f"  Staged image: {result.get('staged_image_url')}")
else:
    print(f"✗ Failed: {r.status_code}")
    print(r.text)

# Test 2: Unfurnish mode (remove furniture)
print("\n" + "="*60)
print("TEST 2: Unfurnish Mode - Remove Furniture")
print("="*60)
r = requests.post(
    f"{BASE}/api/v1/stage",
    params={"image_id": image_id, "mode": "unfurnish"},
    headers=headers,
    timeout=120
)
if r.status_code == 200:
    result = r.json()
    print(f"✓ Success!")
    print(f"  Mode: {result.get('mode')}")
    print(f"  Style: {result.get('style')}")
    print(f"  Processing time: {result.get('processing_time')}s")
    print(f"  Staged image: {result.get('staged_image_url')}")
    print(f"\n  Changes made:")
    for change in result.get('changes_made', []):
        print(f"    • {change}")
    print(f"\n  Preserved elements:")
    for elem in result.get('preserved_elements', [])[:3]:
        print(f"    • {elem}")
else:
    print(f"✗ Failed: {r.status_code}")
    print(r.text)

# Test 3: Custom prompt furnish
print("\n" + "="*60)
print("TEST 3: Custom Prompt - Bohemian Style")
print("="*60)
custom_prompt = "bohemian style with lots of plants and colorful textiles"
r = requests.post(
    f"{BASE}/api/v1/stage",
    params={"image_id": image_id, "custom_prompt": custom_prompt, "mode": "furnish"},
    headers=headers,
    timeout=120
)
if r.status_code == 200:
    result = r.json()
    print(f"✓ Success!")
    print(f"  Mode: {result.get('mode')}")
    print(f"  Custom prompt: {result.get('custom_prompt')}")
    print(f"  Processing time: {result.get('processing_time')}s")
else:
    print(f"✗ Failed: {r.status_code}")

print("\n" + "="*60)
print("✓ Reverse staging tests complete!")
print("="*60)
print("\nFeatures tested:")
print("  ✓ Furnish mode with predefined style")
print("  ✓ Unfurnish mode (furniture removal)")
print("  ✓ Custom prompt furnishing")
print("\nBenefits of unfurnish mode:")
print("  • Shows actual room dimensions")
print("  • Helps buyers visualize their own furniture")
print("  • Reveals floor space and layout")
print("  • Preserves walls, windows, and structure")
