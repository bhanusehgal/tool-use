"""Retrieval benchmark (stage 5): how well does each search mode find the right text?

No chat model involved, only search_documents() (and embeddings for semantic/hybrid),
so it's fast and free. For each query in evals/retrieval_cases.json we check:

  doc hit@1    the right document is the first result
  doc hit@3    the right document is in the top 3
  MRR          mean reciprocal rank of the right document (1 = always first, 0.5 = always second...)
  answer@3     the line that actually ANSWERS the question appears in the top-3 snippets
               (what the agent needs: the right doc with the wrong snippet doesn't help)

Usage:  py evals/run_retrieval_eval.py
"""

import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import settings  # noqa: E402
from tools import embeddings, vector_index  # noqa: E402
from tools.documents import search_documents  # noqa: E402

CASES = json.loads((ROOT / "evals" / "retrieval_cases.json").read_text(encoding="utf-8"))
TOP_K = 3

# (label, retrieval mode, stemming, use nomic prefixes)
CONFIGS = [
    ("keyword", "keyword", False, True),
    ("keyword + stemming", "keyword", True, True),
    ("semantic", "semantic", False, True),
    ("semantic, no prefixes", "semantic", False, False),
    ("hybrid", "hybrid", False, True),
    ("hybrid + stemming", "hybrid", True, True),
]


def evaluate(mode: str, stemming: bool, prefixes: bool) -> list[dict]:
    settings.RETRIEVAL, settings.STEMMING = mode, stemming
    if embeddings.USE_PREFIXES != prefixes:
        embeddings.USE_PREFIXES = prefixes
        vector_index.reset()  # the index must be rebuilt with/without prefixes
    rows = []
    for case in CASES:
        results = search_documents(case["query"], top_k=TOP_K)["results"]
        docs = list(dict.fromkeys(r["doc"] for r in results))  # unique, in rank order
        rank = docs.index(case["doc"]) + 1 if case["doc"] in docs else None
        snippets = " ".join(r["snippet"] for r in results)
        rows.append({**case, "rank": rank, "answer_found": case["answer"] in snippets,
                     "top_doc": results[0]["doc"] if results else None})
    return rows


def metrics(rows: list[dict]) -> dict:
    n = len(rows) or 1
    return {
        "hit@1": sum(r["rank"] == 1 for r in rows) / n,
        "hit@3": sum(r["rank"] is not None for r in rows) / n,
        "mrr": sum(1 / r["rank"] for r in rows if r["rank"]) / n,
        "answer@3": sum(r["answer_found"] for r in rows) / n,
    }


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    lines = [f"# Retrieval benchmark ({datetime.now():%Y-%m-%d %H:%M})", "",
             f"{len(CASES)} queries ({sum(c['type'] == 'exact' for c in CASES)} using the docs' own words, "
             f"{sum(c['type'] == 'paraphrase' for c in CASES)} paraphrased). top_k = {TOP_K}.", "",
             "| Mode | Query type | Doc hit@1 | Doc hit@3 | MRR | Answer line in top 3 |",
             "|---|---|---|---|---|---|"]
    misses = []
    for label, mode, stemming, prefixes in CONFIGS:
        rows = evaluate(mode, stemming, prefixes)
        for qtype in ("exact", "paraphrase", "all"):
            subset = [r for r in rows if qtype == "all" or r["type"] == qtype]
            m = metrics(subset)
            name = f"**{label}**" if qtype == "all" else label
            lines.append(f"| {name} | {qtype} | {m['hit@1']:.0%} | {m['hit@3']:.0%} | {m['mrr']:.2f} | {m['answer@3']:.0%} |")
        misses += [f"- {label}: \"{r['query']}\" → top doc {r['top_doc']}, answer line {'found' if r['answer_found'] else 'MISSING'}"
                   for r in rows if not r["answer_found"]]
    embeddings.USE_PREFIXES = True
    vector_index.reset()

    lines += ["", f"## Queries where the answer line was not in the top 3 ({len(misses)})", ""] + misses
    report = "\n".join(lines) + "\n"
    out = ROOT / "evals" / "results" / f"retrieval_{datetime.now():%Y-%m-%d_%H%M%S}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(report, encoding="utf-8")
    print(report)
    print(f"Saved to {out.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
