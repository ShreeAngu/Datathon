"""Accessibility detection service."""

from PIL import Image
import numpy as np


# Estimated door width heuristic: largest vertical rectangle in detections
def _estimate_door_width(detection_result: dict, img_w: int) -> int:
    """Rough door width estimate in cm based on bounding box proportion."""
    # Standard door = ~90cm, assume image width represents ~4m room
    cm_per_px = 400 / max(img_w, 1)
    # Look for tall narrow boxes (door-like aspect ratio)
    best_w = 0
    for d in detection_result.get("detections", []):
        x1, y1, x2, y2 = d["bbox"]
        bw, bh = x2 - x1, y2 - y1
        if bh > 0 and 0.3 < (bw / bh) < 0.8:   # door-like ratio
            best_w = max(best_w, bw)
    if best_w == 0:
        return 85   # default assumption
    return int(best_w * cm_per_px)


def detect_accessibility(image_path: str, detection_result: dict = None) -> dict:
    """
    Returns accessibility analysis dict.
    """
    from app.models.detection_model import detect_objects

    if detection_result is None:
        detection_result = detect_objects(image_path)

    img      = Image.open(image_path)
    img_w, _ = img.size

    has_grab_bar  = detection_result.get("has_grab_bar", False)
    has_stairs    = detection_result.get("has_stairs", False)
    door_width_cm = _estimate_door_width(detection_result, img_w)

    # Wheelchair accessible: no stairs, door ≥ 80cm, ideally has grab bar
    is_accessible = (not has_stairs) and (door_width_cm >= 80)

    features = []
    if has_grab_bar:
        features.append("grab_bar")
    if door_width_cm >= 90:
        features.append("wide_door")
    if not has_stairs:
        features.append("step_free")

    # Score: base 50, +20 step-free, +15 wide door, +15 grab bar
    score = 50.0
    if not has_stairs:
        score += 20
    if door_width_cm >= 90:
        score += 15
    if has_grab_bar:
        score += 15

    return {
        "accessibility_score":       round(score, 1),
        "has_grab_bar":              has_grab_bar,
        "has_stairs":                has_stairs,
        "estimated_door_width_cm":   door_width_cm,
        "is_wheelchair_accessible":  is_accessible,
        "features_detected":         features,
    }
