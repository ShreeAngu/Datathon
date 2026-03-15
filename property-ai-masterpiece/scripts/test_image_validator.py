"""Test the image validation endpoint with a real image from the dataset."""
import requests
from pathlib import Path
import json

API = "http://localhost:8000"

# Login as seller
r = requests.post(f"{API}/api/v1/auth/login",
                  json={"email": "seller1@propertyai.demo", "password": "Seller123!"})
if not r.ok:
    print(f"Login failed: {r.text}")
    exit(1)
token = r.json()["token"]
hdrs  = {"Authorization": f"Bearer {token}"}
print(f"Logged in as seller1@propertyai.demo")

# Find a test image
test_img = None
for p in Path("dataset/real").rglob("*.jpg"):
    test_img = p
    break

if not test_img:
    print("No test image found in dataset/real/")
    exit(1)

print(f"Testing with: {test_img}")

# Test /upload/validate
with open(test_img, "rb") as f:
    r = requests.post(f"{API}/api/v1/seller/upload/validate",
                      headers=hdrs,
                      files={"file": (test_img.name, f, "image/jpeg")},
                      params={"expected_room": "living room"})

print(f"\nStatus: {r.status_code}")
if r.ok:
    d = r.json()
    print(f"Room type      : {d['verified_room_type']} (conf={d['room_confidence']:.2f}, matches={d['matches_expected']})")
    print(f"Lighting       : {d['lighting_score']:.0f}/100 — {d['lighting_feedback']}")
    print(f"Clutter        : {d['clutter_score']:.0f}/100 — {d['clutter_object_count']} objects — {d['clutter_locations']}")
    print(f"AI generated   : {d['is_ai_generated']} ({d['ai_probability']:.1f}%)")
    print(f"Duplicate      : {d['is_duplicate']}")
    print(f"Composition    : {d['composition_score']:.0f}/100 — issues: {d['composition_issues']}")
    print(f"Overall quality: {d['overall_quality']:.0f}/100")
    print(f"Processing     : {d['processing_time_ms']:.0f}ms")
    print(f"\nTop recommendations:")
    for rec in d["recommendations"][:3]:
        print(f"  [{rec['priority'].upper()}] {rec['action']}")
        print(f"         Impact: {rec['impact']} | Auto-fix: {rec['auto_fixable']}")

    # Test enhance
    iid = d.get("temp_image_id")
    if iid:
        r2 = requests.post(f"{API}/api/v1/seller/upload/{iid}/enhance", headers=hdrs)
        print(f"\nEnhance status: {r2.status_code} — {r2.json()}")
else:
    print(r.text[:500])
