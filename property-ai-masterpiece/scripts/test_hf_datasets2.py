#!/usr/bin/env python3
"""
Test second batch of HuggingFace datasets — parquet-based only (no scripts).
Run: python scripts/test_hf_datasets2.py
"""

import os, sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

env_path = project_root / "backend" / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

token = os.environ.get("HF_TOKEN", "")
print(f"HF token: {'set ✅' if token else 'MISSING ❌'}")
print("datasets version:", end=" ")
import datasets; print(datasets.__version__)
print("=" * 60)

from datasets import load_dataset

# Parquet-native datasets (no loading scripts)
CANDIDATES = [
    ("CIFAKE",                          "RichardBronosky/CIFAKE",              None,  "test"),
    ("awsaf49/artifact",                "awsaf49/artifact",                    None,  "train"),
    ("jlbaker361/fake_vs_real_custom",  "jlbaker361/fake_vs_real_custom",      None,  "train"),
    ("Organika/sdxl-detector",          "Organika/sdxl-detector",              None,  "train"),
    ("haywoodsloan/ai-images-20240629", "haywoodsloan/ai-images-20240629",     None,  "train"),
    ("tonyassi/ai-generated-images",    "tonyassi/ai-generated-images",        None,  "train"),
    ("Heem2/AI-vs-Human-Generated-Dataset", "Heem2/AI-vs-Human-Generated-Dataset", None, "train"),
    ("birdy-comp/ai-vs-real-images",    "birdy-comp/ai-vs-real-images",        None,  "train"),
]

for label, name, cfg, split in CANDIDATES:
    try:
        kwargs = dict(split=split, streaming=True, token=token or None)
        if cfg and cfg != name:
            kwargs["name"] = cfg
        ds = load_dataset(name, **kwargs)
        item = next(iter(ds))
        keys = list(item.keys())
        img_key = next((k for k in keys if "image" in k.lower()), None)
        lbl_key = next((k for k in keys if "label" in k.lower()), None)
        img_val = item.get(img_key) if img_key else None
        lbl_val = item.get(lbl_key) if lbl_key else None
        print(f"✅ {name}")
        print(f"   keys={keys}  label={lbl_val}  img_type={type(img_val).__name__ if img_val else 'none'}")
    except Exception as e:
        print(f"❌ {name}: {str(e)[:120]}")
    print()
