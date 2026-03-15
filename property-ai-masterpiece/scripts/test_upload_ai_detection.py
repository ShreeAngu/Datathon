"""Test that uploaded images are checked for AI-generated content."""
import requests
import json
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

auth_data = login_resp.json()
token = auth_data.get("token") or auth_data.get("access_token")
if not token:
    print(f"❌ No token in response: {auth_data}")
    exit(1)

headers = {"Authorization": f"Bearer {token}"}

# Get first listing
print("\n📋 Getting seller's listings...")
listings_resp = requests.get(f"{BASE_URL}/seller/listings", headers=headers)
if listings_resp.status_code != 200:
    print(f"❌ Failed to get listings: {listings_resp.text}")
    exit(1)

listings_data = listings_resp.json()
# Handle both list and dict responses
if isinstance(listings_data, dict):
    listings = listings_data.get("listings", [])
else:
    listings = listings_data

if not listings:
    print("❌ No listings found. Create a listing first.")
    exit(1)

listing_id = listings[0]["id"]
print(f"✅ Using listing: {listing_id}")

# Find test images
dataset_path = Path("dataset/uploads")
test_images = list(dataset_path.glob("*.jpg"))[:2]  # Upload 2 images

if not test_images:
    print("❌ No test images found in dataset/uploads/")
    exit(1)

print(f"\n📤 Uploading {len(test_images)} images to listing...")
files = [("files", (img.name, open(img, "rb"), "image/jpeg")) for img in test_images]

upload_resp = requests.post(
    f"{BASE_URL}/seller/listings/{listing_id}/images",
    headers=headers,
    files=files
)

# Close file handles
for _, (_, fh, _) in files:
    fh.close()

if upload_resp.status_code != 200:
    print(f"❌ Upload failed: {upload_resp.text}")
    exit(1)

result = upload_resp.json()
print(f"\n✅ Upload successful!")
print(f"   Images uploaded: {result['count']}")
print(f"   Average quality score: {result.get('avg_quality_score', 'N/A')}")

# Get detailed analysis for each image
print("\n🔍 Checking AI detection results...")

# Query image_analysis table via listing analysis endpoint
analysis_resp = requests.get(
    f"{BASE_URL}/seller/listings/{listing_id}/analysis",
    headers=headers
)

if analysis_resp.status_code == 200:
    analysis_data = analysis_resp.json()
    analyses = analysis_data.get("analyses", [])
    
    for item in analyses:
        img = item.get("image", {})
        analysis = item.get("analysis", {})
        
        if not analysis:
            print(f"\n📊 Image: {img.get('original_filename', 'N/A')}")
            print("   ⚠️  No analysis data found")
            continue
        
        print(f"\n📊 Image: {img.get('original_filename', 'N/A')}")
        print(f"   Room Type: {analysis.get('room_type', 'N/A')}")
        print(f"   Overall Quality: {analysis.get('overall_quality_score', 'N/A')}")
        print(f"   Lighting Score: {analysis.get('lighting_quality_score', 'N/A')}")
        print(f"   Clutter Score: {analysis.get('clutter_score', 'N/A')}")
        print(f"   Trust Score: {analysis.get('trust_score', 'N/A')}")
        print(f"   🤖 AI Generated: {'Yes' if analysis.get('is_ai_generated') == 1 else 'No'}")
        print(f"   🤖 AI Probability: {analysis.get('ai_probability', 0)}%")
        
        if analysis.get('is_ai_generated') == 1:
            print("   ⚠️  WARNING: This image was detected as AI-generated!")
        else:
            print("   ✅ Image appears to be authentic")
else:
    print(f"❌ Failed to get analysis: {analysis_resp.text}")

# Check listing authenticity flag
print("\n📋 Checking listing authenticity status...")
listing_resp = requests.get(
    f"{BASE_URL}/seller/listings/{listing_id}",
    headers=headers
)

if listing_resp.status_code == 200:
    listing = listing_resp.json()
    auth_verified = listing.get("authenticity_verified", False)
    print(f"   Authenticity Verified: {'✅ Yes' if auth_verified else '❌ No (AI images detected)'}")
    print(f"   Overall Quality Score: {listing.get('overall_quality_score', 'N/A')}")

print("\n✅ Test complete!")
