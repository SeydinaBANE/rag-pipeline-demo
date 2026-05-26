from __future__ import annotations

import structlog
from langchain_ollama import OllamaEmbeddings

from src.config import EmbeddingSettings
from src.embedding.base import BaseEmbedder

logger = structlog.get_logger(__name__)


class OllamaEmbedder(BaseEmbedder):
    """Ollama-backed embeddings (nomic-embed-text by default, 768 dimensions)."""

    def __init__(self, settings: EmbeddingSettings) -> None:
        self._model = OllamaEmbeddings(
            model=settings.model,
            base_url=settings.base_url,
        )
        logger.info(
            "embedder_initialized",
            model=settings.model,
            base_url=settings.base_url,
        )

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._model.embed_documents(texts)  # type: ignore[no-any-return]

    def embed_query(self, text: str) -> list[float]:
        return self._model.embed_query(text)  # type: ignore[no-any-return]
