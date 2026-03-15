"""MobileNetV3-Small binary classifier for real vs fake image detection."""

import torch
import torch.nn as nn
from torchvision import models


class FakeImageClassifier(nn.Module):
    """
    MobileNetV3-Small backbone + custom binary head.
    Fits comfortably in 6GB VRAM at batch_size=16.
    """

    def __init__(self, num_classes: int = 2, pretrained: bool = True):
        super().__init__()
        weights = models.MobileNet_V3_Small_Weights.IMAGENET1K_V1 if pretrained else None
        self.backbone = models.mobilenet_v3_small(weights=weights)

        # MobileNetV3-Small: avgpool output is 576-dim, classifier[0] maps 576→1024
        in_features = self.backbone.classifier[0].in_features  # 576
        self.backbone.classifier = nn.Sequential(
            nn.Linear(in_features, 256),
            nn.Hardswish(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(256, 64),
            nn.Hardswish(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(64, num_classes),
        )

    def forward(self, x):
        return self.backbone(x)

    def freeze_backbone(self, freeze: bool = True):
        for param in self.backbone.features.parameters():
            param.requires_grad = not freeze
