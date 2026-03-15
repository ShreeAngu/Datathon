"""Test that only REAL images are uploaded, AI images are rejected."""
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

# Create new listing
print("\n📝 Creating new test listing...")
create_resp = requests.post(f"{BASE_URL}/seller/listings", headers=headers, json={
    "title": "Real Images Only Test",
    "description": "Testing real image upload filter",
    "price": 350000,
    "city": "Seattle",
    "state": "WA",
    "property_type": "house",
    "bedrooms": 3,
    "bathrooms": 2
})
listing_id = create_resp.json()["listing_id"]
print(f"✅ Created listing: {listing_id}")

# Try to upload 1 real + 1 fake image
print("\n📤 Attempting to upload 1 REAL + 1 AI-GENERATED image...")
dataset_path = Path("dataset")

# Get one real and one fake image
real_images = list((dataset_path / "real").glob("*.jpg"))
fake_images = list((dataset_path / "fake").glob("*.jpg"))

if not real_images or not fake_images:
    print("❌ Test images not found")
    exit(1)

real_img = real_images[0]
fake_img = fake_images[0]

print(f"   📷 Real: {real_img.name}")
print(f"   🤖 Fake: {fake_img.name}")

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

print("\n" + "=" * 70)
print("UPLOAD RESULTS:")
print("=" * 70)

if upload_resp.status_code == 200:
    result = upload_resp.json()
    
    accepted = result.get("accepted_count", 0)
    rejected = result.get("rejected_count", 0)
    accepted_images = result.get("images", [])
    rejected_images = result.get("rejected_images", [])
    
    print(f"\n✅ Accepted: {accepted} image(s)")
    for img in accepted_images:
        print(f"   • {img['filename']}")
    
    print(f"\n🚫 Rejected: {rejected} image(s)")
    for rej in rejected_images:
        print(f"   • {rej['filename']}")
        print(f"     Reason: {rej['reason']}")
        print(f"     AI Probability: {rej['ai_probability']:.1f}%")
    
    if result.get("avg_quality_score"):
        print(f"\n📊 Average Quality Score: {result['avg_quality_score']:.1f}/100")
else:
    print(f"❌ Upload failed: {upload_resp.status_code}")
    print(upload_resp.text)

# Verify listing only has real images
print("\n" + "=" * 70)
print("LISTING VERIFICATION:")
print("=" * 70)

listing_resp = requests.get(f"{BASE_URL}/seller/listings/{listing_id}", headers=headers)
if listing_resp.status_code == 200:
    listing = listing_resp.json()
    images = listing.get("images", [])
    
    print(f"\n🏠 Listing: {listing['title']}")
    print(f"   Images in listing: {len(images)}")
    print(f"   Authenticity Verified: {'✅ Yes' if listing.get('authenticity_verified') else '❌ No'}")
    
    if images:
        print(f"\n📸 Images stored in listing:")
        for img in images:
            print(f"   • {img['original_filename']}")

# Get analysis to verify
analysis_resp = requests.get(f"{BASE_URL}/seller/listings/{listing_id}/analysis", headers=headers)
if analysis_resp.status_code == 200:
    analysis_data = analysis_resp.json()
    analyses = analysis_data.get("analyses", [])
    
    print(f"\n🔍 Analysis Results:")
    for item in analyses:
        img = item.get("image", {})
        analysis = item.get("analysis", {})
        if analysis:
            filename = img.get("original_filename")
            is_ai = analysis.get("is_ai_generated") == 1
            ai_prob = analysis.get("ai_probability", 0)
            
            status = "🤖 AI" if is_ai else "✅ REAL"
            print(f"   {status} {filename} ({ai_prob:.0f}% AI probability)")

print("\n" + "=" * 70)
print("\n✅ TEST COMPLETE!")
print("\nExpected behavior:")
print("  • Only REAL images should be accepted and stored")
print("  • AI-generated images should be rejected")
print("  • Listing should show authenticity_verified = True")
print("  • Only real images appear in listing")

# Cleanup
print(f"\n🗑️  Cleaning up test listing...")
requests.delete(f"{BASE_URL}/seller/listings/{listing_id}", headers=headers)
print("✅ Done!")
