"""TDD: cross-encoder reranker (with disabled fallback)."""
from unittest.mock import MagicMock

from rag.reranker import CrossEncoderReranker


def _candidates():
    return [
        {"text": "irrelevant about lunch options", "source": "a", "score": 0.9},
        {"text": "exact answer about 403 forbidden", "source": "b", "score": 0.5},
        {"text": "tangential mention of permissions", "source": "c", "score": 0.7},
    ]


class TestDisabledReranker:
    def test_disabled_returns_first_top_k(self):
        r = CrossEncoderReranker(enabled=False)
        out = r.rerank("403 forbidden", _candidates(), top_k=2)
        assert len(out) == 2
        assert out[0]["source"] == "a"

    def test_disabled_handles_empty(self):
        r = CrossEncoderReranker(enabled=False)
        assert r.rerank("q", [], top_k=5) == []


class TestEnabledReranker:
    def test_uses_model_predict_to_sort(self):
        fake_model = MagicMock()
        fake_model.predict.return_value = [0.1, 0.9, 0.5]
        r = CrossEncoderReranker(enabled=True, model=fake_model)
        out = r.rerank("403 forbidden", _candidates(), top_k=3)
        assert [c["source"] for c in out] == ["b", "c", "a"]
        for c in out:
            assert "rerank_score" in c

    def test_top_k_truncation(self):
        fake_model = MagicMock()
        fake_model.predict.return_value = [0.3, 0.9, 0.1]
        r = CrossEncoderReranker(enabled=True, model=fake_model)
        out = r.rerank("q", _candidates(), top_k=2)
        assert len(out) == 2
        assert out[0]["source"] == "b"

    def test_empty_candidates(self):
        fake_model = MagicMock()
        r = CrossEncoderReranker(enabled=True, model=fake_model)
        assert r.rerank("q", [], top_k=5) == []
        fake_model.predict.assert_not_called()

    def test_model_failure_falls_back_to_input_order(self):
        fake_model = MagicMock()
        fake_model.predict.side_effect = RuntimeError("model died")
        r = CrossEncoderReranker(enabled=True, model=fake_model)
        out = r.rerank("q", _candidates(), top_k=2)
        assert len(out) == 2
        assert out[0]["source"] == "a"
