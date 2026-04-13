"""Cross-encoder reranker with a graceful-fallback "disabled" mode.

Production model: ``BAAI/bge-reranker-base`` loaded via
``sentence_transformers.CrossEncoder``. The model is loaded **lazily** so that
unit tests and Docker images that do not need it never pay the download /
RAM cost.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

log = logging.getLogger(__name__)


class CrossEncoderReranker:
    def __init__(
        self,
        *,
        model_name: str = "BAAI/bge-reranker-base",
        enabled: bool = True,
        model: Optional[Any] = None,
    ):
        self.model_name = model_name
        self.enabled = enabled
        self._model = model  # injected (tests) or lazily loaded

    # ------------------------------------------------------------------
    def _load_model(self) -> Any:
        if self._model is None:
            from sentence_transformers import CrossEncoder  # heavy import
            log.info("loading cross-encoder %s", self.model_name)
            self._model = CrossEncoder(self.model_name)
        return self._model

    # ------------------------------------------------------------------
    def rerank(self, query: str, candidates: list[dict], top_k: int = 5) -> list[dict]:
        if not candidates:
            return []
        if top_k <= 0:
            return []

        if not self.enabled:
            return list(candidates[:top_k])

        try:
            model = self._load_model()
            pairs = [(query, c.get("text", "")) for c in candidates]
            scores = model.predict(pairs)
        except Exception as e:
            log.warning("reranker failed (%s) — returning input order", e)
            return list(candidates[:top_k])

        scored = []
        for c, s in zip(candidates, scores):
            scored.append({**c, "rerank_score": float(s)})
        scored.sort(key=lambda x: x["rerank_score"], reverse=True)
        return scored[:top_k]
