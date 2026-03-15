"""Verify buyer can see properties with images for staging."""
import requests

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
print(f"✓ Logged in as buyer")

# Get published listings (same as UI does)
print("\nFetching published listings (per_page=100)...")
r = requests.get(f"{BASE}/api/v1/buyer/search/advanced", 
                 params={"per_page": 100},
                 headers=headers)
if r.status_code != 200:
    print(f"Search failed: {r.status_code} {r.text}")
    exit(1)

listings = r.json()["listings"]
print(f"✓ Found {len(listings)} total listings")

# Filter for listings with images (same as UI does)
listings_with_images = [l for l in listings if l.get("image_url")]
print(f"✓ Found {len(listings_with_images)} listings with images")

if not listings_with_images:
    print("\n✗ No listings with images available!")
    print("This is why the UI shows 'No properties with images available for staging.'")
    exit(1)

print("\n✓ Listings available for staging:")
for i, l in enumerate(listings_with_images[:5], 1):
    print(f"  {i}. {l['title']} - {l.get('city', '')}, {l.get('state', '')}")
    print(f"     Image: {l.get('image_url')}")
    print(f"     Price: ${l.get('price', 0):,.0f}")

# Test getting full details for first listing
if listings_with_images:
    lid = listings_with_images[0]["id"]
    print(f"\n✓ Testing full listing details for: {listings_with_images[0]['title']}")
    r = requests.get(f"{BASE}/api/v1/buyer/listings/{lid}", headers=headers)
    if r.status_code == 200:
        detail = r.json()
        images = detail.get("images", [])
        print(f"  ✓ Listing has {len(images)} image(s)")
        for i, img in enumerate(images, 1):
            print(f"    {i}. {img['original_filename']} (ID: {img['id'][:16]}...)")
    else:
        print(f"  ✗ Failed to get details: {r.status_code}")

print("\n✓ Buyer staging UI should now work!")
print("\nTo test in UI:")
print("  1. Open http://localhost:8501")
print("  2. Login as buyer1@propertyai.demo / Buyer123!")
print("  3. Go to 'Buyer Dashboard' → '🎨 Virtual Staging' tab")
print("  4. You should see properties in the dropdown")
