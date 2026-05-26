from __future__ import annotations

from typing import Any

import structlog
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

from src.config import RetrievalSettings
from src.vectorstore.base import BaseVectorStore

logger = structlog.get_logger(__name__)

# RRF smoothing constant — standard value from the original paper
_RRF_K = 60


class HybridRetriever:
    """
    Hybrid BM25 + dense vector retrieval with Reciprocal Rank Fusion.

    BM25 handles exact keyword matching; dense handles semantic similarity.
    RRF combines rankings without needing calibrated scores between the two.

    Per-tenant BM25 indexes are built lazily and cached in memory.
    """

    def __init__(
        self,
        vectorstore: BaseVectorStore,
        settings: RetrievalSettings,
    ) -> None:
        self._vectorstore = vectorstore
        self._settings = settings
        # {tenant_id: BM25Retriever}
        self._bm25_indexes: dict[str, BM25Retriever] = {}

    def build_bm25_index(self, documents: list[Document], tenant_id: str) -> None:
        """Build (or rebuild) the BM25 index for a tenant from its document corpus."""
        self._bm25_indexes[tenant_id] = BM25Retriever.from_documents(
            documents,
            k=self._settings.fetch_k,
        )
        logger.info("bm25_index_built", tenant=tenant_id, docs=len(documents))

    def retrieve(
        self,
        query: str,
        tenant_id: str,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[Document]:
        """Retrieve documents using hybrid search (or pure vector if BM25 not available)."""
        fetch_k = self._settings.fetch_k
        k = self._settings.k

        # Dense retrieval
        vector_docs = self._vectorstore.similarity_search(
            query, tenant_id, k=fetch_k, metadata_filter=metadata_filter
        )

        bm25 = self._bm25_indexes.get(tenant_id)
        if not bm25 or not self._settings.use_hybrid:
            logger.debug("vector_only_retrieval", tenant=tenant_id, reason="no bm25 index")
            return vector_docs[:k]

        # Sparse retrieval
        bm25_docs = bm25.invoke(query)

        merged = self._rrf_merge(bm25_docs, vector_docs)
        logger.info(
            "hybrid_retrieval_done",
            tenant=tenant_id,
            bm25_candidates=len(bm25_docs),
            vector_candidates=len(vector_docs),
            merged=len(merged),
        )
        return merged

    def _rrf_merge(
        self,
        bm25_docs: list[Document],
        vector_docs: list[Document],
    ) -> list[Document]:
        """Combine two ranked lists using Reciprocal Rank Fusion."""
        scores: dict[str, float] = {}
        doc_map: dict[str, Document] = {}

        for rank, doc in enumerate(bm25_docs):
            key = _doc_key(doc)
            scores[key] = scores.get(key, 0.0) + (self._settings.bm25_weight / (_RRF_K + rank + 1))
            doc_map[key] = doc

        for rank, doc in enumerate(vector_docs):
            key = _doc_key(doc)
            scores[key] = scores.get(key, 0.0) + (
                self._settings.vector_weight / (_RRF_K + rank + 1)
            )
            doc_map[key] = doc

        sorted_keys = sorted(scores, key=lambda x: scores[x], reverse=True)
        result = [doc_map[key] for key in sorted_keys[: self._settings.k]]

        # Attach RRF score to metadata for observability
        for key, doc in zip(sorted_keys, result, strict=False):
            doc.metadata["rrf_score"] = round(scores[key], 6)

        return result


def _doc_key(doc: Document) -> str:
    """Stable key for a document — prefers doc_id, falls back to content prefix."""
    doc_id: str | None = doc.metadata.get("doc_id")
    return doc_id or doc.page_content[:120]
