"""Seed multiple demo listings with confirmed real images."""
import requests, sys
sys.path.insert(0, "backend")
import os; os.chdir(".")
from pathlib import Path
from app.models.authenticity_hf_model import detect_ai_generated

BASE = "http://localhost:8000/api/v1"

# Login
r = requests.post(f"{BASE}/auth/login", json={"email": "seller1@propertyai.demo", "password": "Seller123!"})
token = r.json()["token"]
H = {"Authorization": f"Bearer {token}"}

# Find confirmed real images
print("🔍 Scanning for confirmed real images...")
real_imgs = list(Path("dataset/real").glob("*.jpg"))
confirmed_real = []
for img in real_imgs:
    result = detect_ai_generated(str(img))
    if not result["is_ai_generated"] and result["real_probability"] > 0.7:
        confirmed_real.append(img)
        print(f"  ✅ {img.name} — real_prob={result['real_probability']:.2f}")
    if len(confirmed_real) >= 5:
        break

print(f"\nFound {len(confirmed_real)} confirmed real images\n")

# Listing templates
listings_data = [
    {"title": "Modern 3BR Family Home", "description": "Spacious modern home with hardwood floors, granite countertops, updated kitchen. Large backyard, quiet neighborhood.", "price": 425000, "city": "Austin", "state": "TX", "property_type": "house", "bedrooms": 3, "bathrooms": 2, "square_feet": 1800},
    {"title": "Downtown Studio Apartment", "description": "Bright studio in prime downtown location. Stainless appliances, balcony with city views, pet-friendly building with parking.", "price": 185000, "city": "Seattle", "state": "WA", "property_type": "apartment", "bedrooms": 1, "bathrooms": 1, "square_feet": 550},
    {"title": "Luxury 4BR Colonial", "description": "Timeless colonial with formal dining room, updated kitchen, hardwood floors throughout. Prime school district, walkable neighborhood.", "price": 750000, "city": "Boston", "state": "MA", "property_type": "house", "bedrooms": 4, "bathrooms": 3, "square_feet": 2800},
]

for i, listing_info in enumerate(listings_data):
    if i >= len(confirmed_real):
        break

    # Create listing
    res = requests.post(f"{BASE}/seller/listings", headers=H, json=listing_info)
    lid = res.json()["listing_id"]
    img_path = confirmed_real[i]

    # Upload image
    files = [("files", (img_path.name, open(img_path, "rb"), "image/jpeg"))]
    upload = requests.post(f"{BASE}/seller/listings/{lid}/images", headers=H, files=files)
    files[0][1][1].close()

    result = upload.json()
    accepted = result.get("accepted_count", 0)
    rejected = result.get("rejected_count", 0)
    quality = result.get("avg_quality_score", "N/A")

    status = "✅" if accepted > 0 else "⚠️"
    print(f"{status} '{listing_info['title']}'")
    print(f"   Image: {img_path.name} → {'ACCEPTED' if accepted else 'REJECTED'}")
    print(f"   Quality: {quality}")
    if result.get("images"):
        img = result["images"][0]
        print(f"   Room: {img.get('room_type', 'N/A')} | AI: {img.get('is_ai_generated')} | URL: http://localhost:8000{img['image_url']}")
    print()

print("✅ Done! Open http://localhost:8501 → Seller Dashboard → My Listings")
