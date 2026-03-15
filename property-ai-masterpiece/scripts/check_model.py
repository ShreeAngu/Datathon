import sys
sys.path.insert(0, "backend")

from app.models.fake_detector_inference import get_local_fake_detector
import json
from pathlib import Path

d = get_local_fake_detector()
print(f"Architecture : {d.arch}")
print(f"Device       : {d.device}")
print(f"Metadata     : {json.dumps(d.metadata, indent=2)}")

# Also show raw .pt file sizes
for fname in ("fake_detector_best.pt", "fake_detector_final.pt"):
    p = Path("backend/app/models") / fname
    if p.exists():
        print(f"{fname}: {p.stat().st_size / 1e6:.1f} MB")
    else:
        print(f"{fname}: NOT FOUND")
