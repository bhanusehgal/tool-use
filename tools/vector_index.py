"""A vector index built by hand (stage 5): a list of chunk vectors plus cosine similarity.

At our size (~50 chunks x 768 numbers) a plain Python loop is instant. Real systems
with millions of vectors use a vector database (FAISS, pgvector, Qdrant...) that does
APPROXIMATE nearest-neighbour search, trading a little accuracy for a lot of speed.
The idea is identical: find the stored vectors that point in the most similar direction.
"""

import json
import math
from pathlib import Path

from tools import embeddings
from tools.chunking import load_chunks

INDEX_PATH = Path(__file__).parent.parent / "data" / "index.json"

_index: list[dict] | None = None


def cosine(a: list[float], b: list[float]) -> float:
    """cos(angle) = (a . b) / (|a| |b|): 1 = same direction, 0 = unrelated, -1 = opposite."""
    dot = sum(x * y for x, y in zip(a, b))
    norm = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / norm if norm else 0.0


def build_index(path: Path = INDEX_PATH) -> list[dict]:
    """Embed every chunk, reusing cached vectors for chunks whose text hasn't changed."""
    cache = {}
    if path.exists():
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved.get("model") == embeddings.EMBED_MODEL and saved.get("prefixes") == embeddings.USE_PREFIXES:
            cache = {c["hash"]: c["vector"] for c in saved["chunks"]}

    chunks = load_chunks()
    missing = [c for c in chunks if c["hash"] not in cache]
    if missing:
        vectors = embeddings.embed([c["text"] for c in missing], kind="document")
        cache.update({c["hash"]: v for c, v in zip(missing, vectors)})

    index = [{**c, "vector": cache[c["hash"]]} for c in chunks]
    path.write_text(json.dumps({"model": embeddings.EMBED_MODEL, "prefixes": embeddings.USE_PREFIXES,
                                "chunks": index}), encoding="utf-8")
    return index


def get_index() -> list[dict]:
    global _index
    if _index is None:
        _index = build_index()
    return _index


def reset() -> None:
    global _index
    _index = None


def semantic_search(query: str, top_k: int) -> list[tuple[float, dict]]:
    """Return the top_k chunks most similar in meaning to the query: [(score, chunk), ...]."""
    query_vector = embeddings.embed([query], kind="query")[0]
    scored = [(cosine(query_vector, c["vector"]), c) for c in get_index()]
    return sorted(scored, key=lambda sc: -sc[0])[:top_k]
