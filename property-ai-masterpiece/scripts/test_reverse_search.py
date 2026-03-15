import requests

# Login
r = requests.post("http://localhost:8000/api/v1/auth/login",
                  json={"email": "buyer1@propertyai.demo", "password": "Buyer123!"})
token = r.json()["token"]
headers = {"Authorization": f"Bearer {token}"}

# Test reverse search with an existing upload
img_path = "dataset/uploads/76a58247d43b4a58b4015ed8ea144ccb.jpeg"
with open(img_path, "rb") as f:
    resp = requests.post(
        "http://localhost:8000/api/v1/buyer/search/reverse-image?top_k=5&min_similarity=0.2",
        files={"file": ("test.jpeg", f, "image/jpeg")},
        headers=headers,
        timeout=60,
    )

print("Status:", resp.status_code)
print("Response:", resp.text[:2000])
