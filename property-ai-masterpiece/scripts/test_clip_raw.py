import sys
sys.path.insert(0, 'backend')

from sentence_transformers import SentenceTransformer
from PIL import Image
import numpy as np

model = SentenceTransformer("clip-ViT-B-32")

img1 = Image.open("dataset/uploads/76a58247d43b4a58b4015ed8ea144ccb.jpeg").convert("RGB")
img2 = Image.open("dataset/uploads/c3150bc052c4423dbfedf1538f6fc6fe.jpeg").convert("RGB")

emb1 = model.encode(img1, convert_to_numpy=True, normalize_embeddings=True)
emb2 = model.encode(img2, convert_to_numpy=True, normalize_embeddings=True)

print(f"Emb1: shape={emb1.shape}, norm={np.linalg.norm(emb1):.4f}, mean={emb1.mean():.4f}")
print(f"Emb2: shape={emb2.shape}, norm={np.linalg.norm(emb2):.4f}, mean={emb2.mean():.4f}")
print(f"Cosine sim: {np.dot(emb1, emb2):.4f}")
print(f"First 10 values emb1: {emb1[:10]}")
print(f"First 10 values emb2: {emb2[:10]}")
