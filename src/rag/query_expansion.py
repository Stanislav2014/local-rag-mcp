"""Query expansion for short / abbreviation-heavy queries.

Strategy:
1. If the query is "long enough" — return it unchanged.
2. If any token matches a built-in abbreviation dictionary — append the
   expansion to the original query (so the original token survives for BM25).
3. Otherwise, if an LLM client is provided, ask it to rewrite the query.
4. On any failure — return the original query (graceful degrade).
"""
from __future__ import annotations

import logging
from typing import Any, Optional

log = logging.getLogger(__name__)

ABBREVIATIONS: dict[str, str] = {
    "sqli": "SQL Injection vulnerability",
    "xss":  "Cross Site Scripting vulnerability",
    "csrf": "Cross Site Request Forgery",
    "ssrf": "Server Side Request Forgery",
    "rce":  "Remote Code Execution",
    "lfi":  "Local File Inclusion",
    "rfi":  "Remote File Inclusion",
    "idor": "Insecure Direct Object Reference",
    "xxe":  "XML External Entity",
    "mfa":  "Multi Factor Authentication",
    "sso":  "Single Sign On",
    "jwt":  "JSON Web Token",
    "cors": "Cross Origin Resource Sharing",
}

REWRITE_SYSTEM = (
    "You are a query rewriter. Rewrite the user query into a longer, "
    "more descriptive search query. Keep all original technical terms. "
    "Reply with ONLY the rewritten query, no explanation."
)


class QueryExpander:
    def __init__(
        self,
        llm_client: Optional[Any] = None,
        *,
        model: str = "qwen3:0.6b",
        max_len: int = 4,
        abbreviations: Optional[dict[str, str]] = None,
    ):
        self.llm = llm_client
        self.model = model
        self.max_len = max_len
        self.abbrev = {k.lower(): v for k, v in (abbreviations or ABBREVIATIONS).items()}

    # ------------------------------------------------------------------
    def expand(self, query: str) -> str:
        if query is None:
            return ""
        q = query.strip()
        if not q:
            return ""

        tokens = q.split()
        if len(tokens) > self.max_len:
            return q

        # 1. Dictionary lookup — wins over LLM (deterministic, offline)
        expansions = []
        for tok in tokens:
            key = tok.lower()
            if key in self.abbrev:
                expansions.append(self.abbrev[key])
        if expansions:
            return f"{q} {' '.join(expansions)}"

        # 2. LLM rewriter — only for ASCII queries. On non-Latin scripts
        # (Cyrillic, etc.) small LLMs tend to translate the query into
        # English which destroys both BM25 matching and embedding similarity.
        if self.llm is not None and q.isascii():
            try:
                rewritten = self._llm_rewrite(q)
                if rewritten:
                    return f"{q} {rewritten}"
            except Exception as e:  # pragma: no cover - defensive
                log.warning("query expansion LLM failed: %s", e)

        return q

    # ------------------------------------------------------------------
    def _llm_rewrite(self, query: str) -> str:
        response = self.llm.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": REWRITE_SYSTEM},
                {"role": "user", "content": query},
            ],
        )
        # Support both ollama-python ({"message":{"content":...}}) and a
        # plain dict / object for testability.
        if isinstance(response, dict):
            msg = response.get("message") or {}
            content = msg.get("content", "") if isinstance(msg, dict) else ""
        else:
            content = getattr(getattr(response, "message", None), "content", "")
        return (content or "").strip()
