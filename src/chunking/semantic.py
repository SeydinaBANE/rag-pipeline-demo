from __future__ import annotations

from typing import cast

import structlog
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_experimental.text_splitter import SemanticChunker

from src.chunking.base import BaseChunker

logger = structlog.get_logger(__name__)


class SemanticSplitter(BaseChunker):
    """
    Semantic chunking — finds natural break points via embedding similarity.

    Unlike fixed-size chunking, boundaries align with topic shifts rather than
    character count, preserving semantic coherence within each chunk.
    """

    def __init__(
        self,
        embeddings: Embeddings,
        breakpoint_percentile: float = 95.0,
    ) -> None:
        self._splitter = SemanticChunker(
            embeddings=embeddings,
            breakpoint_threshold_type="percentile",
            breakpoint_threshold_amount=breakpoint_percentile,
        )

    def split(self, documents: list[Document]) -> list[Document]:
        chunks = cast(list[Document], self._splitter.split_documents(documents))
        logger.info(
            "chunking_done",
            strategy="semantic",
            input_docs=len(documents),
            output_chunks=len(chunks),
        )
        return chunks
