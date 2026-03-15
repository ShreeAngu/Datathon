import requests

API = "http://localhost:8000"

# 1. Register a test seller
print("=== Register seller ===")
r = requests.post(f"{API}/api/v1/auth/register", json={
    "email": "seller_test@test.com",
    "password": "test1234",
    "name": "Test Seller",
    "user_type": "seller"
})
print(r.status_code, r.text[:300])

# 2. Login
print("\n=== Login ===")
r = requests.post(f"{API}/api/v1/auth/login", json={
    "email": "seller_test@test.com",
    "password": "test1234"
})
print(r.status_code, r.text[:300])
if not r.ok:
    print("LOGIN FAILED - stopping")
    exit(1)

token = r.json()["token"]
hdrs = {"Authorization": f"Bearer {token}"}

# 3. List listings
print("\n=== GET /seller/listings ===")
r = requests.get(f"{API}/api/v1/seller/listings", headers=hdrs)
print(r.status_code, r.text[:300])

# 4. Create listing
print("\n=== POST /seller/listings ===")
r = requests.post(f"{API}/api/v1/seller/listings", headers=hdrs, json={
    "title": "Test Property",
    "description": "A nice place",
    "city": "Austin",
    "state": "TX",
    "price": 350000,
    "property_type": "house",
    "bedrooms": 3,
    "bathrooms": 2.0,
    "square_feet": 1800,
    "year_built": 2010
})
print(r.status_code, r.text[:300])

# 5. Analytics
print("\n=== GET /seller/analytics ===")
r = requests.get(f"{API}/api/v1/seller/analytics", headers=hdrs)
print(r.status_code, r.text[:300])

# 6. Messages
print("\n=== GET /seller/messages ===")
r = requests.get(f"{API}/api/v1/seller/messages", headers=hdrs)
print(r.status_code, r.text[:300])
