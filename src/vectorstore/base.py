from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from langchain_core.documents import Document


class BaseVectorStore(ABC):
    """Abstract interface for vector store implementations."""

    @abstractmethod
    def add_documents(self, documents: list[Document], tenant_id: str) -> list[str]:
        """Add documents and return their vector IDs."""
        ...

    @abstractmethod
    def similarity_search(
        self,
        query: str,
        tenant_id: str,
        k: int = 4,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[Document]: ...

    @abstractmethod
    def similarity_search_with_score(
        self,
        query: str,
        tenant_id: str,
        k: int = 4,
        metadata_filter: dict[str, Any] | None = None,
    ) -> list[tuple[Document, float]]: ...

    @abstractmethod
    def delete(self, ids: list[str], tenant_id: str) -> None:
        """Delete documents by their vector IDs."""
        ...

    @abstractmethod
    def get_collection_name(self, tenant_id: str) -> str: ...

    @abstractmethod
    def collection_exists(self, tenant_id: str) -> bool: ...

    @abstractmethod
    def delete_collection(self, tenant_id: str) -> None: ...
