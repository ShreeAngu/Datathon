"""Centralized API client for Property AI backend."""
import requests
import streamlit as st
from typing import Optional, Dict, Any, List

BASE = "http://localhost:8000"
API  = f"{BASE}/api/v1"


def _headers() -> Dict:
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _get(path: str, params: Dict = None) -> Optional[Dict]:
    try:
        r = requests.get(f"{API}{path}", params=params, headers=_headers(), timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        st.error(f"API {e.response.status_code}: {e.response.text[:200]}")
    except Exception as e:
        st.error(f"Connection error: {e}")
    return None


def _post(path: str, json_body: Any = None, files: Any = None,
          data: Any = None) -> Optional[Dict]:
    try:
        hdrs = _headers()
        if files:
            r = requests.post(f"{API}{path}", files=files, data=data,
                              headers=hdrs, timeout=60)
        else:
            r = requests.post(f"{API}{path}", json=json_body,
                              headers=hdrs, timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        st.error(f"API {e.response.status_code}: {e.response.text[:200]}")
    except Exception as e:
        st.error(f"Connection error: {e}")
    return None


def _delete(path: str) -> Optional[Dict]:
    try:
        r = requests.delete(f"{API}{path}", headers=_headers(), timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        st.error(f"API {e.response.status_code}: {e.response.text[:200]}")
    except Exception as e:
        st.error(f"Connection error: {e}")
    return None


def _put(path: str, json_body: Any = None) -> Optional[Dict]:
    try:
        r = requests.put(f"{API}{path}", json=json_body,
                         headers=_headers(), timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        st.error(f"API {e.response.status_code}: {e.response.text[:200]}")
    except Exception as e:
        st.error(f"Connection error: {e}")
    return None


# ── Auth ──────────────────────────────────────────────────────────────────────

def login(email: str, password: str) -> Optional[Dict]:
    r = _post("/auth/login", {"email": email, "password": password})
    if r and r.get("token"):
        st.session_state["token"]     = r["token"]
        st.session_state["user_id"]   = r["user_id"]
        st.session_state["user_type"] = r["user_type"]
        st.session_state["name"]      = r["name"]
    return r


def register(email: str, password: str, name: str, user_type: str) -> Optional[Dict]:
    r = _post("/auth/register", {"email": email, "password": password,
                                  "name": name, "user_type": user_type})
    if r and r.get("token"):
        st.session_state["token"]     = r["token"]
        st.session_state["user_id"]   = r["user_id"]
        st.session_state["user_type"] = r["user_type"]
        st.session_state["name"]      = r["name"]
    return r


def logout():
    for k in ["token", "user_id", "user_type", "name"]:
        st.session_state.pop(k, None)
    st.rerun()


# ── Seller ────────────────────────────────────────────────────────────────────

def validate_upload(file, expected_room: str = None) -> Optional[Dict]:
    files = {"file": (file.name, file.getvalue(), file.type)}
    params = {"expected_room": expected_room} if expected_room else {}
    return _post("/seller/upload/validate", files=files, data=params)


def enhance_upload(image_id: str) -> Optional[Dict]:
    return _post(f"/seller/upload/{image_id}/enhance")


def create_listing(data: Dict) -> Optional[Dict]:
    return _post("/seller/listings", data)


def get_my_listings() -> List[Dict]:
    r = _get("/seller/listings")
    return r.get("listings", []) if r else []


def update_listing(lid: str, data: Dict) -> Optional[Dict]:
    return _put(f"/seller/listings/{lid}", data)


def delete_listing(lid: str) -> Optional[Dict]:
    return _delete(f"/seller/listings/{lid}")


def publish_listing(lid: str) -> Optional[Dict]:
    return _post(f"/seller/listings/{lid}/publish")


def upload_listing_images(lid: str, files) -> Optional[Dict]:
    file_list = [("files", (f.name, f.getvalue(), f.type)) for f in files]
    try:
        r = requests.post(f"{API}/seller/listings/{lid}/images",
                          files=file_list, headers=_headers(), timeout=120)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        st.error(f"API {e.response.status_code}: {e.response.text[:200]}")
    except Exception as e:
        st.error(f"Connection error: {e}")
    return None


def extract_listing_info(files) -> Optional[Dict]:
    file_list = [("files", (f.name, f.getvalue(), f.type)) for f in files]
    try:
        r = requests.post(f"{API}/seller/upload/extract-listing-info",
                          files=file_list, headers=_headers(), timeout=120)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Extraction error: {e}")
    return None


def seller_analytics() -> Optional[Dict]:
    return _get("/seller/analytics")


def seller_messages() -> Optional[Dict]:
    return _get("/seller/messages")


def reply_message(mid: str, message: str) -> Optional[Dict]:
    try:
        r = requests.post(f"{API}/seller/messages/{mid}/reply",
                          params={"message": message},
                          headers=_headers(), timeout=30)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        st.error(f"API {e.response.status_code}: {e.response.text[:200]}")
    except Exception as e:
        st.error(f"Connection error: {e}")
    return None


def seller_investment(lid: str) -> Optional[Dict]:
    return _get(f"/seller/listings/{lid}/investment")


def get_listing_analysis(lid: str) -> Optional[Dict]:
    """Get AI analysis data for all images in a listing."""
    return _get(f"/seller/listings/{lid}/analysis")


def delete_listing_image(lid: str, image_id: str) -> Optional[Dict]:
    """Delete an image from a listing."""
    return _delete(f"/seller/listings/{lid}/images/{image_id}")


def get_listing_detail(lid: str) -> Optional[Dict]:
    """Get full listing details including images."""
    # Try buyer endpoint first (for published listings)
    result = _get(f"/buyer/listings/{lid}")
    if result:
        return result
    # Fallback to seller endpoint (for seller's own listings)
    return _get(f"/seller/listings/{lid}")


def stage_image(image_id: str, style: str = None, custom_prompt: str = None, mode: str = "furnish") -> Optional[Dict]:
    """
    Generate virtually staged version of an image.
    
    Args:
        image_id: Image UUID
        style: Predefined style (for furnish mode)
        custom_prompt: Custom prompt (for furnish mode)
        mode: "furnish" (add furniture) or "unfurnish" (remove furniture)
    """
    try:
        params = {"image_id": image_id, "mode": mode}
        if style:
            params["style"] = style
        if custom_prompt:
            params["custom_prompt"] = custom_prompt
        
        r = requests.post(f"{API}/stage",
                         params=params,
                         headers=_headers(), timeout=120)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        st.error(f"API {e.response.status_code}: {e.response.text[:200]}")
    except Exception as e:
        st.error(f"Connection error: {e}")
    return None


# ── Buyer ─────────────────────────────────────────────────────────────────────

def reverse_image_search(file, top_k: int = 10,
                         min_similarity: float = 0.3) -> Optional[Dict]:
    files = {"file": (file.name, file.getvalue(), file.type)}
    try:
        r = requests.post(
            f"{API}/buyer/search/reverse-image?top_k={top_k}&min_similarity={min_similarity}",
            files=files, headers=_headers(), timeout=120,
        )
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        st.error(f"API {e.response.status_code}: {e.response.text[:200]}")
    except Exception as e:
        st.error(f"Connection error: {e}")
    return None


def advanced_search(**params) -> Optional[Dict]:
    return _get("/buyer/search/advanced", params={k: v for k, v in params.items()
                                                   if v is not None})


def get_investment(listing_id: str) -> Optional[Dict]:
    return _get(f"/buyer/listings/{listing_id}/investment")


def get_neighborhood_score(listing_id: str) -> Optional[Dict]:
    return _get(f"/buyer/properties/{listing_id}/neighborhood-score")


def save_comparison(listing_ids: List[str]) -> Optional[Dict]:
    return _post("/buyer/properties/compare", {"listing_ids": listing_ids})


def get_comparison(listing_ids: List[str]) -> Optional[Dict]:
    return _get("/buyer/comparison", {"listing_ids": ",".join(listing_ids)})


def add_favorite(listing_id: str) -> Optional[Dict]:
    try:
        r = requests.post(f"{API}/buyer/favorites",
                          params={"listing_id": listing_id},
                          headers=_headers(), timeout=15)
        r.raise_for_status()
        return r.json()
    except requests.HTTPError as e:
        st.error(f"API {e.response.status_code}: {e.response.text[:200]}")
    except Exception as e:
        st.error(f"Connection error: {e}")
    return None


def get_favorites() -> List[Dict]:
    r = _get("/buyer/favorites")
    return r.get("favorites", []) if r else []


def remove_favorite(fav_id: str) -> Optional[Dict]:
    return _delete(f"/buyer/favorites/{fav_id}")


def get_history() -> List[Dict]:
    r = _get("/buyer/history")
    return r.get("history", []) if r else []


def contact_seller(listing_id: str, subject: str, message: str) -> Optional[Dict]:
    return _post("/buyer/contact", {"listing_id": listing_id,
                                    "subject": subject, "message": message})


# ── Admin ─────────────────────────────────────────────────────────────────────

def admin_stats() -> Optional[Dict]:
    return _get("/admin/stats")


def admin_users(page: int = 1, search: str = None) -> Optional[Dict]:
    return _get("/admin/users", {"page": page, "search": search})


def admin_listings(status: str = None, page: int = 1) -> Optional[Dict]:
    return _get("/admin/listings", {"status": status, "page": page})


def admin_suspend_user(uid: str) -> Optional[Dict]:
    return _post(f"/admin/users/{uid}/suspend")


def admin_activate_user(uid: str) -> Optional[Dict]:
    return _post(f"/admin/users/{uid}/activate")


def admin_delete_user(uid: str) -> Optional[Dict]:
    return _delete(f"/admin/users/{uid}")


def admin_update_listing_status(lid: str, status: str) -> Optional[Dict]:
    return _post(f"/admin/listings/{lid}/status", {"status": status})


# ── Helpers ───────────────────────────────────────────────────────────────────

def image_url(path: str) -> str:
    """Resolve a relative image path to full URL."""
    if not path:
        return ""
    if path.startswith("http"):
        return path
    return f"{BASE}{path}"
