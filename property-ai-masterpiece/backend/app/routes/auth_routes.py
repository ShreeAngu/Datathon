"""Authentication routes — register, login, profile."""

import uuid
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr

from app.database.connection import fetchone, execute
from app.auth.auth import hash_password, verify_password, create_token, get_current_user

router = APIRouter()


class RegisterBody(BaseModel):
    email: str
    password: str
    name: str
    user_type: str = "buyer"


class LoginBody(BaseModel):
    email: str
    password: str


@router.post("/register")
def register(body: RegisterBody):
    if fetchone("SELECT id FROM users WHERE email=?", (body.email,)):
        raise HTTPException(400, "Email already registered")
    uid = str(uuid.uuid4()).replace("-", "")
    execute(
        "INSERT INTO users(id,email,password_hash,name,user_type) VALUES(?,?,?,?,?)",
        (uid, body.email, hash_password(body.password), body.name, body.user_type),
    )
    token = create_token(uid, body.user_type)
    return {"token": token, "user_id": uid, "user_type": body.user_type, "name": body.name}


@router.post("/login")
def login(body: LoginBody):
    user = fetchone("SELECT * FROM users WHERE email=? AND is_active=1", (body.email,))
    if not user or not verify_password(body.password, user["password_hash"]):
        raise HTTPException(401, "Invalid credentials")
    token = create_token(user["id"], user["user_type"])
    return {"token": token, "user_id": user["id"],
            "user_type": user["user_type"], "name": user["name"]}


@router.get("/me")
def me(current=Depends(get_current_user)):
    user = fetchone("SELECT id,email,name,user_type,is_verified,created_at FROM users WHERE id=?",
                    (current["sub"],))
    if not user:
        raise HTTPException(404, "User not found")
    return user
