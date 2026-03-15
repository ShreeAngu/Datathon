#!/usr/bin/env python3
"""Inspect saved model state dict keys to determine exact architecture."""
import sys, torch
from pathlib import Path

model_dir = Path(__file__).parent.parent / "backend" / "app" / "models"

for fname in ("fake_detector_best.pt", "fake_detector_final.pt"):
    pt = model_dir / fname
    if not pt.exists():
        print(f"NOT FOUND: {fname}")
        continue
    sd = torch.load(str(pt), map_location="cpu", weights_only=True)
    keys = list(sd.keys())
    print(f"\n=== {fname} ===")
    print(f"Total keys: {len(keys)}")
    print("First 15 keys:")
    for k in keys[:15]:
        print(f"  {k}  {tuple(sd[k].shape)}")
    print("Last 5 keys:")
    for k in keys[-5:]:
        print(f"  {k}  {tuple(sd[k].shape)}")
