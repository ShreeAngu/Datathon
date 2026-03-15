"""
Main analysis pipeline — runs all models on a single image.
Models are loaded once and reused across calls.
"""

import time
import logging
import numpy as np
from pathlib import Path

logger = logging.getLogger("pipeline")


class PropertyImageAnalyzer:
    """Singleton-style analyzer. Call analyze() per image."""

    def __init__(self):
        self._clip_ready  = False
        self._depth_ready = False
        self._yolo_ready  = False

    def _ensure_models(self):
        """Lazy-load all models on first call."""
        if not self._clip_ready:
            from app.models.clip_model import _load as load_clip
            load_clip()
            self._clip_ready = True
            logger.info("CLIP loaded")

        if not self._yolo_ready:
            from app.models.detection_model import _load as load_yolo
            load_yolo()
            self._yolo_ready = True
            logger.info("YOLO loaded")

        if not self._depth_ready:
            from app.models.depth_model import _load as load_depth
            load_depth()
            self._depth_ready = True
            logger.info("Depth model loaded")

    def analyze(self, image_path: str, dataset_label: str = None) -> dict:
        """
        Full pipeline for one image.
        Returns combined analysis dict with all sub-results + embedding.
        """
        t0 = time.time()
        self._ensure_models()

        path = str(image_path)

        # --- Run models (share detection + depth across services) ---
        from app.models.detection_model import detect_objects
        from app.models.depth_model     import estimate_depth
        from app.models.clip_model      import get_image_embedding

        detection  = detect_objects(path)
        depth_map, spaciousness = estimate_depth(path)
        embedding  = get_image_embedding(path)

        # --- Services ---
        from app.services.spatial_service       import analyze_spatial
        from app.services.authenticity_service  import verify_authenticity
        from app.services.accessibility_service import detect_accessibility
        from app.services.quality_service       import calculate_quality_score

        spatial       = analyze_spatial(path, detection_result=detection,
                                        depth_result=(depth_map, spaciousness))
        authenticity  = verify_authenticity(path, dataset_label=dataset_label)
        accessibility = detect_accessibility(path, detection_result=detection)
        quality       = calculate_quality_score(path, spatial, authenticity, accessibility)

        elapsed = round(time.time() - t0, 2)

        return {
            "image_path":    path,
            "spatial":       spatial,
            "authenticity":  authenticity,
            "accessibility": accessibility,
            "quality":       quality,
            "embedding":     embedding.tolist(),
            "processing_time_s": elapsed,
        }


# Module-level singleton
_analyzer = None


def get_analyzer() -> PropertyImageAnalyzer:
    global _analyzer
    if _analyzer is None:
        _analyzer = PropertyImageAnalyzer()
    return _analyzer
