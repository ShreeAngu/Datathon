"""
Deep Learning fake image detector.
Primary:  dima806/deepfake_vs_real_image_detection  (ViT, CIFAKE-trained)
Fallback: capcheck/ai-image-detection → prithivMLmods/Deep-Fake-Detector-v2-Model
Note: threshold lowered to 0.15 per dima806 author recommendation for modern AI images.
"""

import torch
from PIL import Image

# Lower threshold catches modern AI generators (SD, MJ, DALL-E) better
# dima806 author explicitly recommends 0.1-0.15 for post-2022 generators
FAKE_THRESHOLD = 0.15


class FakeImageDetector:
    def __init__(self):
        self.device    = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model     = None
        self.processor = None
        self.model_name = None
        self._load()

    def _load(self):
        candidates = [
            "dima806/deepfake_vs_real_image_detection",
            "capcheck/ai-image-detection",
            "prithivMLmods/Deep-Fake-Detector-v2-Model",
        ]
        for name in candidates:
            try:
                print(f"🤖 Loading {name} on {self.device}...")
                from transformers import AutoImageProcessor, AutoModelForImageClassification
                self.processor  = AutoImageProcessor.from_pretrained(name)
                self.model      = AutoModelForImageClassification.from_pretrained(name)
                self.model.to(self.device).eval()
                self.model_name = name
                print(f"✅ Loaded: {name}  labels={self.model.config.id2label}")
                return
            except Exception as e:
                print(f"⚠️  {name} failed: {e}")
        print("❌ All DL models failed — using heuristic fallback")

    def _resolve_fake_idx(self) -> int:
        """Find which output index corresponds to 'fake/AI'."""
        id2label = self.model.config.id2label
        for i, label in id2label.items():
            if any(k in label.lower() for k in ("fake", "ai", "generated", "deepfake")):
                return int(i)
        return 1  # default assumption

    def detect(self, image_path: str) -> dict:
        if self.model is None:
            return self._fallback(image_path)
        try:
            image  = Image.open(image_path).convert("RGB")
            inputs = self.processor(images=image, return_tensors="pt")
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            with torch.no_grad():
                logits = self.model(**inputs).logits
                probs  = torch.softmax(logits, dim=-1)[0]

            fake_idx  = self._resolve_fake_idx()
            real_idx  = 1 - fake_idx
            ai_prob   = float(probs[fake_idx])
            real_prob = float(probs[real_idx])

            # Use lowered threshold per author recommendation for modern AI images
            is_fake = ai_prob > FAKE_THRESHOLD

            return {
                "is_ai_generated":  is_fake,
                "confidence":       round(max(ai_prob, real_prob), 3),
                "ai_probability":   round(ai_prob * 100, 2),
                "real_probability": round(real_prob * 100, 2),
                "model_used":       self.model_name,
            }
        except Exception as e:
            print(f"⚠️  Inference error ({image_path}): {e}")
            return self._fallback(image_path)

    def _fallback(self, image_path: str) -> dict:
        """Heuristic fallback when DL model unavailable."""
        try:
            import numpy as np
            from scipy.ndimage import convolve
            arr  = np.array(Image.open(image_path).convert("RGB"), dtype=np.float32)
            gray = arr.mean(axis=2)
            k    = np.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]], dtype=np.float32)
            noise_var = float(np.var(convolve(gray, k)))
            ai_prob = max(0.0, min(1.0, 1.0 - noise_var / 600))
        except Exception:
            ai_prob = 0.5
        return {
            "is_ai_generated":  ai_prob > FAKE_THRESHOLD,
            "confidence":       round(max(ai_prob, 1 - ai_prob), 3),
            "ai_probability":   round(ai_prob * 100, 2),
            "real_probability": round((1 - ai_prob) * 100, 2),
            "model_used":       "heuristic_fallback",
        }


_detector = None

def get_fake_detector() -> FakeImageDetector:
    global _detector
    if _detector is None:
        _detector = FakeImageDetector()
    return _detector
