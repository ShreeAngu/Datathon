"""Test reverse staging as buyer."""
import requests

BASE = "http://localhost:8000"

# Login as buyer
print("Logging in as buyer1...")
r = requests.post(f"{BASE}/api/v1/auth/login", json={
    "email": "buyer1@propertyai.demo",
    "password": "Buyer123!"
})
token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}
print("✓ Logged in\n")

# Get published listings
print("Fetching published listings...")
r = requests.get(f"{BASE}/api/v1/buyer/search/advanced", 
                 params={"per_page": 5},
                 headers=headers)
listings = r.json()["listings"]
print(f"✓ Found {len(listings)} listing(s)\n")

# Get first listing with images
listing_with_images = None
for listing in listings:
    lid = listing["id"]
    r = requests.get(f"{BASE}/api/v1/buyer/listings/{lid}", headers=headers)
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

# Test: Unfurnish mode (remove furniture)
print("="*60)
print("TEST: Unfurnish Mode - Remove Furniture & Show Empty Room")
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
    print(f"  Tier: {result.get('tier')}")
    print(f"  Processing time: {result.get('processing_time')}s")
    print(f"  Staged image: {result.get('staged_image_url')}")
    print(f"  Original image: {result.get('original_image_url')}")
    print(f"\n  Changes made:")
    for change in result.get('changes_made', []):
        print(f"    • {change}")
    print(f"\n  Preserved elements:")
    for elem in result.get('preserved_elements', []):
        print(f"    • {elem}")
else:
    print(f"✗ Failed: {r.status_code}")
    print(r.text)

print("\n" + "="*60)
print("✓ Reverse staging test complete!")
print("="*60)
print("\nUse Cases:")
print("  • Buyers can see actual room dimensions")
print("  • Visualize their own furniture placement")
print("  • Understand floor space and layout")
print("  • Compare empty vs furnished versions")
