"""Tests for stage 5 retrieval: chunking, cosine, RRF, index cache. No Ollama needed
(a fake embedder stands in for nomic-embed-text).

Run from the project folder:  py -m unittest discover tests
"""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

import settings  # noqa: E402
from tools import documents, embeddings, vector_index  # noqa: E402
from tools.chunking import chunk_document, load_chunks  # noqa: E402
from tools.vector_index import build_index, cosine  # noqa: E402


def fake_embed(texts, kind):
    """Deterministic 'embedding': counts of a few keywords. Good enough to test the plumbing."""
    fake_embed.calls += 1
    vocab = ["meal", "hotel", "vacation", "raise", "trial", "internet", "atlas", "food"]
    return [[t.lower().count(w) + 0.01 for w in vocab] for t in texts]


fake_embed.calls = 0


class ChunkingTests(unittest.TestCase):
    def test_bullets_become_separate_chunks_with_title(self):
        chunks = chunk_document("x.md", "# Expense Policy\n\nIntro line.\n\n- Meals: $60.\n- Hotels: $200.\n")
        self.assertEqual([c["text"] for c in chunks],
                         ["Expense Policy: Intro line.", "Expense Policy: Meals: $60.", "Expense Policy: Hotels: $200."])
        self.assertEqual(chunks[1]["id"], "x.md#1")

    def test_real_docs_have_the_meal_chunk(self):
        texts = [c["text"] for c in load_chunks()]
        self.assertIn("Expense Policy: Meals while traveling: up to $60 per day.", texts)
        self.assertFalse(any(t.startswith("# ") for t in texts))


class MathTests(unittest.TestCase):
    def test_cosine(self):
        self.assertAlmostEqual(cosine([1, 2, 3], [1, 2, 3]), 1.0)
        self.assertAlmostEqual(cosine([1, 0], [0, 1]), 0.0)
        self.assertAlmostEqual(cosine([1, 0], [-1, 0]), -1.0)
        self.assertEqual(cosine([0, 0], [1, 1]), 0.0)

    def test_rrf_rewards_agreement(self):
        a, b, c = {"id": "a"}, {"id": "b"}, {"id": "c"}
        fused = documents.reciprocal_rank_fusion([[a, b, c], [b, a]])
        # a: 1/61 + 1/62, b: 1/62 + 1/61 (tie), c: 1/63 only -> c last
        self.assertEqual(fused[-1][1]["id"], "c")
        self.assertAlmostEqual(fused[0][0], 1 / 61 + 1 / 62)


class IndexTests(unittest.TestCase):
    def setUp(self):
        self._real_embed = embeddings.embed
        embeddings.embed = fake_embed
        vector_index.reset()

    def tearDown(self):
        embeddings.embed = self._real_embed
        vector_index.reset()
        settings.apply_variant("baseline")

    def test_cache_reuses_vectors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.json"
            fake_embed.calls = 0
            build_index(path)
            self.assertEqual(fake_embed.calls, 1)          # one batch for all chunks
            build_index(path)
            self.assertEqual(fake_embed.calls, 1)          # second build: everything cached
            saved = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(len(saved["chunks"]), len(load_chunks()))

    def test_semantic_mode_returns_chunks_same_interface(self):
        with tempfile.TemporaryDirectory() as tmp:
            vector_index.INDEX_PATH, real_path = Path(tmp) / "index.json", vector_index.INDEX_PATH
            try:
                vector_index._index = build_index(vector_index.INDEX_PATH)
                settings.RETRIEVAL = "semantic"
                result = documents.search_documents("meal allowance", top_k=2)
                self.assertEqual(set(result["results"][0]), {"doc", "score", "snippet"})
                self.assertIn("Meals while traveling", result["results"][0]["snippet"])
                settings.RETRIEVAL = "hybrid"
                self.assertEqual(len(documents.search_documents("meal allowance", top_k=2)["results"]), 2)
            finally:
                vector_index.INDEX_PATH = real_path

    def test_variants_set_retrieval(self):
        settings.apply_variant("all_semantic")
        self.assertEqual(settings.RETRIEVAL, "semantic")
        self.assertIn("RETRIEVAL=semantic", settings.active())
        settings.apply_variant("all")
        self.assertEqual(settings.RETRIEVAL, "keyword")


class RetrievalCaseTests(unittest.TestCase):
    def test_answers_exist_in_docs(self):
        cases = json.loads((ROOT / "evals" / "retrieval_cases.json").read_text(encoding="utf-8"))
        for case in cases:
            with self.subTest(query=case["query"]):
                text = (ROOT / "data" / "docs" / case["doc"]).read_text(encoding="utf-8")
                self.assertIn(case["answer"], " ".join(text.split()))


if __name__ == "__main__":
    unittest.main()
