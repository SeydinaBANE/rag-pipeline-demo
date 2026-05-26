from __future__ import annotations

from typing import cast

import structlog
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.chunking.base import BaseChunker
from src.config import ChunkingSettings

logger = structlog.get_logger(__name__)


class ParentChildChunker(BaseChunker):
    """
    Parent-child chunking strategy (default).

    Indexes small child chunks for high-precision retrieval, but stores parent
    content in metadata so the LLM receives sufficient context. Empirically
    outperforms fixed chunking on both faithfulness and relevance (see ADR 003).
    """

    def __init__(self, settings: ChunkingSettings) -> None:
        self._parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.parent_chunk_size,
            chunk_overlap=settings.chunk_overlap * 2,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        self._child_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def split(self, documents: list[Document]) -> list[Document]:
        """Return child chunks with parent_content embedded in metadata."""
        children, parents = self.split_with_parents(documents)
        logger.info(
            "chunking_done",
            strategy="parent_child",
            input_docs=len(documents),
            parent_chunks=len(parents),
            child_chunks=len(children),
        )
        return children

    def split_with_parents(
        self, documents: list[Document]
    ) -> tuple[list[Document], list[Document]]:
        """Return (child_chunks, parent_chunks) as separate lists."""
        parent_chunks = cast(list[Document], self._parent_splitter.split_documents(documents))

        all_children: list[Document] = []
        for idx, parent in enumerate(parent_chunks):
            source = parent.metadata.get("source", "doc")
            parent_id = f"{source}::parent::{idx}"
            parent.metadata["doc_id"] = parent_id

            children = cast(list[Document], self._child_splitter.split_documents([parent]))
            for child in children:
                child.metadata["parent_id"] = parent_id
                # Embed parent content so retrieval can return full context
                child.metadata["parent_content"] = parent.page_content

            all_children.extend(children)

        return all_children, parent_chunks
