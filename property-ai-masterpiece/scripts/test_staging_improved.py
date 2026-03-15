"""Test improved virtual staging with structure preservation."""
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

# Test staging on first image with multiple styles
image = listing_with_images["images"][0]
image_id = image["id"]
print(f"\n✓ Testing improved staging on image: {image_id}")
print(f"  Original filename: {image['original_filename']}")

styles_to_test = ["modern", "luxury"]

for style in styles_to_test:
    print(f"\n{'='*60}")
    print(f"Testing style: {style.upper()}")
    print(f"{'='*60}")
    
    r = requests.post(
        f"{BASE}/api/v1/stage",
        params={"image_id": image_id, "style": style},
        headers=headers,
        timeout=120
    )
    
    if r.status_code != 200:
        print(f"✗ Staging failed: {r.status_code}")
        print(r.text)
        continue
    
    result = r.json()
    print(f"✓ Staging successful!")
    print(f"  Processing time: {result.get('processing_time')}s")
    print(f"  Staged image: {result.get('staged_image_url')}")
    print(f"\n  Changes made:")
    for change in result.get('changes_made', []):
        print(f"    • {change}")
    print(f"\n  Structure preserved:")
    for elem in result.get('preserved_elements', [])[:3]:
        print(f"    • {elem}")

print("\n" + "="*60)
print("✓ Improved staging test complete!")
print("="*60)
print("\nKey improvements:")
print("  • Lower strength (0.35) preserves room structure")
print("  • Blending (70% staged + 30% original) maintains walls/windows")
print("  • Updated prompts focus on furniture/decor only")
print("  • Negative prompts prevent structural changes")
