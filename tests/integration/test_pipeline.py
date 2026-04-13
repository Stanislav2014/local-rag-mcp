"""Integration test: full advanced search pipeline without FAISS.

Verifies that QueryExpander → HybridSearchEngine → CrossEncoderReranker
compose correctly and produce sensible top-K for two adversarial queries:
1. an exact-token query (`403 Forbidden`)
2. an abbreviation (`sqli`)
"""
from rag.search_engine import HybridSearchEngine
from rag.query_expansion import QueryExpander
from rag.reranker import CrossEncoderReranker


def _vector_like(chunks):
    """Build a deterministic 'vector' search that prefers semantically close phrases."""
    def _search(query: str, k: int):
        q = query.lower()
        scored = []
        for i, c in enumerate(chunks):
            text = c["text"].lower()
            overlap = sum(1 for tok in q.split() if tok in text)
            scored.append((overlap, i))
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [
            {**chunks[i], "score": float(s), "rank": rank + 1}
            for rank, (s, i) in enumerate(scored[:k])
        ]
    return _search


def test_pipeline_finds_exact_token(sample_chunks):
    expander = QueryExpander(llm_client=None)
    engine = HybridSearchEngine(sample_chunks, _vector_like(sample_chunks))
    reranker = CrossEncoderReranker(enabled=False)

    query = expander.expand("403 Forbidden")
    cands = engine.search(query, k=20)
    final = reranker.rerank(query, cands, top_k=3)

    assert final
    assert final[0]["source"] == "docs/http-errors.md"
    assert "403" in final[0]["text"]


def test_pipeline_expands_abbreviation_and_finds_sqli(sample_chunks):
    expander = QueryExpander(llm_client=None)
    engine = HybridSearchEngine(sample_chunks, _vector_like(sample_chunks))
    reranker = CrossEncoderReranker(enabled=False)

    query = expander.expand("sqli")
    assert "sql injection" in query.lower(), "expander should kick in"

    cands = engine.search(query, k=20)
    final = reranker.rerank(query, cands, top_k=3)

    assert final
    assert any("sqli" in c["source"] for c in final)
