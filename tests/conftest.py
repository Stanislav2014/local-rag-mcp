"""Shared pytest fixtures and sys.path setup for the local-rag-mcp tests."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


import pytest


@pytest.fixture
def sample_chunks():
    """A small, deterministic corpus used across hybrid-search tests."""
    return [
        {
            "text": "When the server returns 403 Forbidden the client lacks permission for the resource.",
            "source": "docs/http-errors.md",
            "chunk_id": 0,
        },
        {
            "text": "404 Not Found indicates the requested resource does not exist on the server.",
            "source": "docs/http-errors.md",
            "chunk_id": 1,
        },
        {
            "text": "SQL injection (sqli) allows attackers to execute arbitrary SQL on the database.",
            "source": "docs/security/sqli.md",
            "chunk_id": 2,
        },
        {
            "text": "Cross site scripting xss lets an attacker run JavaScript in the victim browser.",
            "source": "docs/security/xss.md",
            "chunk_id": 3,
        },
        {
            "text": "The vacation policy grants employees 20 paid days off per year.",
            "source": "docs/hr/vacation.md",
            "chunk_id": 4,
        },
    ]


@pytest.fixture
def fake_vector_search(sample_chunks):
    """A deterministic stand-in for the real FAISS vector search.

    Returns chunks whose text contains the longest substring of the query —
    intentionally weak so BM25 can outperform it on exact-token queries.
    """

    def _search(query: str, k: int):
        q = query.lower()
        scored = []
        for i, c in enumerate(sample_chunks):
            text = c["text"].lower()
            overlap = sum(1 for tok in q.split() if tok in text)
            scored.append((overlap, i))
        scored.sort(key=lambda x: (-x[0], x[1]))
        results = []
        for rank, (score, idx) in enumerate(scored[:k]):
            results.append({**sample_chunks[idx], "score": float(score), "rank": rank + 1})
        return results

    return _search
