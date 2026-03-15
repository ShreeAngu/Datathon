import sys
sys.path.insert(0, 'backend')

from app.models.clip_model import get_image_embedding
import numpy as np

# Test 3 different images
imgs = [
    "dataset/uploads/76a58247d43b4a58b4015ed8ea144ccb.jpeg",
    "dataset/uploads/c3150bc052c4423dbfedf1538f6fc6fe.jpeg",
    "dataset/uploads/29d51a23ce694656929c7e8357361b46.jpeg",
]

embeddings = []
for img in imgs:
    emb = get_image_embedding(img)
    embeddings.append(emb)
    print(f"{img.split('/')[-1][:20]}: shape={emb.shape}, mean={emb.mean():.4f}, std={emb.std():.4f}")

# Check if they're identical
print("\nPairwise cosine similarity:")
for i in range(len(embeddings)):
    for j in range(i+1, len(embeddings)):
        a, b = embeddings[i], embeddings[j]
        sim = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
        print(f"  {i} vs {j}: {sim:.4f}")
