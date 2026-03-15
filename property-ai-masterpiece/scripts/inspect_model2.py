#!/usr/bin/env python3
"""Deep inspect fake_detector_final.pt to identify exact MobileNetV3 variant."""
import torch
from pathlib import Path

model_dir = Path(__file__).parent.parent / "backend" / "app" / "models"
sd = torch.load(str(model_dir / "fake_detector_final.pt"), map_location="cpu", weights_only=True)

# Key diagnostic: first conv weight shape tells us the variant
first_conv = sd["backbone.features.0.0.weight"]
print(f"First conv shape: {tuple(first_conv.shape)}")
# MobileNetV3-Small: (16, 3, 3, 3)
# MobileNetV3-Large: (16, 3, 3, 3)  -- wait, both start at 16
# The saved model has (32, 3, 3, 3) -- that's EfficientNet-B0!

# Check classifier shape
for k in sd:
    if "classifier" in k:
        print(f"  {k}: {tuple(sd[k].shape)}")

# Check features keys to identify model
feat_keys = [k for k in sd if "features" in k]
print(f"\nTotal feature keys: {len(feat_keys)}")
print("Unique feature layer prefixes:")
prefixes = set()
for k in feat_keys:
    parts = k.split(".")
    if len(parts) >= 3:
        prefixes.add(".".join(parts[:3]))
for p in sorted(prefixes)[:10]:
    print(f"  {p}")

# Try to match against known architectures
print("\n--- Architecture detection ---")
print(f"features.0.0.weight shape: {tuple(sd['backbone.features.0.0.weight'].shape)}")
# EfficientNet-B0 first conv: (32, 3, 3, 3)
# MobileNetV3-Small first conv: (16, 3, 3, 3)
# MobileNetV3-Large first conv: (16, 3, 3, 3)
if sd["backbone.features.0.0.weight"].shape[0] == 32:
    print("→ Likely EfficientNet-B0 (32 output channels in first conv)")
elif sd["backbone.features.0.0.weight"].shape[0] == 16:
    print("→ Likely MobileNetV3-Small or Large (16 output channels)")
