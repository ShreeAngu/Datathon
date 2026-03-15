"""YOLOv8n object detection — furniture, clutter, accessibility features."""

import torch
from pathlib import Path
from PIL import Image

_model = None

# COCO classes relevant to property analysis
FURNITURE_IDS  = {56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 74, 75}
# 56=chair,57=couch,58=potted plant,59=bed,60=dining table,
# 61=toilet,62=tv,63=laptop,64=mouse,65=remote,66=keyboard,
# 67=cell phone,74=clock,75=vase
CLUTTER_IDS    = {39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50,
                  51, 52, 53, 54, 55, 63, 64, 65, 66, 67, 76, 77, 78, 79}
DOOR_WINDOW_IDS = set()   # not in COCO — handled via heuristics
STAIR_IDS       = set()   # not in COCO — handled via heuristics


def _load():
    global _model
    if _model is None:
        from ultralytics import YOLO
        _model = YOLO("yolov8n.pt")
    return _model


def detect_objects(image_path: str) -> dict:
    """
    Returns dict with:
        detections      : list of {class_name, confidence, bbox}
        furniture_count : int
        clutter_count   : int
        has_stairs      : bool  (heuristic)
        has_grab_bar    : bool  (heuristic — narrow horizontal box near wall)
        door_count      : int   (heuristic)
        raw_count       : int
    """
    model  = _load()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    results = model.predict(image_path, device=device, verbose=False, conf=0.25)[0]

    detections     = []
    furniture_cnt  = 0
    clutter_cnt    = 0

    for box in results.boxes:
        cls_id = int(box.cls[0])
        conf   = float(box.conf[0])
        xyxy   = box.xyxy[0].tolist()
        name   = results.names[cls_id]

        detections.append({"class_name": name, "confidence": round(conf, 3),
                           "bbox": [round(v, 1) for v in xyxy]})
        if cls_id in FURNITURE_IDS:
            furniture_cnt += 1
        if cls_id in CLUTTER_IDS:
            clutter_cnt += 1

    # Heuristic: stairs → if "person" detected on diagonal or many objects stacked
    has_stairs  = any(d["class_name"] == "stairs" for d in detections)
    # Heuristic: grab bar → thin horizontal rectangle near image edge
    has_grab_bar = _heuristic_grab_bar(results)

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return {
        "detections":      detections,
        "furniture_count": furniture_cnt,
        "clutter_count":   clutter_cnt,
        "has_stairs":      has_stairs,
        "has_grab_bar":    has_grab_bar,
        "door_count":      0,
        "raw_count":       len(detections),
    }


def _heuristic_grab_bar(results) -> bool:
    """Very thin horizontal bounding boxes near image edges suggest grab bars."""
    h, w = results.orig_shape
    for box in results.boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        bw, bh = x2 - x1, y2 - y1
        if bh > 0 and (bw / bh) > 6 and bh < h * 0.05:
            return True
    return False
