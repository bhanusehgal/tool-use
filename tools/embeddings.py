"""Turn text into vectors with Ollama's nomic-embed-text (stage 5).

Plain HTTP to /api/embed, the same style as llm.py, with no new library.

nomic-embed-text was trained with TASK PREFIXES: documents get "search_document: "
and queries get "search_query: ". Leaving them off measurably hurts retrieval
(try it: set USE_PREFIXES = False and re-run evals/run_retrieval_eval.py).
"""

import json
import os
import urllib.error
import urllib.request

OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "nomic-embed-text")
USE_PREFIXES = True

calls = 0  # how many embedding requests were made (the cache test checks this)


def embed(texts: list[str], kind: str) -> list[list[float]]:
    """kind: "document" or "query"."""
    global calls
    prefix = {"document": "search_document: ", "query": "search_query: "}[kind] if USE_PREFIXES else ""
    body = {"model": EMBED_MODEL, "input": [prefix + t for t in texts]}
    request = urllib.request.Request(f"{OLLAMA_URL}/api/embed", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=300) as resp:
            calls += 1
            return json.load(resp)["embeddings"]
    except urllib.error.URLError as e:
        raise RuntimeError(f"Embedding failed ({e}). Is Ollama running with '{EMBED_MODEL}' pulled?") from None
