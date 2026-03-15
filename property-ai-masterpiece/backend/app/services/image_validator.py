"""
Image Validator Service — seller upload validation.
Checks: room type, lighting (LAB), clutter heatmap (YOLO/cv2),
        AI detection, duplicates, composition (tilt + blur + aspect).
"""
import uuid, time, os
import numpy as np
import cv2
from pathlib import Path
from PIL import Image, ImageDraw

HEATMAP_DIR = Path("backend/app/uploads/heatmaps")
HEATMAP_DIR.mkdir(parents=True, exist_ok=True)

STAGED_DIR = Path("dataset/staged")
STAGED_DIR.mkdir(parents=True, exist_ok=True)

# Objects that count as clutter in property photos
_CLUTTER_CLASSES = {
    "bottle", "cup", "book", "chair", "couch", "potted plant", "bed",
    "dining table", "tv", "laptop", "cell phone", "remote", "keyboard",
    "mouse", "scissors", "toothbrush", "backpack", "handbag", "suitcase",
}


class ImageValidator:
    """Full validation pipeline for seller-uploaded images."""

    def __init__(self):
        self.device = "cuda" if self._cuda_available() else "cpu"
        print(f"🤖 ImageValidator on {self.device}")

    @staticmethod
    def _cuda_available():
        try:
            import torch
            return torch.cuda.is_available()
        except Exception:
            return False

    # ── Public API ────────────────────────────────────────────────────────────

    def validate_upload(self, image_path: str,
                        expected_room: str = None,
                        listing_id: str = None) -> dict:
        """Complete validation pipeline. Returns detailed feedback dict."""
        t0 = time.time()
        img_cv = cv2.imread(image_path)
        if img_cv is None:
            raise ValueError(f"Cannot read image: {image_path}")
        arr = cv2.cvtColor(img_cv, cv2.COLOR_BGR2RGB)

        room   = self._analyze_room_type(image_path, expected_room)
        light  = self._analyze_lighting(img_cv)
        clut   = self._analyze_clutter(img_cv, image_path)
        auth   = self._check_authenticity(image_path)
        dup    = self._check_duplicate(image_path, listing_id)
        comp   = self._analyze_composition(img_cv)

        overall = round(
            room["confidence"] * 100 * (1.0 if room["matches_expected"] else 0.5) * 0.15 +
            light["score"] * 0.25 +
            clut["score"] * 0.25 +
            (100 - auth["ai_probability"]) * 0.20 +
            comp["score"] * 0.15,
            1
        )

        recs = self._generate_recommendations(room, light, clut, auth, dup, comp)

        return {
            "image_id":             str(uuid.uuid4()).replace("-", ""),
            "verified_room_type":   room["room_type"],
            "room_confidence":      room["confidence"],
            "matches_expected":     room["matches_expected"],
            "lighting_score":       light["score"],
            "lighting_feedback":    light["feedback"],
            "lighting_metrics":     light["metrics"],
            "clutter_score":        clut["score"],
            "clutter_locations":    clut["locations"],
            "clutter_object_count": clut["object_count"],
            "clutter_heatmap_path": clut["heatmap_path"],
            "is_ai_generated":      auth["is_fake"],
            "ai_probability":       auth["ai_probability"],
            "real_probability":     auth["real_probability"],
            "is_duplicate":         dup["is_duplicate"],
            "duplicate_listing_id": dup["listing_id"],
            "composition_score":    comp["score"],
            "composition_issues":   comp["issues"],
            "composition_metrics":  comp["metrics"],
            "overall_quality":      overall,
            "recommendations":      recs,
            "auto_enhance_available": light["score"] < 75 or clut["score"] < 60,
            "processing_time_ms":   round((time.time() - t0) * 1000, 1),
        }

    def auto_enhance(self, image_path: str) -> dict:
        """CLAHE lighting + saturation boost. Saves *_enhanced.jpg alongside original."""
        img = cv2.imread(image_path)
        if img is None:
            return {"success": False, "error": "Cannot read image"}

        # CLAHE on L channel
        lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        lab = cv2.merge([clahe.apply(l), a, b])
        enhanced = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

        # Mild saturation boost
        hsv = cv2.cvtColor(enhanced, cv2.COLOR_BGR2HSV).astype(np.float32)
        hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.1, 0, 255)
        enhanced = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)

        p = Path(image_path)
        out = str(p.parent / f"{p.stem}_enhanced{p.suffix}")
        cv2.imwrite(out, enhanced)
        return {"success": True, "enhanced_path": out, "original_path": image_path}

    # ── Room type ─────────────────────────────────────────────────────────────

    def _analyze_room_type(self, image_path: str, expected: str = None) -> dict:
        try:
            from app.services.spatial_service import analyze_spatial
            r = analyze_spatial(image_path)
            room_type = r.get("room_type", "unknown")
            conf = float(r.get("room_type_confidence", 0.5))
        except Exception:
            room_type, conf = "unknown", 0.5

        matches = True
        if expected:
            matches = room_type.lower().replace("_", " ") == expected.lower().replace("_", " ")

        return {"room_type": room_type, "confidence": round(conf, 3),
                "matches_expected": matches, "expected": expected}

    # ── Lighting ──────────────────────────────────────────────────────────────

    def _analyze_lighting(self, img_cv: np.ndarray) -> dict:
        lab = cv2.cvtColor(img_cv, cv2.COLOR_BGR2LAB)
        l = lab[:, :, 0].astype(np.float32)
        mean_b = float(np.mean(l))
        std_b  = float(np.std(l))
        drange = float(np.max(l) - np.min(l))

        # Score components
        if 120 <= mean_b <= 180:   bright_s = 40
        elif 90 <= mean_b < 120 or 180 < mean_b <= 210: bright_s = 25
        else:                       bright_s = 10

        if 50 <= std_b <= 100:     contrast_s = 30
        elif 30 <= std_b < 50 or 100 < std_b <= 120: contrast_s = 20
        else:                       contrast_s = 10

        range_s = 30 if drange > 150 else (20 if drange > 100 else 10)
        score = bright_s + contrast_s + range_s

        if score < 50:
            feedback = "Too dark — open curtains, add lamps, or increase camera exposure"
        elif score < 70:
            feedback = "Adequate but could be brighter — consider opening curtains or adding lamps"
        elif score < 85:
            feedback = "Good lighting — minor improvements possible"
        else:
            feedback = "Excellent natural lighting — professional quality"

        return {
            "score": float(score),
            "feedback": feedback,
            "metrics": {
                "mean_brightness": round(mean_b, 1),
                "contrast":        round(std_b, 1),
                "dynamic_range":   round(drange, 1),
            },
        }

    # ── Clutter ───────────────────────────────────────────────────────────────

    def _analyze_clutter(self, img_cv: np.ndarray, image_path: str) -> dict:
        try:
            from app.models.detection_model import detect_objects
            det = detect_objects(image_path)
            objects = det.get("objects", [])
            clutter = [o for o in objects if o.get("label", "").lower() in _CLUTTER_CLASSES]
            count = len(clutter)
            score = float(max(0, 100 - count * 10))
            locations = list({self._zone(o.get("bbox", []), img_cv.shape) for o in clutter})
            heatmap = self._make_heatmap_cv2(img_cv, clutter, image_path)
            return {"score": score, "locations": locations,
                    "object_count": count, "heatmap_path": heatmap}
        except Exception:
            return {"score": 60.0, "locations": [], "object_count": 0, "heatmap_path": None}

    def _zone(self, bbox: list, shape) -> str:
        if len(bbox) < 4:
            return "unknown"
        h, w = shape[:2]
        cx = (bbox[0] + bbox[2]) / 2
        cy = (bbox[1] + bbox[3]) / 2
        if cy > h * 0.7:   return "floor area"
        if cy < h * 0.3:   return "upper area"
        if cx < w * 0.33:  return "left side"
        if cx > w * 0.67:  return "right side"
        return "center"

    def _make_heatmap_cv2(self, img_cv: np.ndarray, objects: list,
                           image_path: str) -> str:
        try:
            heat = np.zeros(img_cv.shape[:2], dtype=np.float32)
            for o in objects:
                box = o.get("bbox", [])
                if len(box) == 4:
                    x1, y1, x2, y2 = [int(v) for v in box]
                    heat[y1:y2, x1:x2] += 0.7
            heat = np.clip(heat, 0, 1)
            colored = cv2.applyColorMap((heat * 255).astype(np.uint8), cv2.COLORMAP_JET)
            blended = cv2.addWeighted(img_cv, 0.6, colored, 0.4, 0)
            stem = Path(image_path).stem
            out = HEATMAP_DIR / f"{stem}_heatmap.jpg"
            cv2.imwrite(str(out), blended)
            return f"/uploads/heatmaps/{stem}_heatmap.jpg"
        except Exception:
            return None

    # ── Authenticity ──────────────────────────────────────────────────────────

    def _check_authenticity(self, image_path: str) -> dict:
        try:
            from app.services.authenticity_service import verify_authenticity
            r = verify_authenticity(image_path)
            return {
                "is_fake":       r.get("is_ai_generated", False),
                "ai_probability": float(r.get("ai_probability", 0.0)),
                "real_probability": float(r.get("real_probability", 100.0)),
                "confidence":    float(r.get("detection_confidence", 0.5)),
            }
        except Exception as e:
            print(f"⚠️  Authenticity check failed: {e}")
            return {"is_fake": False, "ai_probability": 0.0,
                    "real_probability": 100.0, "confidence": 0.5}

    # ── Duplicate ─────────────────────────────────────────────────────────────

    def _check_duplicate(self, image_path: str, listing_id: str = None) -> dict:
        try:
            from app.models.clip_model import get_image_embedding
            from app.services.vector_indexer import search as vec_search
            emb = get_image_embedding(image_path).tolist()
            for m in vec_search(emb, top_k=3):
                score = float(m.get("score", 0) if isinstance(m, dict) else m.score)
                mid   = m.get("id") if isinstance(m, dict) else m.id
                if score > 0.97 and mid != listing_id:
                    return {"is_duplicate": True, "listing_id": mid, "similarity": score}
        except Exception:
            pass
        return {"is_duplicate": False, "listing_id": None}

    # ── Composition ───────────────────────────────────────────────────────────

    def _analyze_composition(self, img_cv: np.ndarray) -> dict:
        issues = []
        score  = 100.0
        h, w   = img_cv.shape[:2]

        # Tilt via HoughLines
        tilt_angle = 0.0
        try:
            gray  = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)
            edges = cv2.Canny(gray, 50, 150)
            lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                                    minLineLength=100, maxLineGap=10)
            if lines is not None:
                angles = [abs(np.degrees(np.arctan2(l[0][3] - l[0][1],
                                                     l[0][2] - l[0][0])))
                          for l in lines]
                tilt_angle = float(np.mean(angles))
                if tilt_angle > 5:
                    issues.append(f"Photo is tilted ({tilt_angle:.1f}°) — straighten before uploading")
                    score -= 15
        except Exception:
            pass

        # Aspect ratio
        ratio = w / h
        if ratio < 0.8:
            issues.append("Portrait orientation — landscape (4:3 or 16:9) preferred")
            score -= 10
        elif ratio > 2.5:
            issues.append("Image too wide — standard 4:3 or 16:9 recommended")
            score -= 5

        # Blur via Laplacian variance
        sharpness = 0.0
        try:
            gray_f = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY).astype(np.float32)
            lap    = cv2.Laplacian(gray_f, cv2.CV_32F)
            sharpness = float(np.var(lap))
            if sharpness < 100:
                issues.append("Image appears blurry — use a tripod or increase shutter speed")
                score -= 20
        except Exception:
            pass

        return {
            "score":   round(max(0.0, score), 1),
            "issues":  issues,
            "metrics": {
                "tilt_angle":   round(tilt_angle, 1),
                "aspect_ratio": round(ratio, 2),
                "sharpness":    round(sharpness, 1),
            },
        }

    # ── Recommendations ───────────────────────────────────────────────────────

    def _generate_recommendations(self, room, light, clut, auth, dup, comp) -> list:
        recs = []

        if auth["is_fake"]:
            recs.append({"priority": "high",
                         "action": "Replace with an authentic photo",
                         "impact": "AI-generated images reduce buyer trust by 60%",
                         "auto_fixable": False,
                         "tip": "Retake with a real camera"})
        if dup["is_duplicate"]:
            recs.append({"priority": "high",
                         "action": "Remove duplicate image",
                         "impact": "Duplicate images flag listings for review",
                         "auto_fixable": True,
                         "tip": "This image already exists in another listing"})
        if not room["matches_expected"] and room["expected"]:
            recs.append({"priority": "high",
                         "action": f"Photo detected as '{room['room_type']}', not '{room['expected']}'",
                         "impact": "Room mismatch reduces search relevance",
                         "auto_fixable": False,
                         "tip": "Retake photo or update the room category"})
        if light["score"] < 60:
            recs.append({"priority": "high",
                         "action": "Improve lighting",
                         "impact": "Well-lit photos get 40% more views",
                         "auto_fixable": True,
                         "tip": light["feedback"]})
        elif light["score"] < 80:
            recs.append({"priority": "medium",
                         "action": "Slightly brighten image",
                         "impact": "Better lighting increases engagement",
                         "auto_fixable": True,
                         "tip": "Open curtains or add a lamp"})
        if clut["score"] < 50:
            zones = ", ".join(clut["locations"][:2]) or "the room"
            recs.append({"priority": "high",
                         "action": f"Remove clutter from {zones}",
                         "impact": "Clean spaces sell 30% faster",
                         "auto_fixable": False,
                         "tip": "Clear countertops and floors before photographing"})
        elif clut["score"] < 70:
            recs.append({"priority": "medium",
                         "action": "Reduce visible clutter",
                         "impact": "Tidier photos increase buyer interest",
                         "auto_fixable": False,
                         "tip": "Remove personal items and excess decorations"})
        for issue in comp["issues"]:
            fixable = "tilted" in issue.lower() or "blurry" in issue.lower()
            recs.append({"priority": "medium",
                         "action": issue,
                         "impact": "Better composition improves first impressions",
                         "auto_fixable": fixable,
                         "tip": "Use photo editor to correct"})

        order = {"high": 0, "medium": 1, "low": 2}
        recs.sort(key=lambda x: order.get(x["priority"], 3))
        return recs[:5]


# ── Singleton ─────────────────────────────────────────────────────────────────

_validator = None


def get_image_validator() -> ImageValidator:
    global _validator
    if _validator is None:
        _validator = ImageValidator()
    return _validator
