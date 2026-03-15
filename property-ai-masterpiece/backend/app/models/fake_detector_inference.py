"""
Inference wrapper for locally trained fake image detector.

Saved model inventory (both use 'backbone.' prefix wrapper):
  fake_detector_final.pt — EfficientNet-B0
      backbone.features.0.0.weight (32,3,3,3)
      backbone.classifier: Dropout → Linear(1280→256) → SiLU → Dropout → Linear(256→2)

  fake_detector_best.pt  — ResNet-50
      backbone.conv1.weight (64,3,7,7)
      backbone.fc: Dropout → Linear(2048→512) → ReLU → Dropout → Linear(512→2)

Architecture is auto-detected from state dict keys — no manual config needed.
"""

import json
import torch
import torch.nn as nn
from pathlib import Path
from PIL import Image
import torchvision.transforms as T
from torchvision import models

MODEL_DIR = Path(__file__).parent

_TRANSFORM = T.Compose([
    T.Resize((224, 224)),
    T.ToTensor(),
    T.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


# ---------------------------------------------------------------------------
# Model builders — must exactly match the training-time architecture
# ---------------------------------------------------------------------------

class _EfficientNetWrapper(nn.Module):
    """EfficientNet-B0 with backbone.classifier head (matches fake_detector_final.pt)."""
    def __init__(self):
        super().__init__()
        self.backbone = models.efficientnet_b0(weights=None)
        in_features = self.backbone.classifier[1].in_features  # 1280
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(0.4),
            nn.Linear(in_features, 256),
            nn.SiLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 2),
        )

    def forward(self, x):
        return self.backbone(x)


class _ResNet50Wrapper(nn.Module):
    """ResNet-50 with backbone.fc head (matches fake_detector_best.pt)."""
    def __init__(self):
        super().__init__()
        self.backbone = models.resnet50(weights=None)
        in_features = self.backbone.fc.in_features  # 2048
        self.backbone.fc = nn.Sequential(
            nn.Dropout(0.4),
            nn.Linear(in_features, 512),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(512, 2),
        )

    def forward(self, x):
        return self.backbone(x)


class _MobileNetV3Wrapper(nn.Module):
    """MobileNetV3-Small matching retrain_original_only.py classifier head."""
    def __init__(self):
        super().__init__()
        self.backbone = models.mobilenet_v3_small(weights=None)
        in_features = self.backbone.classifier[0].in_features  # 576
        self.backbone.classifier = nn.Sequential(
            nn.Linear(in_features, 256),
            nn.Hardswish(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(256, 64),
            nn.Hardswish(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(64, 2),
        )

    def forward(self, x):
        return self.backbone(x)


def _detect_arch(state_dict: dict) -> str:
    keys = list(state_dict.keys())
    if any("backbone.conv1" in k or "backbone.layer1" in k for k in keys):
        return "resnet50"
    if any("backbone.features" in k for k in keys):
        first_conv = state_dict.get("backbone.features.0.0.weight")
        if first_conv is not None and first_conv.shape[0] == 32:
            return "efficientnet_b0"
        return "mobilenet_v3_small"   # 16-channel first conv
    return "unknown"


def _build_model(arch: str) -> nn.Module:
    if arch == "efficientnet_b0":
        return _EfficientNetWrapper()
    if arch == "resnet50":
        return _ResNet50Wrapper()
    if arch == "mobilenet_v3_small":
        return _MobileNetV3Wrapper()
    raise ValueError(f"Unsupported architecture: {arch}")


# ---------------------------------------------------------------------------
# Detector
# ---------------------------------------------------------------------------

class LocalFakeDetector:
    def __init__(self):
        self.device    = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model     = None
        self.arch      = "unknown"
        self.metadata  = {}
        self.threshold = 0.40   # tuned for better fake recall
        self._load()

    def _load(self):
        # Prefer final (EfficientNet-B0) over best (ResNet-50)
        for fname in ("fake_detector_final.pt", "fake_detector_best.pt"):
            pt = MODEL_DIR / fname
            if not pt.exists():
                continue
            try:
                sd   = torch.load(str(pt), map_location=self.device, weights_only=True)
                arch = _detect_arch(sd)
                m    = _build_model(arch)
                m.load_state_dict(sd, strict=True)
                m.to(self.device).eval()
                self.model = m
                self.arch  = arch

                meta_path = MODEL_DIR / "fake_detector_metadata.json"
                if meta_path.exists():
                    self.metadata = json.loads(meta_path.read_text())

                acc = self.metadata.get("best_val_accuracy", "?")
                print(f"✅ LocalFakeDetector: {fname}  arch={arch}  val_acc={acc}%  device={self.device}")
                return

            except Exception as e:
                print(f"⚠️  Failed to load {fname}: {e}")

        raise FileNotFoundError(
            "No trained model found. Run: python scripts/train_fake_detector.py"
        )

    def detect(self, image_path: str) -> dict:
        if self.model is None:
            return self._fallback()
        try:
            img    = Image.open(image_path).convert("RGB")
            tensor = _TRANSFORM(img).unsqueeze(0).to(self.device)
            with torch.no_grad():
                probs = torch.softmax(self.model(tensor), dim=-1)[0]
            real_prob = float(probs[0])
            ai_prob   = float(probs[1])
            return {
                "is_ai_generated":    ai_prob > self.threshold,
                "confidence":         round(max(real_prob, ai_prob), 3),
                "ai_probability":     round(ai_prob * 100, 2),
                "real_probability":   round(real_prob * 100, 2),
                "model_type":         "local_fine_tuned",
                "model_architecture": self.arch,
                "training_accuracy":  self.metadata.get("best_val_accuracy"),
                "threshold_used":     self.threshold,
            }
        except Exception as e:
            print(f"⚠️  Inference error ({image_path}): {e}")
            return self._fallback(str(e))

    def _fallback(self, error: str = "") -> dict:
        return {
            "is_ai_generated":  False,
            "confidence":       0.5,
            "ai_probability":   50.0,
            "real_probability": 50.0,
            "model_type":       "fallback",
            "error":            error,
        }


_detector = None

def get_local_fake_detector() -> LocalFakeDetector:
    global _detector
    if _detector is None:
        _detector = LocalFakeDetector()
    return _detector
