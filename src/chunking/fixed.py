from __future__ import annotations

from typing import cast

import structlog
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.chunking.base import BaseChunker
from src.config import ChunkingSettings

logger = structlog.get_logger(__name__)


class FixedChunker(BaseChunker):
    """Fixed-size chunking with RecursiveCharacterTextSplitter."""

    def __init__(self, settings: ChunkingSettings) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def split(self, documents: list[Document]) -> list[Document]:
        chunks = cast(list[Document], self._splitter.split_documents(documents))
        logger.info(
            "chunking_done",
            strategy="fixed",
            input_docs=len(documents),
            output_chunks=len(chunks),
        )
        return chunks
