#!/usr/bin/env python3
"""
Probe FatimahEmadEldin/genai-manipulation-detection-interior
Run: python scripts/probe_fatimah_dataset.py
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

import pandas as pd
from PIL import Image

DATASET = "FatimahEmadEldin/genai-manipulation-detection-interior"

print(f"Loading annotations from: {DATASET}")
df = pd.read_csv(f"hf://datasets/{DATASET}/annotations.csv")

print(f"\nTotal images : {len(df)}")
print(f"Real images  : {len(df[df['label'] == 'real'])}")
print(f"Fake images  : {len(df[df['label'] == 'fake'])}")
print(f"\nAll columns  : {list(df.columns)}")
print(f"\nSample rows:")
print(df.head(5).to_string())

fakes = df[df['label'] == 'fake']
print(f"\nManipulation categories:")
print(fakes['manipulation_category'].value_counts())
