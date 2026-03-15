"""Pinecone vector indexer — upsert and semantic search."""

import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

_index = None


def _get_index():
    global _index
    if _index is None:
        from pinecone import Pinecone
        pc     = Pinecone(api_key=os.getenv("PINECONE_API_KEY", ""))
        _index = pc.Index("property-ai")
    return _index


def _sanitize_meta(metadata: dict) -> dict:
    """Convert all metadata values to Pinecone-safe types (str/int/float/bool/list)."""
    import numpy as np
    safe = {}
    for k, v in metadata.items():
        if isinstance(v, (str, bool, list)):
            safe[k] = v
        elif isinstance(v, (np.integer,)):
            safe[k] = int(v)
        elif isinstance(v, (np.floating, np.float64, np.float32, float)):
            safe[k] = float(v)
        elif isinstance(v, int):
            safe[k] = v
        else:
            safe[k] = str(v)
    return safe


def index_image(image_id: str, embedding: list, metadata: dict) -> bool:
    """Upsert a single image embedding + metadata to Pinecone."""
    try:
        idx = _get_index()
        idx.upsert(vectors=[{"id": image_id, "values": embedding,
                              "metadata": _sanitize_meta(metadata)}])
        return True
    except Exception as e:
        print(f"  [Pinecone] upsert failed for {image_id}: {e}")
        return False


def index_batch(vectors: list[dict]) -> bool:
    """
    Batch upsert. vectors = [{"id":..., "values":..., "metadata":...}, ...]
    Pinecone recommends batches of ≤100.
    """
    try:
        idx = _get_index()
        for i in range(0, len(vectors), 100):
            idx.upsert(vectors=vectors[i:i+100])
        return True
    except Exception as e:
        print(f"  [Pinecone] batch upsert failed: {e}")
        return False


def search(query_embedding: list, top_k: int = 20,
           filter_meta: dict = None) -> list:
    """
    Semantic search. Returns list of matches with id, score, metadata.
    """
    idx = _get_index()
    kwargs = {"vector": query_embedding, "top_k": top_k,
              "include_metadata": True}
    if filter_meta:
        kwargs["filter"] = filter_meta
    result = idx.query(**kwargs)
    return result.get("matches", [])


def get_index_stats() -> dict:
    """Return Pinecone index statistics as a plain JSON-serializable dict."""
    try:
        stats = _get_index().describe_index_stats()
        # Access attributes directly before serializing
        return {
            "total_vector_count": stats.total_vector_count,
            "dimension":          stats.dimension,
            "metric":             stats.metric,
            "index_fullness":     stats.index_fullness,
            "namespaces":         {k: {"vector_count": v.vector_count}
                                   for k, v in (stats.namespaces or {}).items()},
        }
    except Exception as e:
        return {"error": str(e)}
