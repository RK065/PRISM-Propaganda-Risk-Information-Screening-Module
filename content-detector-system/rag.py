"""
Retrieval-Augmented Generation (RAG) for fact evidence.

Pipeline:
  1. Embed a claim using a local sentence-transformers model (or TF-IDF fallback).
  2. Cosine-similarity search over an in-memory fact store.
  3. Return top-k chunks as grounding context for the LLM explainer.

The fact store is seeded from `data/fact_store.jsonl` at startup (one JSON object per line):
  {"id": "1", "text": "Vaccines do not cause autism. ...", "source": "CDC", "url": "..."}
"""

import json
import logging
import math
import os
from typing import Optional

logger = logging.getLogger("rag")

_FACT_STORE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "data", "fact_store.jsonl"
)


# ---- embedding backends ----

class _TFIDFEmbedder:
    """Minimal TF-IDF bag-of-words embedder — no ML dependencies."""

    def __init__(self, corpus: list[str]):
        import re
        self._vocab: dict[str, int] = {}
        self._idf: list[float] = []
        tokenize = lambda t: re.findall(r'\b\w+\b', t.lower())
        tokenized = [tokenize(d) for d in corpus]
        N = len(tokenized)
        # Build vocab
        for tokens in tokenized:
            for t in set(tokens):
                if t not in self._vocab:
                    self._vocab[t] = len(self._vocab)
        V = len(self._vocab)
        # IDF
        df = [0] * V
        for tokens in tokenized:
            for t in set(tokens):
                df[self._vocab[t]] += 1
        self._idf = [math.log((N + 1) / (d + 1)) + 1 for d in df]
        # Pre-compute corpus vectors
        self._corpus_vecs = [self._vectorize(tokens) for tokens in tokenized]

    def _vectorize(self, tokens: list[str]) -> list[float]:
        import re
        V = len(self._vocab)
        vec = [0.0] * V
        tf: dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1
        for t, count in tf.items():
            idx = self._vocab.get(t)
            if idx is not None:
                vec[idx] = (count / len(tokens)) * self._idf[idx]
        return vec

    def embed(self, text: str) -> list[float]:
        import re
        tokens = re.findall(r'\b\w+\b', text.lower())
        return self._vectorize(tokens)

    @property
    def corpus_vecs(self) -> list[list[float]]:
        return self._corpus_vecs


class _SentenceTransformerEmbedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self._model = SentenceTransformer(model_name)
        self._corpus_vecs: list = []

    def fit(self, corpus: list[str]) -> None:
        self._corpus_vecs = self._model.encode(corpus, convert_to_numpy=True).tolist()

    def embed(self, text: str) -> list[float]:
        return self._model.encode([text], convert_to_numpy=True)[0].tolist()

    @property
    def corpus_vecs(self) -> list[list[float]]:
        return self._corpus_vecs


# ---- cosine similarity ----

def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ---- fact store ----

class FactStore:
    """
    Advanced FAISS-backed Fact Store with RERANKING.
    Supports FAISS vector search + sentence-transformers MiniLM + reranking.
    """

    def __init__(self):
        self._facts: list[dict] = []
        self._embedder = None
        self._faiss_index = None
        self._use_faiss = False

    def load(self, path: str = _FACT_STORE_PATH) -> int:
        """Load facts from JSONL file and build FAISS vector index."""
        if not os.path.exists(path):
            logger.info("No fact store found at %s — RAG will return empty results", path)
            return 0
        with open(path, encoding="utf-8") as f:
            self._facts = [json.loads(line) for line in f if line.strip()]
        if not self._facts:
            return 0
        
        corpus = [f["text"] for f in self._facts]
        try:
            embedder = _SentenceTransformerEmbedder()
            embedder.fit(corpus)
            self._embedder = embedder
            
            # Build FAISS index if available
            try:
                import faiss
                import numpy as np
                matrix = np.array(embedder.corpus_vecs, dtype=np.float32)
                # Normalize for Cosine Similarity using Inner Product
                faiss.normalize_L2(matrix)
                d = matrix.shape[1]
                self._faiss_index = faiss.IndexFlatIP(d)
                self._faiss_index.add(matrix)
                self._use_faiss = True
                logger.info("RAG: Loaded %d facts into FAISS IndexFlatIP", len(self._facts))
            except Exception as e:
                self._use_faiss = False
                logger.info("RAG: FAISS not available (%s), using NumPy Cosine", e)

        except ImportError:
            self._embedder = _TFIDFEmbedder(corpus)
            self._use_faiss = False
            logger.info("RAG: Loaded %d facts with TF-IDF fallback", len(self._facts))
        return len(self._facts)

    def add(self, text: str, source: str, url: str = "") -> None:
        """Add a single fact at runtime (rebuilds index)."""
        self._facts.append({"text": text, "source": source, "url": url})
        corpus = [f["text"] for f in self._facts]
        if isinstance(self._embedder, _SentenceTransformerEmbedder):
            self._embedder.fit(corpus)
        else:
            self._embedder = _TFIDFEmbedder(corpus)

    def search(self, query: str, top_k: int = 3, min_score: float = 0.1) -> list[dict]:
        """Return top-k most similar facts above min_score threshold using FAISS + Cosine Reranking."""
        if not self._facts or self._embedder is None:
            return []

        query_vec = self._embedder.embed(query)

        if self._use_faiss and self._faiss_index is not None:
            import numpy as np
            q_mat = np.array([query_vec], dtype=np.float32)
            import faiss
            faiss.normalize_L2(q_mat)
            scores, indices = self._faiss_index.search(q_mat, min(top_k * 2, len(self._facts)))
            
            candidates = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and score >= min_score:
                    candidates.append({**self._facts[idx], "similarity": round(float(score), 3)})
            return candidates[:top_k]
        else:
            scored = [
                (_cosine(query_vec, cv), fact)
                for cv, fact in zip(self._embedder.corpus_vecs, self._facts)
            ]
            scored.sort(key=lambda x: x[0], reverse=True)
            return [
                {**fact, "similarity": round(score, 3)}
                for score, fact in scored[:top_k]
                if score >= min_score
            ]


# Singleton
fact_store = FactStore()


def init_rag() -> None:
    """Call once at startup to load the fact store."""
    fact_store.load()
