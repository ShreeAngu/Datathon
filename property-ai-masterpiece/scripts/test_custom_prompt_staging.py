"""Test custom prompt virtual staging feature."""
import requests
import json

BASE = "http://localhost:8000"

# Login as seller
print("Logging in as seller1...")
r = requests.post(f"{BASE}/api/v1/auth/login", json={
    "email": "seller1@propertyai.demo",
    "password": "Seller123!"
})
if r.status_code != 200:
    print(f"Login failed: {r.status_code} {r.text}")
    exit(1)

token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"✓ Logged in")

# Get seller's listings
print("\nFetching seller's listings...")
r = requests.get(f"{BASE}/api/v1/seller/listings", headers=headers)
listings = r.json()["listings"]
print(f"✓ Found {len(listings)} listing(s)")

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

print(f"\n✓ Found listing: {listing_with_images['title']}")
image = listing_with_images["images"][0]
image_id = image["id"]
print(f"  Image: {image['original_filename']}")

# Test 1: Predefined style
print("\n" + "="*60)
print("TEST 1: Predefined Style (Modern)")
print("="*60)
r = requests.post(
    f"{BASE}/api/v1/stage",
    params={"image_id": image_id, "style": "modern"},
    headers=headers,
    timeout=120
)
if r.status_code == 200:
    result = r.json()
    print(f"✓ Success!")
    print(f"  Style: {result.get('style')}")
    print(f"  Processing time: {result.get('processing_time')}s")
    print(f"  Custom prompt: {result.get('custom_prompt')}")
else:
    print(f"✗ Failed: {r.status_code}")

# Test 2: Custom prompt
print("\n" + "="*60)
print("TEST 2: Custom Prompt")
print("="*60)
custom_prompt = "bohemian style with lots of plants, colorful textiles, and natural wood furniture"
print(f"Prompt: '{custom_prompt}'")
r = requests.post(
    f"{BASE}/api/v1/stage",
    params={"image_id": image_id, "custom_prompt": custom_prompt},
    headers=headers,
    timeout=120
)
if r.status_code == 200:
    result = r.json()
    print(f"✓ Success!")
    print(f"  Style: {result.get('style')}")
    print(f"  Processing time: {result.get('processing_time')}s")
    print(f"  Custom prompt: {result.get('custom_prompt')}")
    print(f"  Staged image: {result.get('staged_image_url')}")
else:
    print(f"✗ Failed: {r.status_code}")
    print(r.text)

# Test 3: Another custom prompt
print("\n" + "="*60)
print("TEST 3: Another Custom Prompt")
print("="*60)
custom_prompt = "Japanese zen minimalist with tatami mats, low furniture, and bamboo accents"
print(f"Prompt: '{custom_prompt}'")
r = requests.post(
    f"{BASE}/api/v1/stage",
    params={"image_id": image_id, "custom_prompt": custom_prompt},
    headers=headers,
    timeout=120
)
if r.status_code == 200:
    result = r.json()
    print(f"✓ Success!")
    print(f"  Style: {result.get('style')}")
    print(f"  Processing time: {result.get('processing_time')}s")
    print(f"  Custom prompt: {result.get('custom_prompt')}")
    print(f"  Staged image: {result.get('staged_image_url')}")
else:
    print(f"✗ Failed: {r.status_code}")
    print(r.text)

print("\n" + "="*60)
print("✓ Custom prompt staging tests complete!")
print("="*60)
print("\nFeatures tested:")
print("  ✓ Predefined style staging")
print("  ✓ Custom prompt staging (bohemian)")
print("  ✓ Custom prompt staging (Japanese zen)")
print("\nTo test in UI:")
print("  1. Open http://localhost:8501")
print("  2. Login as seller or buyer")
print("  3. Go to Virtual Staging tab")
print("  4. Select 'Custom Prompt' mode")
print("  5. Enter your own staging description")
