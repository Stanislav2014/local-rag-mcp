"""TDD: hybrid search engine — tokenizer, BM25, RRF and HybridSearchEngine."""
import math

import pytest

from rag.search_engine import (
    tokenize,
    BM25Index,
    rrf_fuse,
    HybridSearchEngine,
)


# ---------------------------------------------------------------------------
# tokenize
# ---------------------------------------------------------------------------
class TestTokenize:
    def test_keeps_alphanumeric_tokens_and_lowercases(self):
        assert tokenize("403 Forbidden") == ["403", "forbidden"]

    def test_strips_punctuation_but_keeps_digits(self):
        assert tokenize("HTTP/1.1 404 Not-Found!") == ["http", "1", "1", "404", "not", "found"]

    def test_handles_empty_string(self):
        assert tokenize("") == []


# ---------------------------------------------------------------------------
# BM25Index
# ---------------------------------------------------------------------------
class TestBM25Index:
    def test_returns_chunk_with_exact_token_first(self, sample_chunks):
        bm = BM25Index(sample_chunks)
        results = bm.search("403 Forbidden", k=3)

        assert results, "expected at least one result"
        assert results[0]["source"] == "docs/http-errors.md"
        assert "403" in results[0]["text"]

    def test_results_have_required_fields(self, sample_chunks):
        bm = BM25Index(sample_chunks)
        results = bm.search("vacation", k=2)
        for r in results:
            assert "text" in r
            assert "source" in r
            assert "score" in r
            assert "rank" in r

    def test_returns_at_most_k_results(self, sample_chunks):
        bm = BM25Index(sample_chunks)
        assert len(bm.search("a", k=2)) <= 2

    def test_empty_query_returns_empty(self, sample_chunks):
        bm = BM25Index(sample_chunks)
        assert bm.search("", k=5) == []


# ---------------------------------------------------------------------------
# RRF fusion
# ---------------------------------------------------------------------------
class TestRRFFuse:
    def test_doc_in_both_lists_outranks_doc_in_one(self):
        list_a = [{"chunk_id": 1, "text": "a", "source": "x"},
                  {"chunk_id": 2, "text": "b", "source": "x"}]
        list_b = [{"chunk_id": 2, "text": "b", "source": "x"},
                  {"chunk_id": 3, "text": "c", "source": "x"}]
        fused = rrf_fuse([list_a, list_b], k_rrf=60)
        assert fused[0]["chunk_id"] == 2
        chunk_ids = [d["chunk_id"] for d in fused]
        assert set(chunk_ids) == {1, 2, 3}

    def test_score_formula(self):
        list_a = [{"chunk_id": 7, "text": "x", "source": "s"}]
        fused = rrf_fuse([list_a], k_rrf=60)
        assert math.isclose(fused[0]["score"], 1 / (60 + 1))

    def test_empty_inputs(self):
        assert rrf_fuse([], k_rrf=60) == []
        assert rrf_fuse([[], []], k_rrf=60) == []

    def test_dedup_uses_text_source_when_chunk_id_missing(self):
        a = [{"text": "hello", "source": "f.md"}]
        b = [{"text": "hello", "source": "f.md"}]
        fused = rrf_fuse([a, b], k_rrf=60)
        assert len(fused) == 1


# ---------------------------------------------------------------------------
# HybridSearchEngine
# ---------------------------------------------------------------------------
class TestHybridSearchEngine:
    def test_finds_exact_token_query_via_bm25(self, sample_chunks, fake_vector_search):
        engine = HybridSearchEngine(
            chunks=sample_chunks,
            vector_search=fake_vector_search,
            k_rrf=60,
            n_vec=5,
            n_bm25=5,
        )
        results = engine.search("403 Forbidden", k=3)
        assert results, "engine returned no results"
        top_sources = [r["source"] for r in results]
        assert "docs/http-errors.md" in top_sources
        assert results[0]["source"] == "docs/http-errors.md"

    def test_returns_at_most_k(self, sample_chunks, fake_vector_search):
        engine = HybridSearchEngine(sample_chunks, fake_vector_search)
        assert len(engine.search("anything", k=2)) <= 2

    def test_results_carry_score_and_rank(self, sample_chunks, fake_vector_search):
        engine = HybridSearchEngine(sample_chunks, fake_vector_search)
        results = engine.search("vacation policy", k=3)
        assert results
        for r in results:
            assert "score" in r
            assert "rank" in r

    def test_weighted_strategy(self, sample_chunks, fake_vector_search):
        engine = HybridSearchEngine(
            sample_chunks, fake_vector_search, strategy="weighted"
        )
        results = engine.search("vacation", k=3)
        assert results, "weighted strategy returned no results"

    def test_unknown_strategy_raises(self, sample_chunks, fake_vector_search):
        with pytest.raises(ValueError):
            HybridSearchEngine(sample_chunks, fake_vector_search, strategy="bogus")

    def test_empty_corpus(self, fake_vector_search):
        engine = HybridSearchEngine([], fake_vector_search)
        assert engine.search("anything", k=5) == []
