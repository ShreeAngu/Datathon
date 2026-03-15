"""Test uploading AI-generated images to verify detection."""
import requests
from pathlib import Path

BASE_URL = "http://localhost:8000/api/v1"

# Login as seller
print("🔐 Logging in as seller...")
login_resp = requests.post(f"{BASE_URL}/auth/login", json={
    "email": "seller1@propertyai.demo",
    "password": "Seller123!"
})

if login_resp.status_code != 200:
    print(f"❌ Login failed: {login_resp.text}")
    exit(1)

token = login_resp.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

# Get first listing
listings_resp = requests.get(f"{BASE_URL}/seller/listings", headers=headers)
listings_data = listings_resp.json()
listings = listings_data.get("listings", []) if isinstance(listings_data, dict) else listings_data
listing_id = listings[0]["id"]

print(f"✅ Using listing: {listing_id}")

# Upload one real and one fake image
dataset_path = Path("dataset")
real_img = list((dataset_path / "real").glob("*.jpg"))[0]
fake_img = list((dataset_path / "fake").glob("*.jpg"))[0]

print(f"\n📤 Uploading 1 real + 1 AI-generated image...")
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
print(f"\n✅ Upload successful!")
print(f"   Average quality score: {result.get('avg_quality_score', 'N/A')}")

# Get analysis
analysis_resp = requests.get(
    f"{BASE_URL}/seller/listings/{listing_id}/analysis",
    headers=headers
)

if analysis_resp.status_code == 200:
    analysis_data = analysis_resp.json()
    analyses = analysis_data.get("analyses", [])
    
    # Get last 2 analyses (the ones we just uploaded)
    recent_analyses = analyses[-2:]
    
    print("\n🔍 AI Detection Results:")
    print("=" * 60)
    
    for item in recent_analyses:
        img = item.get("image", {})
        analysis = item.get("analysis", {})
        
        if not analysis:
            continue
        
        filename = img.get("original_filename", "N/A")
        is_ai = analysis.get("is_ai_generated") == 1
        ai_prob = analysis.get("ai_probability", 0)
        trust_score = analysis.get("trust_score", 0)
        
        print(f"\n📊 {filename}")
        print(f"   Room Type: {analysis.get('room_type', 'N/A')}")
        print(f"   Overall Quality: {analysis.get('overall_quality_score', 'N/A')}")
        print(f"   Trust Score: {trust_score}")
        print(f"   🤖 AI Generated: {'YES ⚠️' if is_ai else 'NO ✅'}")
        print(f"   🤖 AI Probability: {ai_prob}%")
        
        if is_ai:
            print(f"   ⚠️  WARNING: AI-generated image detected!")
        else:
            print(f"   ✅ Image appears authentic")

# Check listing authenticity flag
listing_resp = requests.get(f"{BASE_URL}/seller/listings/{listing_id}", headers=headers)
if listing_resp.status_code == 200:
    listing = listing_resp.json()
    auth_verified = listing.get("authenticity_verified", False)
    print(f"\n📋 Listing Authenticity Status:")
    print(f"   {'✅ All images authentic' if auth_verified else '⚠️  Contains AI-generated images'}")

print("\n✅ Test complete!")
