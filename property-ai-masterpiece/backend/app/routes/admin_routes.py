"""Admin routes — user management, moderation, platform analytics."""

import pathlib
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.database.connection import fetchall, fetchone, execute
from app.auth.auth import require_role

router = APIRouter()
admin_only = require_role("admin")


@router.get("/stats")
@router.get("/analytics")
def platform_analytics(current=Depends(admin_only)):
    users     = fetchone("SELECT COUNT(*) n FROM users")["n"]
    active    = fetchone("SELECT COUNT(*) n FROM users WHERE is_active=1")["n"]
    listings  = fetchone("SELECT COUNT(*) n FROM listings")["n"]
    published = fetchone("SELECT COUNT(*) n FROM listings WHERE status='published'")["n"]
    images    = fetchone("SELECT COUNT(*) n FROM images")["n"]
    buyers    = fetchone("SELECT COUNT(*) n FROM users WHERE user_type IN ('buyer','both')")["n"]
    sellers   = fetchone("SELECT COUNT(*) n FROM users WHERE user_type IN ('seller','both')")["n"]
    admins    = fetchone("SELECT COUNT(*) n FROM users WHERE user_type='admin'")["n"]
    return {
        "total_users":        users,
        "active_users":       active,
        "buyers":             buyers,
        "sellers":            sellers,
        "admins":             admins,
        "total_listings":     listings,
        "published_listings": published,
        "draft_listings":     fetchone("SELECT COUNT(*) n FROM listings WHERE status='draft'")["n"],
        "total_images":       images,
    }


@router.get("/users")
def list_users(page: int = 1, search: str = None, current=Depends(admin_only)):
    per_page = 20
    offset   = (page - 1) * per_page
    if search:
        rows  = fetchall(
            "SELECT id,email,name,user_type,is_active,created_at FROM users "
            "WHERE name LIKE ? OR email LIKE ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (f"%{search}%", f"%{search}%", per_page, offset))
        total = fetchone(
            "SELECT COUNT(*) n FROM users WHERE name LIKE ? OR email LIKE ?",
            (f"%{search}%", f"%{search}%"))["n"]
    else:
        rows  = fetchall(
            "SELECT id,email,name,user_type,is_active,created_at FROM users "
            "ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (per_page, offset))
        total = fetchone("SELECT COUNT(*) n FROM users")["n"]
    return {"users": rows, "total": total, "page": page}


@router.post("/users/{uid}/suspend")
@router.put("/users/{uid}/suspend")
def suspend_user(uid: str, current=Depends(admin_only)):
    execute("UPDATE users SET is_active=0 WHERE id=?", (uid,))
    return {"status": "suspended"}


@router.post("/users/{uid}/activate")
@router.put("/users/{uid}/activate")
def activate_user(uid: str, current=Depends(admin_only)):
    execute("UPDATE users SET is_active=1 WHERE id=?", (uid,))
    return {"status": "activated"}


@router.delete("/users/{uid}")
def delete_user(uid: str, current=Depends(admin_only)):
    execute("DELETE FROM users WHERE id=?", (uid,))
    return {"status": "deleted"}


@router.get("/listings")
def all_listings(page: int = 1, status: str = None, current=Depends(admin_only)):
    per_page = 20
    offset   = (page - 1) * per_page
    where    = "WHERE l.status=?" if status else ""
    params   = (status, per_page, offset) if status else (per_page, offset)
    rows = fetchall(
        f"""SELECT l.*, u.name seller_name, u.email seller_email
            FROM listings l LEFT JOIN users u ON u.id=l.seller_id
            {where} ORDER BY l.created_at DESC LIMIT ? OFFSET ?""",
        params,
    )
    total = fetchone(
        f"SELECT COUNT(*) n FROM listings l {where}",
        (status,) if status else (),
    )["n"]
    return {"listings": rows, "total": total, "page": page}


class StatusBody(BaseModel):
    status: str


@router.post("/listings/{lid}/status")
@router.put("/listings/{lid}/moderate")
def moderate_listing(lid: str, body: StatusBody = None, status: str = None,
                     current=Depends(admin_only)):
    new_status = (body.status if body else None) or status
    if not new_status:
        raise HTTPException(400, "status required")
    execute("UPDATE listings SET status=? WHERE id=?", (new_status, lid))
    return {"status": "updated"}
