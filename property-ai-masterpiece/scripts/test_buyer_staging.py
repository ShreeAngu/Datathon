"""Test buyer virtual staging endpoint."""
import requests
import json

BASE = "http://localhost:8000"

# Login as buyer
print("Logging in as buyer1...")
r = requests.post(f"{BASE}/api/v1/auth/login", json={
    "email": "buyer1@propertyai.demo",
    "password": "Buyer123!"
})
if r.status_code != 200:
    print(f"Login failed: {r.status_code} {r.text}")
    exit(1)

token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}
print(f"✓ Logged in as buyer, token: {token[:20]}...")

# Search for published listings
print("\nSearching for published listings...")
r = requests.get(f"{BASE}/api/v1/buyer/search/advanced", 
                 params={"per_page": 10},
                 headers=headers)
if r.status_code != 200:
    print(f"Search failed: {r.status_code} {r.text}")
    exit(1)

listings = r.json()["listings"]
print(f"✓ Found {len(listings)} published listing(s)")

if not listings:
    print("No published listings found.")
    exit(1)

# Get first listing with images
listing_with_images = None
for listing in listings:
    lid = listing["id"]
    print(f"\nChecking listing: {listing['title']}")
    r = requests.get(f"{BASE}/api/v1/buyer/listings/{lid}", headers=headers)
    if r.status_code == 200:
        detail = r.json()
        if detail.get("images"):
            listing_with_images = detail
            print(f"  ✓ Has {len(detail['images'])} image(s)")
            break
        else:
            print(f"  ✗ No images")
    else:
        print(f"  ✗ Failed to get details: {r.status_code}")

if not listing_with_images:
    print("\n✗ No published listings with images found.")
    exit(1)

print(f"\n✓ Found listing with images: {listing_with_images['title']}")
print(f"  Seller: {listing_with_images.get('seller_name', 'Unknown')}")
print(f"  Images: {len(listing_with_images['images'])}")

# Test staging on first image
image = listing_with_images["images"][0]
image_id = image["id"]
print(f"\n✓ Testing staging on image: {image_id}")
print(f"  Original filename: {image['original_filename']}")

# Try staging with scandinavian style
print("\nGenerating staged version (scandinavian style)...")
r = requests.post(
    f"{BASE}/api/v1/stage",
    params={"image_id": image_id, "style": "scandinavian"},
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

print("\n✓ Buyer virtual staging test passed!")
