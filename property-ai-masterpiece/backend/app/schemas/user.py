from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    user_type: str = "buyer"
    phone: Optional[str] = None


class UserLogin(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    user_type: str
    is_verified: bool
    is_active: bool
    created_at: Optional[str] = None

    class Config:
        from_attributes = True


class Token(BaseModel):
    token: str
    user_id: str
    user_type: str
    name: str
