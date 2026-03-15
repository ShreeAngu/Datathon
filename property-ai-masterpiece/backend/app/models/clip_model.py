"""CLIP ViT-B/32 embedding model — 512-dim vectors for images and text."""

import numpy as np
import torch
from PIL import Image
from pathlib import Path

_model = None


def _load():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer("clip-ViT-B-32")
        _model.eval()
    return _model


def get_image_embedding(image_path: str) -> np.ndarray:
    """Return 512-dim L2-normalised CLIP embedding for an image."""
    model = _load()
    img = Image.open(image_path).convert("RGB")
    
    # Use encode with batch to avoid caching issues
    emb = model.encode([img], convert_to_numpy=True, normalize_embeddings=True,
                       batch_size=1, show_progress_bar=False)[0]
    return emb.astype(np.float32)


def get_text_embedding(text_query: str) -> np.ndarray:
    """Return 512-dim L2-normalised CLIP embedding for a text query."""
    model = _load()
    emb = model.encode([text_query], convert_to_numpy=True, normalize_embeddings=True,
                       batch_size=1, show_progress_bar=False)[0]
    return emb.astype(np.float32)
