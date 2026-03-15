"""Depth Anything V2 — monocular depth estimation + spaciousness score."""

import numpy as np
import torch
from PIL import Image

_pipe = None


def _load():
    global _pipe
    if _pipe is None:
        from transformers import pipeline as hf_pipeline
        device = 0 if torch.cuda.is_available() else -1
        _pipe = hf_pipeline(
            "depth-estimation",
            model="LiheYoung/depth-anything-large-hf",
            device=device,
        )
    return _pipe


def estimate_depth(image_path: str) -> tuple[np.ndarray, float]:
    """
    Returns:
        depth_map  : H×W float32 array (normalised 0-1, higher = farther)
        spaciousness_score : 0-100 (higher = more open/spacious room)
    """
    pipe = _load()
    img  = Image.open(image_path).convert("RGB")
    out  = pipe(img)
    depth = np.array(out["depth"], dtype=np.float32)

    # Normalise to 0-1
    d_min, d_max = depth.min(), depth.max()
    if d_max > d_min:
        depth = (depth - d_min) / (d_max - d_min)

    # Spaciousness: high variance + high mean depth → open space
    mean_d  = float(depth.mean())
    var_d   = float(depth.var())
    score   = min(100.0, round((mean_d * 60 + var_d * 400), 1))

    if torch.cuda.is_available():
        torch.cuda.empty_cache()

    return depth, score
