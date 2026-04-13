"""TDD: query expansion via dictionary + LLM rewriter."""
from unittest.mock import MagicMock

from rag.query_expansion import QueryExpander, ABBREVIATIONS


class TestAbbreviationDict:
    def test_known_abbreviation_expands(self):
        expander = QueryExpander(llm_client=None)
        out = expander.expand("sqli")
        assert "sql injection" in out.lower()
        assert "sqli" in out.lower(), "must keep original token for BM25"

    def test_xss_is_known(self):
        expander = QueryExpander(llm_client=None)
        out = expander.expand("xss")
        assert "cross" in out.lower() and "site" in out.lower() and "scripting" in out.lower()

    def test_case_insensitive(self):
        expander = QueryExpander(llm_client=None)
        assert "sql injection" in expander.expand("SQLi").lower()


class TestNoExpansion:
    def test_long_query_passthrough(self):
        expander = QueryExpander(llm_client=None)
        long_q = "how do I configure backups in production environment"
        assert expander.expand(long_q) == long_q

    def test_unknown_short_query_without_llm_returns_original(self):
        expander = QueryExpander(llm_client=None)
        assert expander.expand("zzz") == "zzz"

    def test_empty_query(self):
        expander = QueryExpander(llm_client=None)
        assert expander.expand("") == ""


class TestLLMExpansion:
    def test_llm_rewrite_used_when_short_unknown(self):
        client = MagicMock()
        client.chat.return_value = {
            "message": {"content": "weird obscure short query rewritten"}
        }
        expander = QueryExpander(llm_client=client, model="dummy")
        out = expander.expand("foo")
        assert "foo" in out, "must keep original token"
        assert "weird" in out, "must include LLM expansion"
        client.chat.assert_called_once()

    def test_llm_failure_returns_original(self):
        client = MagicMock()
        client.chat.side_effect = RuntimeError("boom")
        expander = QueryExpander(llm_client=client, model="dummy")
        assert expander.expand("foo") == "foo"


class TestAbbreviationsDict:
    def test_dict_contains_basic_security_abbrevs(self):
        for key in ("sqli", "xss", "csrf", "ssrf", "rce"):
            assert key in ABBREVIATIONS
