from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from langchain_core.documents import Document
from src.config import RetrievalSettings
from src.retrieval.cache import CachedEntry, SemanticCache, _cosine_similarity
from src.retrieval.hybrid import HybridRetriever, _doc_key
from src.retrieval.reranker import Reranker

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def retrieval_settings() -> RetrievalSettings:
    return RetrievalSettings(
        k=3,
        fetch_k=10,
        use_hybrid=True,
        bm25_weight=0.3,
        vector_weight=0.7,
        use_reranker=True,
        cache_ttl=300,
        cache_similarity_threshold=0.95,
    )


@pytest.fixture
def corpus() -> list[Document]:
    return [
        Document(
            page_content="LangChain provides abstractions for LLM pipelines.",
            metadata={"source": "lc.txt", "doc_id": "doc-0"},
        ),
        Document(
            page_content="RAG combines retrieval with generation for accurate answers.",
            metadata={"source": "rag.txt", "doc_id": "doc-1"},
        ),
        Document(
            page_content="Vector databases store high-dimensional embeddings.",
            metadata={"source": "vec.txt", "doc_id": "doc-2"},
        ),
        Document(
            page_content="BM25 is a classic sparse retrieval algorithm based on term frequency.",
            metadata={"source": "bm25.txt", "doc_id": "doc-3"},
        ),
        Document(
            page_content=(
                "Cross-encoders rerank documents using full attention " "over query and document."
            ),
            metadata={"source": "rerank.txt", "doc_id": "doc-4"},
        ),
    ]


@pytest.fixture
def mock_vectorstore(corpus: list[Document]) -> MagicMock:
    vs = MagicMock()
    vs.similarity_search.return_value = corpus[:3]
    return vs


@pytest.fixture
def fake_redis():
    import fakeredis

    return fakeredis.FakeRedis()


# ── HybridRetriever ───────────────────────────────────────────────────────────


class TestHybridRetriever:
    def test_vector_only_without_bm25_index(
        self,
        mock_vectorstore: MagicMock,
        retrieval_settings: RetrievalSettings,
        corpus: list[Document],
    ) -> None:
        retriever = HybridRetriever(mock_vectorstore, retrieval_settings)
        results = retriever.retrieve("what is RAG?", tenant_id="acme")

        mock_vectorstore.similarity_search.assert_called_once()
        assert len(results) <= retrieval_settings.k

    def test_hybrid_retrieval_after_bm25_build(
        self,
        mock_vectorstore: MagicMock,
        retrieval_settings: RetrievalSettings,
        corpus: list[Document],
    ) -> None:
        retriever = HybridRetriever(mock_vectorstore, retrieval_settings)
        retriever.build_bm25_index(corpus, tenant_id="acme")

        results = retriever.retrieve("BM25 retrieval algorithm", tenant_id="acme")
        assert len(results) <= retrieval_settings.k

    def test_rrf_attaches_score_to_metadata(
        self,
        mock_vectorstore: MagicMock,
        retrieval_settings: RetrievalSettings,
        corpus: list[Document],
    ) -> None:
        retriever = HybridRetriever(mock_vectorstore, retrieval_settings)
        retriever.build_bm25_index(corpus, tenant_id="acme")

        results = retriever.retrieve("vector database embeddings", tenant_id="acme")
        for doc in results:
            assert "rrf_score" in doc.metadata
            assert isinstance(doc.metadata["rrf_score"], float)

    def test_rrf_merge_respects_k(
        self,
        mock_vectorstore: MagicMock,
        retrieval_settings: RetrievalSettings,
        corpus: list[Document],
    ) -> None:
        retriever = HybridRetriever(mock_vectorstore, retrieval_settings)
        retriever.build_bm25_index(corpus, tenant_id="acme")

        results = retriever.retrieve("query", tenant_id="acme")
        assert len(results) <= retrieval_settings.k

    def test_doc_key_uses_doc_id_when_present(self) -> None:
        doc = Document(page_content="content", metadata={"doc_id": "my-id"})
        assert _doc_key(doc) == "my-id"

    def test_doc_key_falls_back_to_content(self) -> None:
        doc = Document(page_content="short content", metadata={})
        assert _doc_key(doc) == "short content"

    def test_deduplication_in_rrf(
        self,
        retrieval_settings: RetrievalSettings,
    ) -> None:
        """Same document appearing in both BM25 and vector results should appear once."""
        shared_doc = Document(
            page_content="Shared document",
            metadata={"doc_id": "shared-0"},
        )
        vs = MagicMock()
        vs.similarity_search.return_value = [shared_doc]

        retriever = HybridRetriever(vs, retrieval_settings)
        # BM25 will also find shared_doc since it's in the corpus
        retriever.build_bm25_index([shared_doc], tenant_id="acme")

        results = retriever.retrieve("shared document", tenant_id="acme")
        ids = [_doc_key(d) for d in results]
        assert len(ids) == len(set(ids))


# ── Reranker ─────────────────────────────────────────────────────────────────


class TestReranker:
    def test_reranker_returns_sorted_by_score(self, corpus: list[Document]) -> None:
        with patch("src.retrieval.reranker.CrossEncoder") as mock_ce_cls:
            mock_model = MagicMock()
            mock_model.predict.return_value = np.array([0.3, 0.9, 0.1, 0.7, 0.5])
            mock_ce_cls.return_value = mock_model

            reranker = Reranker()
            results = reranker.rerank("RAG", corpus)

        assert results[0].metadata["reranker_score"] >= results[1].metadata["reranker_score"]

    def test_reranker_attaches_score_to_metadata(self, corpus: list[Document]) -> None:
        with patch("src.retrieval.reranker.CrossEncoder") as mock_ce_cls:
            mock_model = MagicMock()
            mock_model.predict.return_value = np.array([0.8, 0.6, 0.4, 0.2, 0.1])
            mock_ce_cls.return_value = mock_model

            reranker = Reranker()
            results = reranker.rerank("query", corpus)

        for doc in results:
            assert "reranker_score" in doc.metadata

    def test_reranker_respects_top_k(self, corpus: list[Document]) -> None:
        with patch("src.retrieval.reranker.CrossEncoder") as mock_ce_cls:
            mock_model = MagicMock()
            mock_model.predict.return_value = np.array([0.9, 0.8, 0.7, 0.6, 0.5])
            mock_ce_cls.return_value = mock_model

            reranker = Reranker()
            results = reranker.rerank("query", corpus, top_k=2)

        assert len(results) == 2

    def test_reranker_empty_input(self) -> None:
        with patch("src.retrieval.reranker.CrossEncoder") as mock_ce_cls:
            mock_ce_cls.return_value = MagicMock()
            reranker = Reranker()
            assert reranker.rerank("query", []) == []


# ── SemanticCache ─────────────────────────────────────────────────────────────


class TestSemanticCache:
    def _make_cache(
        self,
        fake_redis: MagicMock,
        threshold: float = 0.95,
    ) -> tuple[SemanticCache, MagicMock]:
        embedder = MagicMock()
        embedder.embed_query.return_value = [1.0] + [0.0] * 767
        cache = SemanticCache(
            redis_client=fake_redis,
            embedder=embedder,
            ttl=300,
            similarity_threshold=threshold,
        )
        return cache, embedder

    def test_cache_miss_on_empty(self, fake_redis: MagicMock) -> None:
        cache, _ = self._make_cache(fake_redis)
        result = cache.get("what is RAG?", "acme")
        assert result is None

    def test_set_and_get_exact_query(self, fake_redis: MagicMock, corpus: list[Document]) -> None:
        cache, _ = self._make_cache(fake_redis, threshold=0.90)
        cache.set("what is RAG?", "RAG is retrieval-augmented generation.", corpus[:2], "acme")

        result = cache.get("what is RAG?", "acme")
        assert result is not None
        assert result.answer == "RAG is retrieval-augmented generation."

    def test_cache_hit_above_threshold(self, fake_redis: MagicMock, corpus: list[Document]) -> None:
        cache, embedder = self._make_cache(fake_redis, threshold=0.90)
        vec = np.array([1.0] + [0.0] * 767, dtype=np.float32)
        embedder.embed_query.return_value = vec.tolist()

        cache.set("what is RAG?", "RAG answer", corpus[:1], "acme")
        result = cache.get("what is RAG?", "acme")
        assert result is not None

    def test_cache_miss_below_threshold(
        self, fake_redis: MagicMock, corpus: list[Document]
    ) -> None:
        # Store with one vector, query with an orthogonal vector
        embedder = MagicMock()
        cache = SemanticCache(fake_redis, embedder, ttl=300, similarity_threshold=0.95)

        embedder.embed_query.return_value = [1.0] + [0.0] * 767
        cache.set("first query", "first answer", corpus[:1], "acme")

        # Orthogonal vector → cosine similarity = 0
        embedder.embed_query.return_value = [0.0, 1.0] + [0.0] * 766
        result = cache.get("completely different query", "acme")
        assert result is None

    def test_tenant_isolation(self, fake_redis: MagicMock, corpus: list[Document]) -> None:
        cache, _ = self._make_cache(fake_redis, threshold=0.90)
        cache.set("question", "answer for tenant A", corpus[:1], "tenant-a")

        result = cache.get("question", "tenant-b")
        assert result is None

    def test_invalidate_clears_tenant(self, fake_redis: MagicMock, corpus: list[Document]) -> None:
        cache, _ = self._make_cache(fake_redis, threshold=0.90)
        cache.set("question", "answer", corpus[:1], "acme")
        cache.invalidate("acme")

        result = cache.get("question", "acme")
        assert result is None

    def test_stats_returns_count(self, fake_redis: MagicMock, corpus: list[Document]) -> None:
        cache, _ = self._make_cache(fake_redis, threshold=0.90)
        cache.set("q1", "a1", corpus[:1], "acme")
        cache.set("q2", "a2", corpus[:1], "acme")

        stats = cache.stats("acme")
        assert stats["cached_entries"] == 2

    def test_cached_entry_to_documents(self, corpus: list[Document]) -> None:
        entry = CachedEntry.from_result("q", "a", corpus[:2])
        docs = entry.to_documents()
        assert len(docs) == 2
        assert all(isinstance(d, Document) for d in docs)


# ── cosine similarity ─────────────────────────────────────────────────────────


class TestCosineSimilarity:
    def test_identical_vectors(self) -> None:
        v = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        assert float(_cosine_similarity(v, v)) == pytest.approx(1.0)

    def test_orthogonal_vectors(self) -> None:
        a = np.array([1.0, 0.0], dtype=np.float32)
        b = np.array([0.0, 1.0], dtype=np.float32)
        assert float(_cosine_similarity(a, b)) == pytest.approx(0.0)

    def test_zero_vector_returns_zero(self) -> None:
        a = np.array([0.0, 0.0], dtype=np.float32)
        b = np.array([1.0, 0.0], dtype=np.float32)
        assert float(_cosine_similarity(a, b)) == 0.0
