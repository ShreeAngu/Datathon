#!/usr/bin/env python3
"""
Test which HuggingFace datasets are accessible and what their structure looks like.
Run: python scripts/test_hf_datasets.py
"""

import os, sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load .env
env_path = project_root / "backend" / ".env"
if env_path.exists():
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

token = os.environ.get("HF_TOKEN", "")
print(f"HF token: {'set ✅' if token else 'MISSING ❌'}")
print("=" * 60)

from datasets import load_dataset

# Candidates — no trust_remote_code, publicly accessible
CANDIDATES = [
    # (dataset_name, config, split)
    ("poloclub/diffusiondb",          "2m_first_1k",  "train"),
    ("phantom-lab/fake-images",        None,           "train"),
    ("elsaEU/ELSA_1M",                 None,           "train"),
    ("faridlab/deepfake_detection",    None,           "train"),
    ("OpenRL/fake_real_image_dataset", None,           "train"),
    ("Wvolf/TNL2K_Diffusion",          None,           "train"),
    ("recastai/CIFAKE-real-and-ai-generated-images", None, "train"),
]

for name, cfg, split in CANDIDATES:
    try:
        kwargs = dict(split=split, streaming=True, token=token or None)
        if cfg:
            kwargs["name"] = cfg
        ds = load_dataset(name, **kwargs)
        item = next(iter(ds))
        keys = list(item.keys())
        # Check for image key
        img_key = next((k for k in keys if "image" in k.lower()), None)
        lbl_key = next((k for k in keys if "label" in k.lower()), None)
        img_val = item.get(img_key) if img_key else None
        print(f"✅ {name}")
        print(f"   keys={keys}")
        print(f"   image_key={img_key}  label_key={lbl_key}")
        if lbl_key:
            print(f"   label sample={item.get(lbl_key)}")
        if img_val:
            print(f"   image type={type(img_val).__name__}  size={getattr(img_val, 'size', '?')}")
    except Exception as e:
        print(f"❌ {name}: {str(e)[:100]}")
    print()
