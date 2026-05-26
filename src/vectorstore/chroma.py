from __future__ import annotations

from typing import Any

import structlog
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from src.config import VectorStoreSettings
from src.vectorstore.base import BaseVectorStore
from src.vectorstore.tenant import collection_name

logger = structlog.get_logger(__name__)


class ChromaVectorStore(BaseVectorStore):
    """
    ChromaDB vector store with per-tenant namespace isolation.

    Each tenant gets its own collection (rag_{tenant_id}), ensuring
    complete data isolation at the collection level (see ADR 004).
    """

    def __init__(self, embeddings: Embeddings, settings: VectorStoreSettings) -> None:
        import chromadb

        self.embeddings = embeddings
        self.settings = settings
        settings.persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(settings.persist_dir))
        logger.info("chroma_initialized", persist_dir=str(settings.persist_dir))

    def _get_store(self, tenant_id: str) -> Chroma:
        name = self.get_collection_name(tenant_id)
        return Chroma(
            client=self._client,
            collection_name=name,
            embedding_function=self.embeddings,
        )

    def add_documents(self, documents: list[Document], tenant_id: str) -> list[str]:
        ids: list[str] = self._get_store(tenant_id).add_documents(documents)
        logger.info("documents_added", tenant=tenant_id, count=len(ids))
        return ids

    def similarity_search(
        self,
        query: str,
        tenant_id: str,
        k: int = 4,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[Document]:
        return self._get_store(tenant_id).similarity_search(  # type: ignore[no-any-return]
            query, k=k, filter=metadata_filter
        )

    def similarity_search_with_score(
        self,
        query: str,
        tenant_id: str,
        k: int = 4,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[tuple[Document, float]]:
        return self._get_store(tenant_id).similarity_search_with_score(  # type: ignore[no-any-return]
            query, k=k, filter=metadata_filter
        )

    def delete(self, ids: list[str], tenant_id: str) -> None:
        self._get_store(tenant_id).delete(ids)
        logger.info("documents_deleted", tenant=tenant_id, count=len(ids))

    def get_collection_name(self, tenant_id: str) -> str:
        return collection_name(tenant_id, self.settings.collection_prefix)

    def collection_exists(self, tenant_id: str) -> bool:
        name = self.get_collection_name(tenant_id)
        return any(c.name == name for c in self._client.list_collections())

    def delete_collection(self, tenant_id: str) -> None:
        name = self.get_collection_name(tenant_id)
        self._client.delete_collection(name)
        logger.info("collection_deleted", tenant=tenant_id, collection=name)
