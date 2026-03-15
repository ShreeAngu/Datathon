"""Test AI detection display in seller listings."""
import requests
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"

# Login
print("🔐 Logging in as seller...")
login_resp = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "seller1@propertyai.demo",
    "password": "Seller123!"
})
token = login_resp.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

# Get or create listing
listings_resp = requests.get(f"{BASE_URL}/seller/listings", headers=headers)
listings = listings_resp.json().get("listings", [])

if not listings:
    print("Creating test listing...")
    create_resp = requests.post(f"{BASE_URL}/seller/listings", headers=headers, json={
        "title": "Beautiful Modern Home",
        "description": "Stunning property with modern amenities",
        "price": 450000,
        "city": "Seattle",
        "state": "WA",
        "property_type": "house",
        "bedrooms": 3,
        "bathrooms": 2
    })
    listing_id = create_resp.json()["listing_id"]
else:
    listing_id = listings[0]["id"]

print(f"✅ Using listing: {listing_id}")

# Upload 1 real + 1 fake image
print("\n📤 Uploading test images...")
dataset_path = Path("dataset")
real_img = list((dataset_path / "real").glob("*.jpg"))[0]
fake_img = list((dataset_path / "fake").glob("*.jpg"))[0]

print(f"   Real: {real_img.name}")
print(f"   Fake: {fake_img.name}")

files = [
    ("files", (real_img.name, open(real_img, "rb"), "image/jpeg")),
    ("files", (fake_img.name, open(fake_img, "rb"), "image/jpeg"))
]

upload_resp = requests.post(
    f"{BASE_URL}/seller/listings/{listing_id}/images",
    headers=headers,
    files=files
)

for _, (_, fh, _) in files:
    fh.close()

if upload_resp.status_code != 200:
    print(f"❌ Upload failed: {upload_resp.text}")
    exit(1)

result = upload_resp.json()
print(f"✅ Uploaded {result['count']} images")
print(f"   Average quality: {result.get('avg_quality_score', 'N/A')}")

# Now fetch the listing with analysis
print("\n📋 Fetching listing with AI detection...")
listing_resp = requests.get(f"{BASE_URL}/seller/listings/{listing_id}", headers=headers)
listing = listing_resp.json()

print(f"\n🏠 {listing['title']}")
print(f"   Price: ${listing.get('price', 0):,.0f}")
print(f"   Status: {listing['status']}")
print(f"   Quality Score: {listing.get('overall_quality_score', 'N/A')}")
print(f"   Authenticity: {'✅ Verified' if listing.get('authenticity_verified') else '⚠️  Contains AI images'}")

# Get analysis data
analysis_resp = requests.get(f"{BASE_URL}/seller/listings/{listing_id}/analysis", headers=headers)
if analysis_resp.status_code == 200:
    analysis_data = analysis_resp.json()
    analyses = analysis_data.get("analyses", [])
    
    print(f"\n📸 Images ({len(analyses)}):")
    print("=" * 70)
    
    for item in analyses:
        img = item.get("image", {})
        analysis = item.get("analysis", {})
        
        if analysis:
            filename = img.get("original_filename", "Unknown")
            is_ai = analysis.get("is_ai_generated") == 1
            ai_prob = analysis.get("ai_probability", 0)
            quality = analysis.get("overall_quality_score", 0)
            room = analysis.get("room_type", "unknown")
            
            # Apply 70% confidence threshold
            show_confidence = max(ai_prob, 100 - ai_prob) >= 70
            
            print(f"\n📷 {filename}")
            print(f"   Room: {room.replace('_', ' ').title()}")
            print(f"   Quality: {quality:.0f}/100")
            
            if is_ai:
                if show_confidence:
                    print(f"   Status: 🤖 AI GENERATED ({ai_prob:.0f}%)")
                else:
                    print(f"   Status: ❓ UNCERTAIN")
            else:
                if show_confidence:
                    print(f"   Status: ✅ REAL ({100-ai_prob:.0f}%)")
                else:
                    print(f"   Status: ❓ UNCERTAIN")

print("\n" + "=" * 70)
print("\n✅ This is what sellers see in 'My Listings' tab!")
print("\n💡 Open http://localhost:8501 and go to:")
print("   Seller Dashboard → My Listings → Expand the listing")
print("   You'll see the AI detection status for each image!")
