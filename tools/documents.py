"""search_documents(): search over data/docs/*.md.

Three modes, picked by settings.RETRIEVAL (the tool's interface never changes,
so neither agent loop knows or cares which one is used):
  keyword   TF-IDF over whole documents (the original, stages 1-4)
  semantic  embeddings + cosine similarity over chunks (stage 5)
  hybrid    both, merged with reciprocal rank fusion (stage 5)

Keyword search, explained:

This is retrieval with no vector database:
  - TF  (term frequency): how often a query word appears in a document.
  - IDF (inverse document frequency): words that appear in every document
    ("the", "employees") count for little; rare words ("vacation") count a lot.
  score(doc) = sum over query words of  tf(word, doc) * idf(word)
"""

import math
import re
from collections import Counter
from pathlib import Path

import settings
from tools import ToolError, vector_index

DOCS_DIR = Path(__file__).parent.parent / "data" / "docs"
STOPWORDS = {"a", "an", "the", "and", "or", "of", "to", "in", "on", "for", "is", "are", "do",
             "does", "how", "what", "many", "much", "i", "my", "we", "our", "be", "with", "at"}


def _stem(word: str) -> str:
    """A deliberately tiny stemmer (stage 4, Fix 1): meals->meal, traveling->travel, policies->policy.
    Real systems use Porter/Snowball stemmers or, better, embeddings (stage 5)."""
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    for suffix in ("ing", "ed", "s"):
        if len(word) > len(suffix) + 2 and word.endswith(suffix) and not word.endswith("ss"):
            return word[: -len(suffix)]
    return word


def _tokenize(text: str) -> list[str]:
    words = [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOPWORDS]
    return [_stem(w) for w in words] if settings.STEMMING else words


def _load_docs() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(DOCS_DIR.glob("*.md"))}


def search_documents(query: str, top_k: int = 3) -> dict:
    mode = settings.RETRIEVAL
    if mode == "keyword":
        return _keyword_doc_search(query, top_k)
    if mode not in ("semantic", "hybrid"):
        raise ToolError(f"Unknown retrieval mode '{mode}'")

    if mode == "semantic":
        ranked = [(score, chunk) for score, chunk in vector_index.semantic_search(query, top_k)]
    else:
        ranked = _hybrid(query, top_k)
    results = [{"doc": c["doc"], "score": round(score, 4), "snippet": c["text"]} for score, c in ranked]
    return {"query": query, "results": results}


# ── Stage 5: hybrid search with reciprocal rank fusion ───────────────────────

RRF_K = 60  # standard constant: dampens how much the very top ranks dominate


def _keyword_chunk_ranking(query: str) -> list[dict]:
    """TF-IDF like _keyword_doc_search, but over chunks, so it can be fused with semantic results."""
    chunks = vector_index.get_index()
    query_words = _tokenize(query)
    chunk_words = [Counter(_tokenize(c["text"])) for c in chunks]

    def idf(word: str) -> float:
        containing = sum(1 for counts in chunk_words if word in counts)
        return math.log((len(chunks) + 1) / (containing + 1)) + 1

    scored = []
    for chunk, counts in zip(chunks, chunk_words):
        score = sum(counts[w] / max(sum(counts.values()), 1) * idf(w) for w in query_words)
        if score > 0:
            scored.append((score, chunk))
    return [c for _, c in sorted(scored, key=lambda sc: -sc[0])]


def reciprocal_rank_fusion(rankings: list[list[dict]], k: int = RRF_K) -> list[tuple[float, dict]]:
    """score(chunk) = sum over rankings of 1 / (k + rank). Rewards chunks ranked well by BOTH methods,
    without needing their raw scores (TF-IDF and cosine are on different scales) to be comparable."""
    fused, by_id = {}, {}
    for ranking in rankings:
        for rank, chunk in enumerate(ranking, start=1):
            fused[chunk["id"]] = fused.get(chunk["id"], 0.0) + 1.0 / (k + rank)
            by_id[chunk["id"]] = chunk
    return sorted(((score, by_id[cid]) for cid, score in fused.items()), key=lambda sc: -sc[0])


def _hybrid(query: str, top_k: int) -> list[tuple[float, dict]]:
    semantic = [c for _, c in vector_index.semantic_search(query, len(vector_index.get_index()))]
    keyword = _keyword_chunk_ranking(query)
    return reciprocal_rank_fusion([keyword, semantic])[:top_k]


# ── Keyword search over whole documents (original) ──────────────────────────

def _keyword_doc_search(query: str, top_k: int) -> dict:
    docs = _load_docs()
    query_words = _tokenize(query)
    if not query_words:
        raise ToolError("Query has no searchable words")

    doc_words = {name: Counter(_tokenize(text)) for name, text in docs.items()}
    n_docs = len(docs)

    def idf(word: str) -> float:
        containing = sum(1 for counts in doc_words.values() if word in counts)
        return math.log((n_docs + 1) / (containing + 1)) + 1

    scores = {
        name: sum(counts[w] / max(sum(counts.values()), 1) * idf(w) for w in query_words)
        for name, counts in doc_words.items()
    }
    ranked = sorted((s, name) for name, s in scores.items() if s > 0)[::-1][:top_k]

    results = [
        {"doc": name, "score": round(score, 4), "snippet": _best_snippet(docs[name], query_words)}
        for score, name in ranked
    ]
    return {"query": query, "results": results}


def _best_snippet(text: str, query_words: list[str], max_lines: int = 4) -> str:
    """Return the lines of the doc that mention the most query words."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    scored = sorted(lines, key=lambda ln: -sum(w in _tokenize(ln) for w in query_words))
    best = [ln for ln in scored[:max_lines] if any(w in _tokenize(ln) for w in query_words)]
    # Keep the doc's original line order so the snippet reads naturally.
    return "\n".join(ln for ln in lines if ln in best) or lines[0]
