"""Seed a demo listing with a real image for visual testing."""
import requests, shutil
from pathlib import Path

BASE = "http://localhost:8000/api/v1"

# Login
r = requests.post(f"{BASE}/auth/login", json={"email": "seller1@propertyai.demo", "password": "Seller123!"})
token = r.json()["token"]
H = {"Authorization": f"Bearer {token}"}

# Create listing
print("Creating demo listing...")
res = requests.post(f"{BASE}/seller/listings", headers=H, json={
    "title": "Cozy 3BR Family Home",
    "description": "Spacious modern home with hardwood floors, granite countertops, updated kitchen and bathrooms. Large backyard, quiet neighborhood, close to schools and parks.",
    "price": 425000, "city": "Austin", "state": "TX",
    "property_type": "house", "bedrooms": 3, "bathrooms": 2, "square_feet": 1800
})
lid = res.json()["listing_id"]
print(f"  Listing ID: {lid}")

# Find a real image from dataset - use one confirmed as real by model
dataset = Path("dataset")
real_imgs = list((dataset / "real").glob("*.jpg"))
fake_imgs = list((dataset / "fake").glob("*.jpg"))

if not real_imgs:
    print("No real images found in dataset/real/")
    exit(1)

# Use real_80c0YaiSFk4.jpg which is confirmed real by the model
confirmed_real = dataset / "real" / "real_80c0YaiSFk4.jpg"
real_img = confirmed_real if confirmed_real.exists() else real_imgs[0]
print(f"\nUploading real image: {real_img.name}")

files = [("files", (real_img.name, open(real_img, "rb"), "image/jpeg"))]
upload = requests.post(f"{BASE}/seller/listings/{lid}/images", headers=H, files=files)
files[0][1][1].close()

result = upload.json()
print(f"\n=== UPLOAD RESULT ===")
print(f"Accepted: {result.get('accepted_count', 0)}")
print(f"Rejected: {result.get('rejected_count', 0)}")
print(f"Avg Quality: {result.get('avg_quality_score', 'N/A')}")

if result.get("images"):
    for img in result["images"]:
        print(f"\n✅ ACCEPTED: {img['filename']}")
        print(f"   URL: http://localhost:8000{img['image_url']}")
        print(f"   Quality: {img.get('overall_quality', 'N/A')}")
        print(f"   Room: {img.get('room_type', 'N/A')}")
        print(f"   AI: {img.get('is_ai_generated', 'N/A')}")

if result.get("rejected_images"):
    for rej in result["rejected_images"]:
        print(f"\n🚫 REJECTED: {rej['filename']}")
        print(f"   Reason: {rej['reason']}")
        print(f"   AI Prob: {rej.get('ai_probability', 0):.1f}%")

print(f"\n✅ Done! Open http://localhost:8501 → Seller Dashboard → My Listings")
print(f"   Listing ID: {lid}")
