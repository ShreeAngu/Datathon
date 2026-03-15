"""Visualization utilities — depth maps, clutter heatmaps, bounding boxes."""

import cv2
import numpy as np
from pathlib import Path
from PIL import Image

VIZ_ROOT = Path(__file__).parent.parent.parent.parent / "dataset" / "visualizations"
DEPTH_DIR   = VIZ_ROOT / "depth_maps"
HEATMAP_DIR = VIZ_ROOT / "clutter_heatmaps"
BBOX_DIR    = VIZ_ROOT / "bounding_boxes"

for d in (DEPTH_DIR, HEATMAP_DIR, BBOX_DIR):
    d.mkdir(parents=True, exist_ok=True)


def save_depth_map(image_stem: str, depth_array: np.ndarray) -> str:
    """Save colourised depth map. Returns output path."""
    arr = np.squeeze(depth_array)          # ensure 2D
    if arr.ndim != 2:
        arr = arr.mean(axis=-1)            # fallback: collapse channels
    # Normalise to 0-255 uint8 (CV_8UC1 required by applyColorMap)
    arr_min, arr_max = arr.min(), arr.max()
    if arr_max > arr_min:
        norm = ((arr - arr_min) / (arr_max - arr_min) * 255).astype(np.uint8)
    else:
        norm = np.zeros_like(arr, dtype=np.uint8)
    coloured = cv2.applyColorMap(norm, cv2.COLORMAP_INFERNO)
    out = DEPTH_DIR / f"{image_stem}_depth.png"
    cv2.imwrite(str(out), coloured)
    return str(out)


def save_clutter_heatmap(image_stem: str, image_path: str,
                         detection_result: dict) -> str:
    """Overlay detection bounding boxes as a heatmap on the image."""
    img = cv2.imread(image_path)
    if img is None:
        return ""
    h, w = img.shape[:2]
    heat = np.zeros((h, w), dtype=np.float32)

    for det in detection_result.get("detections", []):
        x1, y1, x2, y2 = [int(v) for v in det["bbox"]]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        heat[y1:y2, x1:x2] += det["confidence"]

    if heat.max() > 0:
        heat = (heat / heat.max() * 255).astype(np.uint8)
    heat_colour = cv2.applyColorMap(heat, cv2.COLORMAP_JET)
    blended = cv2.addWeighted(img, 0.6, heat_colour, 0.4, 0)

    out = HEATMAP_DIR / f"{image_stem}_heatmap.jpg"
    cv2.imwrite(str(out), blended)
    return str(out)


def save_bbox_visualization(image_stem: str, image_path: str,
                             detection_result: dict) -> str:
    """Draw bounding boxes with class labels on the image."""
    img = cv2.imread(image_path)
    if img is None:
        return ""

    colours = {"furniture": (0, 255, 0), "clutter": (0, 0, 255),
               "default": (255, 165, 0)}

    for det in detection_result.get("detections", []):
        x1, y1, x2, y2 = [int(v) for v in det["bbox"]]
        label = det["class_name"]
        conf  = det["confidence"]
        colour = colours.get("default")
        cv2.rectangle(img, (x1, y1), (x2, y2), colour, 2)
        cv2.putText(img, f"{label} {conf:.2f}", (x1, max(y1-5, 10)),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, colour, 1)

    out = BBOX_DIR / f"{image_stem}_boxes.jpg"
    cv2.imwrite(str(out), img)
    return str(out)
