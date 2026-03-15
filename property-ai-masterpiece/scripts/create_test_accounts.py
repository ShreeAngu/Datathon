import requests

API = "http://localhost:8000"

accounts = [
    {"email": "seller@demo.com",  "password": "seller123", "name": "Demo Seller", "user_type": "seller"},
    {"email": "buyer@demo.com",   "password": "buyer123",  "name": "Demo Buyer",  "user_type": "buyer"},
    {"email": "admin@demo.com",   "password": "admin123",  "name": "Demo Admin",  "user_type": "admin"},
]

for acc in accounts:
    r = requests.post(f"{API}/api/v1/auth/register", json=acc)
    if r.ok:
        print(f"CREATED  {acc['user_type']:8} | {acc['email']:22} | password: {acc['password']}")
    elif r.status_code == 400:
        # already exists, try login to confirm it works
        r2 = requests.post(f"{API}/api/v1/auth/login", json={"email": acc["email"], "password": acc["password"]})
        if r2.ok:
            print(f"EXISTS   {acc['user_type']:8} | {acc['email']:22} | password: {acc['password']}")
        else:
            print(f"FAILED   {acc['user_type']:8} | {acc['email']:22} | {r.text[:80]}")
    else:
        print(f"ERROR    {acc['user_type']:8} | {acc['email']:22} | {r.text[:80]}")
