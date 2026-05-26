from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from langchain_core.documents import Document
from src.generation.chain import RAGChain, RAGResponse, _format_context
from src.generation.guardrails import GuardrailResult, InputGuardrail, OutputGuardrail
from src.generation.prompts import PROMPT_REGISTRY, get_prompt

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def docs() -> list[Document]:
    return [
        Document(
            page_content="RAG combines retrieval and generation.",
            metadata={"source": "rag.txt", "doc_id": "d1"},
        ),
        Document(
            page_content="BM25 is a sparse retrieval algorithm.",
            metadata={"source": "bm25.txt", "doc_id": "d2"},
        ),
    ]


@pytest.fixture
def mock_retriever(docs: list[Document]) -> MagicMock:
    r = MagicMock()
    r.retrieve.return_value = docs
    return r


@pytest.fixture
def rag_chain(mock_retriever: MagicMock) -> RAGChain:
    chain = RAGChain(llm=MagicMock(), retriever=mock_retriever)
    chain._chain = MagicMock()
    chain._chain.invoke.return_value = "RAG is retrieval-augmented generation."
    chain._chain.stream.return_value = iter(["RAG ", "is ", "great."])
    return chain


# ── InputGuardrail ─────────────────────────────────────────────────────────────


class TestInputGuardrail:
    def test_passes_normal_query(self) -> None:
        g = InputGuardrail()
        assert g.check("What is RAG?").passed is True

    def test_blocks_empty_string(self) -> None:
        result = InputGuardrail().check("")
        assert result.passed is False
        assert result.reason == "empty_query"

    def test_blocks_whitespace_only(self) -> None:
        result = InputGuardrail().check("   ")
        assert result.passed is False
        assert result.reason == "empty_query"

    def test_blocks_too_short(self) -> None:
        result = InputGuardrail(min_length=5).check("hi")
        assert result.passed is False
        assert result.reason == "query_too_short"

    def test_blocks_too_long(self) -> None:
        result = InputGuardrail(max_length=10).check("a" * 11)
        assert result.passed is False
        assert result.reason == "query_too_long"

    def test_passes_at_exact_min_length(self) -> None:
        assert InputGuardrail(min_length=5).check("hello").passed is True

    def test_guardrail_result_has_no_reason_when_passed(self) -> None:
        r = GuardrailResult(passed=True)
        assert r.reason is None


# ── OutputGuardrail ───────────────────────────────────────────────────────────


class TestOutputGuardrail:
    def test_passes_normal_answer(self) -> None:
        g = OutputGuardrail()
        assert g.check("RAG stands for Retrieval-Augmented Generation.", "what is RAG?").passed

    def test_blocks_empty_answer(self) -> None:
        result = OutputGuardrail().check("", "any query")
        assert result.passed is False
        assert result.reason == "empty_answer"

    def test_passes_no_info_response(self) -> None:
        # "I don't have enough information" is an acceptable LLM reply — not a hard block
        result = OutputGuardrail().check(
            "I don't have enough information to answer this question.", "obscure query"
        )
        assert result.passed is True


# ── Prompts ────────────────────────────────────────────────────────────────────


class TestGetPrompt:
    def test_returns_v1(self) -> None:
        assert get_prompt("v1") is PROMPT_REGISTRY["v1"]

    def test_returns_v2(self) -> None:
        assert get_prompt("v2") is PROMPT_REGISTRY["v2"]

    def test_default_version_is_v1(self) -> None:
        assert get_prompt() is PROMPT_REGISTRY["v1"]

    def test_raises_on_unknown_version(self) -> None:
        with pytest.raises(ValueError, match="Unknown prompt version"):
            get_prompt("v99")

    def test_prompt_exposes_required_variables(self) -> None:
        prompt = get_prompt("v1")
        assert "context" in prompt.input_variables
        assert "question" in prompt.input_variables


# ── RAGChain ──────────────────────────────────────────────────────────────────


class TestRAGChain:
    def test_invoke_returns_rag_response(self, rag_chain: RAGChain, docs: list[Document]) -> None:
        response = rag_chain.invoke("What is RAG?", tenant_id="acme")
        assert isinstance(response, RAGResponse)
        assert response.answer == "RAG is retrieval-augmented generation."
        assert response.cached is False
        assert len(response.sources) > 0

    def test_invoke_raises_on_empty_query(self, rag_chain: RAGChain) -> None:
        with pytest.raises(ValueError, match="Input blocked"):
            rag_chain.invoke("", tenant_id="acme")

    def test_invoke_raises_on_short_query(self, rag_chain: RAGChain) -> None:
        with pytest.raises(ValueError, match="Input blocked"):
            rag_chain.invoke("hi", tenant_id="acme")

    def test_invoke_cache_hit_skips_generation(self, mock_retriever: MagicMock) -> None:
        import fakeredis
        from src.retrieval.cache import SemanticCache

        embedder = MagicMock()
        embedder.embed_query.return_value = [1.0] + [0.0] * 767
        cache = SemanticCache(fakeredis.FakeRedis(), embedder, ttl=300, similarity_threshold=0.90)

        chain = RAGChain(llm=MagicMock(), retriever=mock_retriever, cache=cache)
        chain._chain = MagicMock()
        chain._chain.invoke.return_value = "First answer."

        r1 = chain.invoke("What is RAG?", tenant_id="acme")
        assert r1.cached is False

        r2 = chain.invoke("What is RAG?", tenant_id="acme")
        assert r2.cached is True
        assert r2.answer == "First answer."
        # LLM chain should only have been called once
        assert chain._chain.invoke.call_count == 1

    def test_invoke_with_reranker_attaches_scores(self, mock_retriever: MagicMock) -> None:
        with patch("src.retrieval.reranker.CrossEncoder") as mock_ce_cls:
            mock_model = MagicMock()
            mock_model.predict.return_value = np.array([0.9, 0.1])
            mock_ce_cls.return_value = mock_model

            from src.retrieval.reranker import Reranker

            reranker = Reranker()

        chain = RAGChain(llm=MagicMock(), retriever=mock_retriever, reranker=reranker)
        chain._chain = MagicMock()
        chain._chain.invoke.return_value = "Reranked answer."

        response = chain.invoke("What is RAG?", tenant_id="acme")
        assert response.answer == "Reranked answer."
        for doc in response.sources:
            assert "reranker_score" in doc.metadata

    def test_stream_yields_tokens(self, rag_chain: RAGChain) -> None:
        tokens = list(rag_chain.stream("What is RAG?", tenant_id="acme"))
        assert tokens == ["RAG ", "is ", "great."]

    def test_stream_raises_on_invalid_query(self, rag_chain: RAGChain) -> None:
        with pytest.raises(ValueError, match="Input blocked"):
            list(rag_chain.stream("", tenant_id="acme"))

    def test_prompt_version_stored_in_response(self, mock_retriever: MagicMock) -> None:
        chain = RAGChain(llm=MagicMock(), retriever=mock_retriever, prompt_version="v2")
        chain._chain = MagicMock()
        chain._chain.invoke.return_value = "Answer."

        response = chain.invoke("What is RAG?", tenant_id="acme")
        assert response.prompt_version == "v2"

    def test_format_context_joins_with_separator(self, docs: list[Document]) -> None:
        context = _format_context(docs)
        assert "---" in context
        assert "rag.txt" in context
        assert "bm25.txt" in context
        assert "RAG combines retrieval" in context
