"""Test virtual staging endpoint."""
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
print(f"✓ Logged in, token: {token[:20]}...")

# Get seller's listings
print("\nFetching seller's listings...")
r = requests.get(f"{BASE}/api/v1/seller/listings", headers=headers)
if r.status_code != 200:
    print(f"Failed to get listings: {r.status_code} {r.text}")
    exit(1)

listings = r.json()["listings"]
print(f"✓ Found {len(listings)} listing(s)")

if not listings:
    print("No listings found. Create a listing first.")
    exit(1)

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
    print("No listings with images found. Upload images first.")
    exit(1)

print(f"\n✓ Found listing with images: {listing_with_images['title']}")
print(f"  Images: {len(listing_with_images['images'])}")

# Test staging on first image
image = listing_with_images["images"][0]
image_id = image["id"]
print(f"\n✓ Testing staging on image: {image_id}")
print(f"  Original filename: {image['original_filename']}")

# Try staging with modern style
print("\nGenerating staged version (modern style)...")
r = requests.post(
    f"{BASE}/api/v1/stage",
    params={"image_id": image_id, "style": "modern"},
    headers=headers,
    timeout=120
)

if r.status_code != 200:
    print(f"✗ Staging failed: {r.status_code}")
    print(r.text)
    exit(1)

result = r.json()
print(f"\n✓ Staging successful!")
print(f"  Style: {result.get('style')}")
print(f"  Tier: {result.get('tier')}")
print(f"  Processing time: {result.get('processing_time')}s")
print(f"  Staged image URL: {result.get('staged_image_url')}")
print(f"  Original image URL: {result.get('original_image_url')}")
print(f"\nChanges made:")
for change in result.get('changes_made', []):
    print(f"  • {change}")
print(f"\nPreserved elements:")
for elem in result.get('preserved_elements', []):
    print(f"  • {elem}")

print("\n✓ All tests passed!")
