from __future__ import annotations

from abc import ABC, abstractmethod

from langchain_core.embeddings import Embeddings


class BaseEmbedder(Embeddings, ABC):  # type: ignore[misc]
    """Abstract interface for embedding models — extends LangChain's Embeddings."""

    @abstractmethod
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]: ...
