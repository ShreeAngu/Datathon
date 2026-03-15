"""Composite quality scoring service."""

import cv2
import numpy as np
from PIL import Image


def _sharpness_score(image_path: str) -> float:
    """Laplacian variance — higher = sharper."""
    img  = cv2.imread(image_path)
    if img is None:
        return 50.0
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    lap_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    return round(min(100.0, lap_var / 10), 1)


def _composition_score(image_path: str) -> float:
    """
    Rule-of-thirds proxy: check if high-contrast regions align with thirds grid.
    """
    img  = cv2.imread(image_path)
    if img is None:
        return 50.0
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    edges = cv2.Canny(gray, 50, 150)

    # Sample edge density at rule-of-thirds intersections
    pts = [(w//3, h//3), (2*w//3, h//3), (w//3, 2*h//3), (2*w//3, 2*h//3)]
    margin = max(10, min(w, h) // 20)
    scores = []
    for cx, cy in pts:
        region = edges[max(0,cy-margin):cy+margin, max(0,cx-margin):cx+margin]
        scores.append(region.mean())

    base = float(np.mean(scores))
    return round(min(100.0, 40 + base * 1.5), 1)


def _resolution_score(image_path: str) -> float:
    """Score based on megapixels."""
    img = Image.open(image_path)
    mp  = (img.width * img.height) / 1_000_000
    return round(min(100.0, mp * 20), 1)   # 5MP → 100


def calculate_quality_score(image_path: str, spatial: dict,
                             authenticity: dict, accessibility: dict) -> dict:
    """
    Composite score:
      40% spatial  (lighting 20%, clutter inverse 10%, spaciousness 10%)
      30% authenticity (trust score)
      20% technical (sharpness 10%, resolution 5%, composition 5%)
      10% accessibility
    """
    sharpness   = _sharpness_score(image_path)
    composition = _composition_score(image_path)
    resolution  = _resolution_score(image_path)

    lighting    = spatial.get("lighting_quality", 50)
    clutter_inv = 100 - spatial.get("clutter_score", 50)
    spacious    = spatial.get("spaciousness_score", 50)
    trust       = authenticity.get("trust_score", 50)
    access      = accessibility.get("accessibility_score", 50)

    spatial_score = lighting * 0.20 + clutter_inv * 0.10 + spacious * 0.10
    auth_score    = trust * 0.30
    tech_score    = sharpness * 0.10 + resolution * 0.05 + composition * 0.05
    access_score  = access * 0.10

    overall = round(spatial_score + auth_score + tech_score + access_score, 1)

    # Recommendations
    recs = []
    if lighting < 60:
        recs.append("Improve natural lighting (+5 pts)")
    if spatial.get("clutter_score", 0) > 50:
        recs.append("Reduce clutter in foreground (+4 pts)")
    if sharpness < 40:
        recs.append("Increase image sharpness/focus (+3 pts)")
    if spacious < 40:
        recs.append("Wider angle would improve spaciousness perception (+2 pts)")

    return {
        "overall_score":     overall,
        "lighting_score":    round(lighting, 1),
        "composition_score": composition,
        "sharpness_score":   sharpness,
        "resolution_score":  resolution,
        "trust_component":   round(trust * 0.30, 1),
        "recommendations":   recs,
    }
