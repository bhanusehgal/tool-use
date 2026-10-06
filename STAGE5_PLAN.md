# Stage 5 Plan: Real Retrieval (RAG with embeddings)

> **Status: ✅ built and evaluated (2026-10-04).** Results: `EVALUATION.md` → Stage 5. Deviation from the plan: the expected "hybrid is best overall" was **not** confirmed; semantic alone did better on this data.

## Context
`search_documents` uses keyword scoring (TF-IDF). It only finds documents that share **exact words** with the query. "PTO", "pay rise", "work from home", "per diem for food" or "how much time off do I get" either miss or rank the wrong document, even though the answers are in the docs. Real RAG systems solve this with **embeddings**: vectors that place text with similar *meaning* close together.

You already have `nomic-embed-text` in Ollama, so this stays free and local.

**Goal:** build semantic search by hand (chunking, embedding, a vector index, cosine similarity), compare it with keyword search on a retrieval benchmark, and confirm with the stage 3 harness that it helps the agent end to end.

## What gets built

```
tools/
  chunking.py        split docs into chunks with metadata (doc, heading, text)
  embeddings.py      call Ollama /api/embed, cache vectors on disk
  vector_index.py    build/load the index; cosine similarity by hand
  documents.py       search_documents(): keyword | semantic | hybrid (same tool interface)
evals/
  retrieval_cases.json   ~20 queries → the document/chunk that answers them
  run_retrieval_eval.py  hit@1, hit@3, MRR for each retrieval mode (no LLM needed)
```

### 1. Chunking (`tools/chunking.py`)
- Split each markdown doc into chunks of one heading, paragraph or bullet group (our docs are small, so roughly 3–8 chunks each).
- Each chunk keeps `{"doc", "heading", "text", "id"}` so results can cite where they came from.
- Lesson: chunk size is a trade-off. Too big and the vector blurs several topics; too small and you lose context. Try both and measure.

### 2. Embeddings (`tools/embeddings.py`)
- Plain HTTP `POST /api/embed` to Ollama with `nomic-embed-text`, the same style as `llm.py`, with no new library.
- nomic-embed-text expects task prefixes: `search_document: ` for chunks and `search_query: ` for queries. Leaving them off measurably hurts retrieval, which makes a good experiment.
- Cache vectors in `data/index.json`, keyed by a hash of each chunk's text, so docs are only re-embedded when they change.

### 3. Vector index (`tools/vector_index.py`)
- At this size (~40 chunks × 768 dimensions), a Python list and hand-written cosine similarity are enough: `dot(a, b) / (|a| · |b|)`. No vector database and no numpy, so the maths stays visible.
- Note in the code where a real system would use FAISS, pgvector, etc., and why: millions of vectors and approximate search.

### 4. Three search modes behind the same tool
`search_documents(query, top_k)` keeps its exact interface, so **neither agent loop changes**. The mode is picked with a setting (`RETRIEVAL_MODE` / `--retrieval keyword|semantic|hybrid`):
- **keyword**: today's TF-IDF.
- **semantic**: embeddings + cosine similarity.
- **hybrid**: run both and merge with **reciprocal rank fusion** (`score = Σ 1/(60 + rank)`), a simple and strong standard technique.

Results return the chunk text with doc and heading, instead of whole-doc snippets.

### 5. Retrieval benchmark (`evals/retrieval_cases.json` + `run_retrieval_eval.py`)
This tests retrieval on its own, without an LLM, so it's fast and free:
- About 20 queries, each labelled with the doc (and chunk) that answers it. Half use the docs' own words ("vacation days"), half use **synonyms and paraphrases** ("PTO", "pay rise", "WFH internet money", "food allowance on trips", "how long is probation").
- Metrics per mode: **hit@1** (the right doc ranked first), **hit@3**, **MRR** (mean reciprocal rank).
- Expected result: keyword wins or ties on exact-word queries, semantic wins on paraphrases, hybrid is best overall. Measuring it is the point.

### 6. End-to-end check with the stage 3 harness
- Add 3–4 paraphrased **documents** cases to `evals/cases.json` (e.g. "How much PTO do I get in my first year?").
- Run `run_eval.py` with keyword vs hybrid retrieval and compare documents-category pass rates.

## Build order
1. Chunking + tests (offline).
2. Embeddings client + cache; cosine similarity + tests (tiny hand-made vectors, offline).
3. Semantic + hybrid modes in `search_documents`, same interface.
4. Retrieval benchmark + results table for the three modes.
5. New paraphrase cases in the harness; end-to-end comparison; write-up in `EVALUATION.md`.

## Verification
- Unit tests: chunk boundaries, cosine similarity (identical = 1, orthogonal = 0), cache reuse (second build makes 0 embedding calls), RRF merge order.
- Retrieval benchmark runs for all three modes; hybrid ≥ keyword on paraphrase queries.
- Harness: documents category on hybrid ≥ keyword, with no regressions elsewhere.

## Notes
- Your other setup is using `nomic-embed-text` right now. Sharing it is fine: embedding calls are tiny, and the index is built once and cached.
- Experiments to try: remove the nomic prefixes; change chunk size; change `top_k`; `nomic-embed-text` vs embeddings from a chat model.
