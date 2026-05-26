from __future__ import annotations

import structlog
from langchain_core.documents import Document

from src.embedding.base import BaseEmbedder

logger = structlog.get_logger(__name__)


class BatchEmbedder:
    """
    Wraps a BaseEmbedder to embed in fixed-size batches.

    Prevents OOM and timeout errors when embedding large document sets.
    Typical throughput gain: 8-10x vs one-by-one embedding.
    """

    def __init__(self, embedder: BaseEmbedder, batch_size: int = 32) -> None:
        self.embedder = embedder
        self.batch_size = batch_size

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        results: list[list[float]] = []
        total = len(texts)

        for i in range(0, total, self.batch_size):
            batch = texts[i : i + self.batch_size]
            results.extend(self.embedder.embed_documents(batch))
            logger.debug(
                "batch_embedded",
                progress=f"{min(i + self.batch_size, total)}/{total}",
            )

        return results

    def embed_documents(self, documents: list[Document]) -> list[list[float]]:
        return self.embed_texts([doc.page_content for doc in documents])

    def embed_query(self, text: str) -> list[float]:
        return self.embedder.embed_query(text)
