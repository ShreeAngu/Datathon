import sys
sys.path.insert(0, 'backend')

try:
    from app.services.vector_indexer import search, get_index_stats
    stats = get_index_stats()
    print("Pinecone stats:", stats)

    # Try a dummy search
    dummy = [0.0] * 512
    results = search(dummy, top_k=3)
    print("Search results count:", len(results))
except Exception as e:
    import traceback
    print("PINECONE ERROR:")
    traceback.print_exc()
