"""Hybrid (BM25 + Vector) search engine with RRF or weighted-sum fusion.

This module is intentionally decoupled from FAISS / sentence-transformers:
the vector search is injected as a callable, which keeps the unit tests
fast and makes the engine reusable for different embedding backends.
"""
from __future__ import annotations

import re
from typing import Any, Callable, Iterable

from rank_bm25 import BM25Okapi


# ---------------------------------------------------------------------------
# Tokenisation
# ---------------------------------------------------------------------------
_TOKEN_RE = re.compile(r"[A-Za-z0-9]+")


def tokenize(text: str) -> list[str]:
    """Lowercase, alphanumeric-only tokeniser.

    Deliberately simple — no stemming, no stopwords — so that exact
    technical tokens like ``403`` or ``xss`` survive intact.
    """
    if not text:
        return []
    return [t.lower() for t in _TOKEN_RE.findall(text)]


# ---------------------------------------------------------------------------
# BM25 index
# ---------------------------------------------------------------------------
class BM25Index:
    """Thin wrapper around ``rank_bm25.BM25Okapi`` returning chunk dicts."""

    def __init__(self, chunks: list[dict]):
        self.chunks = list(chunks)
        self.tokenized = [tokenize(c.get("text", "")) for c in self.chunks]
        # rank_bm25 errors on empty corpus; guard explicitly
        self._bm25 = BM25Okapi(self.tokenized) if self.tokenized else None

    def search(self, query: str, k: int) -> list[dict]:
        if not query or not self._bm25 or k <= 0:
            return []
        q_tokens = tokenize(query)
        if not q_tokens:
            return []
        scores = self._bm25.get_scores(q_tokens)
        order = sorted(
            range(len(self.chunks)),
            key=lambda i: scores[i],
            reverse=True,
        )[:k]
        out: list[dict] = []
        for rank, idx in enumerate(order, start=1):
            score = float(scores[idx])
            if score <= 0:
                continue
            out.append({**self.chunks[idx], "score": score, "rank": rank})
        return out


# ---------------------------------------------------------------------------
# RRF fusion
# ---------------------------------------------------------------------------
def _doc_key(d: dict) -> tuple:
    if "chunk_id" in d and "source" in d:
        return ("cs", d["source"], d["chunk_id"])
    return ("ts", d.get("source"), d.get("text"))


def rrf_fuse(rankings: Iterable[list[dict]], k_rrf: int = 60) -> list[dict]:
    """Reciprocal Rank Fusion.

    ``rankings`` is an iterable of ranked lists. Documents are deduplicated
    by ``(source, chunk_id)`` (or by ``(source, text)`` when ``chunk_id`` is
    not available). The output preserves the chunk dict from whichever list
    saw the document first and adds a ``score`` field.
    """
    accum: dict[tuple, dict[str, Any]] = {}
    for ranked in rankings:
        if not ranked:
            continue
        for rank, doc in enumerate(ranked, start=1):
            key = _doc_key(doc)
            entry = accum.get(key)
            if entry is None:
                entry = {"doc": dict(doc), "score": 0.0}
                accum[key] = entry
            entry["score"] += 1.0 / (k_rrf + rank)

    fused = sorted(accum.values(), key=lambda e: e["score"], reverse=True)
    out = []
    for rank, entry in enumerate(fused, start=1):
        merged = {**entry["doc"], "score": entry["score"], "rank": rank}
        out.append(merged)
    return out


def _weighted_fuse(
    rankings: list[list[dict]],
    weights: list[float],
) -> list[dict]:
    """Weighted-sum fusion with min-max normalisation per ranking."""
    accum: dict[tuple, dict[str, Any]] = {}
    for ranked, w in zip(rankings, weights):
        if not ranked:
            continue
        scores = [float(d.get("score", 0.0)) for d in ranked]
        lo, hi = min(scores), max(scores)
        rng = hi - lo if hi > lo else 1.0
        for d, s in zip(ranked, scores):
            norm = (s - lo) / rng
            key = _doc_key(d)
            entry = accum.get(key)
            if entry is None:
                entry = {"doc": dict(d), "score": 0.0}
                accum[key] = entry
            entry["score"] += w * norm
    fused = sorted(accum.values(), key=lambda e: e["score"], reverse=True)
    return [
        {**e["doc"], "score": e["score"], "rank": rank}
        for rank, e in enumerate(fused, start=1)
    ]


# ---------------------------------------------------------------------------
# Hybrid search engine
# ---------------------------------------------------------------------------
VectorSearch = Callable[[str, int], list[dict]]


class HybridSearchEngine:
    """Combines BM25 and a pluggable vector search via RRF or weighted sum."""

    def __init__(
        self,
        chunks: list[dict],
        vector_search: VectorSearch,
        *,
        k_rrf: int = 60,
        n_vec: int = 50,
        n_bm25: int = 50,
        strategy: str = "rrf",
        weights: tuple[float, float] = (0.5, 0.5),
    ):
        if strategy not in {"rrf", "weighted"}:
            raise ValueError(f"unknown fusion strategy: {strategy}")
        self.chunks = list(chunks)
        self.vector_search = vector_search
        self.k_rrf = k_rrf
        self.n_vec = n_vec
        self.n_bm25 = n_bm25
        self.strategy = strategy
        self.weights = weights
        self.bm25 = BM25Index(self.chunks)

    def search(self, query: str, k: int = 20) -> list[dict]:
        if not self.chunks or k <= 0:
            return []

        vec_results = self.vector_search(query, self.n_vec) or []
        bm25_results = self.bm25.search(query, self.n_bm25)

        if self.strategy == "rrf":
            fused = rrf_fuse([vec_results, bm25_results], k_rrf=self.k_rrf)
        else:
            fused = _weighted_fuse(
                [vec_results, bm25_results],
                weights=list(self.weights),
            )

        return fused[:k]
