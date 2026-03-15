import sys
sys.path.insert(0, 'backend')

from app.services.reverse_search import reverse_search

result = reverse_search(
    "dataset/uploads/76a58247d43b4a58b4015ed8ea144ccb.jpeg",
    top_k=5,
    min_similarity=0.2,
)
print("Source:", result["source"])
print("Total found:", result["total_found"])
print("Search time:", result["search_time_ms"], "ms")
for m in result["matches"]:
    print(f"  sim={m['similarity']:.3f}  {m.get('title','?')}  {m['image_url']}")
