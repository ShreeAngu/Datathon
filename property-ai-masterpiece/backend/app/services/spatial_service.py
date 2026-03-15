"""Spatial analysis service — room type, style, clutter, lighting, depth."""

import cv2
import numpy as np
from PIL import Image
from pathlib import Path

# Room type classifier using CLIP zero-shot
ROOM_LABELS = [
    "living room", "kitchen", "bedroom", "bathroom", "hallway",
    "staircase", "dining room", "home office", "garage", "basement",
]

STYLE_LABELS = [
    "modern minimalist", "traditional classic", "scandinavian",
    "industrial", "bohemian", "farmhouse", "luxury contemporary",
    "outdated retro", "cluttered messy",
]


def _classify_with_clip(image_path: str, labels: list[str]) -> tuple[str, float]:
    from app.models.clip_model import get_image_embedding, get_text_embedding
    import numpy as np

    img_emb   = get_image_embedding(image_path)
    scores    = []
    for label in labels:
        txt_emb = get_text_embedding(f"a photo of a {label}")
        scores.append(float(np.dot(img_emb, txt_emb)))

    best_idx  = int(np.argmax(scores))
    # Softmax confidence
    exp_s     = np.exp(np.array(scores) - max(scores))
    conf      = float(exp_s[best_idx] / exp_s.sum())
    return labels[best_idx], round(conf, 4)


def _lighting_score(img_array: np.ndarray) -> float:
    """Score 0-100 based on brightness distribution and contrast."""
    gray    = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY).astype(float)
    mean_b  = gray.mean()
    std_b   = gray.std()
    # Penalise very dark (<40) or blown-out (>220) images
    dark_penalty  = max(0, 40 - mean_b) * 1.5
    blown_penalty = max(0, mean_b - 220) * 2.0
    contrast_bonus = min(30, std_b * 0.4)
    score = min(100, max(0, 50 + (mean_b - 128) * 0.2 + contrast_bonus
                         - dark_penalty - blown_penalty))
    return round(float(score), 1)


def _clutter_score(detection_result: dict) -> float:
    """0-100 clutter score based on detected object density."""
    clutter_cnt  = detection_result.get("clutter_count", 0)
    raw_cnt      = detection_result.get("raw_count", 0)
    # More objects per frame = more clutter
    score = min(100, (clutter_cnt * 8) + (raw_cnt * 2))
    return round(float(score), 1)


def analyze_spatial(image_path: str, detection_result: dict = None,
                    depth_result: tuple = None) -> dict:
    """
    Returns spatial analysis dict.
    Accepts pre-computed detection/depth results to avoid re-running models.
    """
    from app.models.detection_model import detect_objects
    from app.models.depth_model import estimate_depth

    img_arr = np.array(Image.open(image_path).convert("RGB"))

    if detection_result is None:
        detection_result = detect_objects(image_path)
    if depth_result is None:
        depth_result = estimate_depth(image_path)

    depth_map, spaciousness = depth_result
    room_type, room_conf    = _classify_with_clip(image_path, ROOM_LABELS)
    style, _                = _classify_with_clip(image_path, STYLE_LABELS)
    lighting                = _lighting_score(img_arr)
    clutter                 = _clutter_score(detection_result)

    return {
        "room_type":              room_type,
        "room_type_confidence":   room_conf,
        "style":                  style,
        "spaciousness_score":     round(spaciousness, 1),
        "clutter_score":          clutter,
        "lighting_quality":       lighting,
        "furniture_count":        detection_result.get("furniture_count", 0),
        "object_count":           detection_result.get("raw_count", 0),
    }
