"""Setup script — seed demo users and verify the backend is ready."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

import os
os.chdir(Path(__file__).parent.parent)

from app.database.connection import fetchone, execute
from app.auth.auth import hash_password
import uuid

DEMO_USERS = [
    ("admin@propertyai.demo",  "AdminDemo2026!", "admin",  "Platform Admin"),
    ("seller1@propertyai.demo","Seller123!",     "seller", "Sarah Johnson"),
    ("buyer1@propertyai.demo", "Buyer123!",      "buyer",  "James Wilson"),
]

print("🚀 Setting up Property AI FastAPI backend...")

for email, password, user_type, name in DEMO_USERS:
    existing = fetchone("SELECT id FROM users WHERE email=?", (email,))
    if existing:
        print(f"  EXISTS   {user_type:8} | {email}")
    else:
        uid = str(uuid.uuid4()).replace("-", "")
        execute(
            "INSERT INTO users(id,email,password_hash,name,user_type,is_verified,is_active) VALUES(?,?,?,?,?,1,1)",
            (uid, email, hash_password(password), name, user_type),
        )
        print(f"  CREATED  {user_type:8} | {email}")

print("\n✅ Setup complete!")
print("\n🔐 Demo credentials:")
print("  Admin  : admin@propertyai.demo   / AdminDemo2026!")
print("  Seller : seller1@propertyai.demo / Seller123!")
print("  Buyer  : buyer1@propertyai.demo  / Buyer123!")
print("\n🚀 Start server:")
print("  uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000")
print("\n📖 API docs: http://localhost:8000/docs")
