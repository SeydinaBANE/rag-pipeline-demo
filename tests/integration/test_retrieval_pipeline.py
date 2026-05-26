from __future__ import annotations

# Integration tests: Chroma (temp dir) + deterministic embeddings + real BM25/RRF
# CrossEncoder is mocked to avoid downloading the model in CI
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from langchain_core.documents import Document
from src.chunking.parent_child import ParentChildChunker
from src.config import ChunkingSettings, RetrievalSettings, VectorStoreSettings
from src.retrieval.hybrid import HybridRetriever
from src.retrieval.reranker import Reranker
from src.vectorstore.chroma import ChromaVectorStore

Settings = tuple[RetrievalSettings, VectorStoreSettings, ChunkingSettings]


@pytest.fixture
def integration_settings() -> Settings:
    return (
        RetrievalSettings(k=3, fetch_k=10, use_hybrid=True),
        VectorStoreSettings(collection_prefix="test"),
        ChunkingSettings(chunk_size=200, chunk_overlap=20, parent_chunk_size=600),
    )


@pytest.fixture
def deterministic_embedder() -> MagicMock:
    """Unique deterministic embeddings per text (hash-based) — no Ollama required."""
    embedder = MagicMock()

    def _embed(texts: list[str]) -> list[list[float]]:
        results = []
        for text in texts:
            seed = int(abs(hash(text[:50])) % (2**31))
            rng = np.random.default_rng(seed)
            vec = rng.random(768).astype(np.float32)
            vec /= np.linalg.norm(vec)
            results.append(vec.tolist())
        return results

    def _embed_query(text: str) -> list[float]:
        return _embed([text])[0]

    embedder.embed_documents.side_effect = _embed
    embedder.embed_query.side_effect = _embed_query
    return embedder


@pytest.fixture
def chroma_store(
    tmp_path: pytest.TempPathFactory,
    deterministic_embedder: MagicMock,
    integration_settings: Settings,
) -> ChromaVectorStore:
    """Ephemeral Chroma store backed by a temp directory."""
    _, vs_settings, _ = integration_settings
    vs_settings.persist_dir = tmp_path / ".chroma_integration"
    return ChromaVectorStore(deterministic_embedder, vs_settings)


@pytest.fixture
def indexed_corpus(
    chroma_store: ChromaVectorStore,
    integration_settings: Settings,
) -> list[Document]:
    """Chunk and index a small test corpus, return the chunks."""
    _, _, chunking_settings = integration_settings

    raw_docs = [
        Document(
            page_content=(
                "LangChain is a framework for developing applications "
                "powered by language models. It provides tools for chaining "
                "calls to LLMs, managing memory, and building agents. "
                "LangChain supports many LLM providers including Ollama."
            ),
            metadata={"source": "langchain.txt"},
        ),
        Document(
            page_content=(
                "Retrieval-Augmented Generation (RAG) combines information "
                "retrieval with text generation. A retriever fetches relevant "
                "documents from a knowledge base, and a language model generates "
                "an answer conditioned on those documents."
            ),
            metadata={"source": "rag.txt"},
        ),
        Document(
            page_content=(
                "BM25 is a ranking function used in information retrieval. "
                "It is based on term frequency and inverse document frequency. "
                "BM25 handles exact keyword matching and complements dense retrieval."
            ),
            metadata={"source": "bm25.txt"},
        ),
    ]

    chunker = ParentChildChunker(chunking_settings)
    chunks = chunker.split(raw_docs)
    chroma_store.add_documents(chunks, tenant_id="integration")
    return chunks


class TestHybridRetrieverIntegration:
    def test_vector_retrieval_returns_relevant_docs(
        self,
        chroma_store: ChromaVectorStore,
        integration_settings: Settings,
        indexed_corpus: list[Document],
    ) -> None:
        retrieval_settings, *_ = integration_settings
        retriever = HybridRetriever(chroma_store, retrieval_settings)

        results = retriever.retrieve("What is RAG?", tenant_id="integration")
        assert len(results) > 0
        assert len(results) <= retrieval_settings.k

    def test_hybrid_retrieval_with_bm25(
        self,
        chroma_store: ChromaVectorStore,
        integration_settings: Settings,
        indexed_corpus: list[Document],
    ) -> None:
        retrieval_settings, *_ = integration_settings
        retriever = HybridRetriever(chroma_store, retrieval_settings)
        retriever.build_bm25_index(indexed_corpus, tenant_id="integration")

        results = retriever.retrieve("BM25 term frequency", tenant_id="integration")
        assert len(results) > 0
        for doc in results:
            assert "rrf_score" in doc.metadata

    def test_different_queries_return_different_results(
        self,
        chroma_store: ChromaVectorStore,
        integration_settings: Settings,
        indexed_corpus: list[Document],
    ) -> None:
        retrieval_settings, *_ = integration_settings
        retriever = HybridRetriever(chroma_store, retrieval_settings)
        retriever.build_bm25_index(indexed_corpus, tenant_id="integration")

        r1 = retriever.retrieve("LangChain agents", tenant_id="integration")
        r2 = retriever.retrieve("BM25 ranking", tenant_id="integration")

        assert r1[0].page_content != r2[0].page_content or len(r1) != len(r2)

    def test_tenant_isolation_in_retrieval(
        self,
        chroma_store: ChromaVectorStore,
        integration_settings: Settings,
        indexed_corpus: list[Document],
    ) -> None:
        retrieval_settings, *_ = integration_settings
        retriever = HybridRetriever(chroma_store, retrieval_settings)

        results = retriever.retrieve("RAG", tenant_id="other-tenant")
        assert results == []


class TestRerankerIntegration:
    def test_reranker_reorders_after_retrieval(
        self,
        chroma_store: ChromaVectorStore,
        integration_settings: Settings,
        indexed_corpus: list[Document],
    ) -> None:
        retrieval_settings, *_ = integration_settings
        retriever = HybridRetriever(chroma_store, retrieval_settings)
        candidates = retriever.retrieve("retrieval augmented generation", tenant_id="integration")

        with patch("src.retrieval.reranker.CrossEncoder") as mock_ce_cls:
            mock_model = MagicMock()
            n = len(candidates)
            mock_model.predict.return_value = np.linspace(0.9, 0.1, n)
            mock_ce_cls.return_value = mock_model

            reranker = Reranker()
            reranked = reranker.rerank("retrieval augmented generation", candidates)

        assert len(reranked) == n
        scores = [d.metadata["reranker_score"] for d in reranked]
        assert scores == sorted(scores, reverse=True)
