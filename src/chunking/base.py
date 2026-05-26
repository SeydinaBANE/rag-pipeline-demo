from __future__ import annotations

from abc import ABC, abstractmethod

from langchain_core.documents import Document


class BaseChunker(ABC):
    """Abstract interface for all chunking strategies."""

    @abstractmethod
    def split(self, documents: list[Document]) -> list[Document]:
        """Split documents into chunks ready for indexing."""
        ...

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"
