"""Test the analyze section features."""
import requests
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"

# Login as seller
print("🔐 Logging in as seller...")
login_resp = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "seller1@propertyai.demo",
    "password": "Seller123!"
})

token = login_resp.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

# Get first listing
listings_resp = requests.get(f"{BASE_URL}/seller/listings", headers=headers)
listings_data = listings_resp.json()
listings = listings_data.get("listings", []) if isinstance(listings_data, dict) else listings_data
listing_id = listings[0]["id"]

print(f"✅ Using listing: {listing_id}")

# Test 1: Get analysis data
print("\n📊 Test 1: Get Analysis Data")
analysis_resp = requests.get(f"{BASE_URL}/seller/listings/{listing_id}/analysis", headers=headers)
if analysis_resp.status_code == 200:
    data = analysis_resp.json()
    print(f"   Found {data.get('image_count', 0)} images")
    analyses = data.get("analyses", [])
    for item in analyses[:2]:  # Show first 2
        img = item.get("image", {})
        analysis = item.get("analysis", {})
        if analysis:
            print(f"\n   📷 {img.get('original_filename', 'N/A')}")
            print(f"      Quality: {analysis.get('overall_quality_score', 'N/A')}/100")
            print(f"      AI Generated: {analysis.get('is_ai_generated', 0) == 1}")
            print(f"      AI Probability: {analysis.get('ai_probability', 0)}%")
            print(f"      Trust Score: {analysis.get('trust_score', 0)}/100")
else:
    print(f"   ❌ Failed: {analysis_resp.text}")

# Test 2: Delete an image
if analyses:
    print("\n🗑️  Test 2: Delete Image")
    first_img = analyses[0].get("image", {})
    img_id = first_img.get("id")
    
    if img_id:
        delete_resp = requests.delete(
            f"{BASE_URL}/seller/listings/{listing_id}/images/{img_id}",
            headers=headers
        )
        if delete_resp.status_code == 200:
            print(f"   ✅ Deleted image: {first_img.get('original_filename', 'N/A')}")
            
            # Check updated listing
            listing_resp = requests.get(f"{BASE_URL}/seller/listings/{listing_id}", headers=headers)
            if listing_resp.status_code == 200:
                listing = listing_resp.json()
                print(f"   Updated quality score: {listing.get('overall_quality_score', 'N/A')}")
        else:
            print(f"   ❌ Failed: {delete_resp.text}")

# Test 3: Create listing with keyword generation
print("\n🔑 Test 3: Keyword Generation")
create_resp = requests.post(f"{BASE_URL}/seller/listings", headers=headers, json={
    "title": "Luxury Modern Condo",
    "description": "Beautiful modern condo with stunning views. Features include hardwood floors, "
                   "granite countertops, stainless steel appliances, and a spacious balcony. "
                   "Located in prime downtown location near shopping, dining, and transit. "
                   "Pet-friendly building with parking and laundry facilities.",
    "price": 450000,
    "property_type": "condo",
    "bedrooms": 2,
    "bathrooms": 2,
    "city": "Seattle",
    "state": "WA"
})

if create_resp.status_code == 200:
    result = create_resp.json()
    keywords = result.get("keywords", [])
    print(f"   ✅ Generated {len(keywords)} keywords:")
    print(f"   {', '.join(keywords[:15])}")
    if len(keywords) > 15:
        print(f"   ...and {len(keywords) - 15} more")
    
    # Clean up - delete the test listing
    test_lid = result.get("listing_id")
    if test_lid:
        requests.delete(f"{BASE_URL}/seller/listings/{test_lid}", headers=headers)
else:
    print(f"   ❌ Failed: {create_resp.text}")

print("\n✅ All tests complete!")
