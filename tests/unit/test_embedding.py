from __future__ import annotations

from unittest.mock import MagicMock, call, patch

from langchain_core.documents import Document
from src.embedding.batch import BatchEmbedder


class TestBatchEmbedder:
    def test_embeds_in_batches(self, mock_embedder: MagicMock) -> None:
        mock_embedder.embed_documents.return_value = [[0.1] * 768] * 3

        batcher = BatchEmbedder(mock_embedder, batch_size=3)
        texts = [f"text {i}" for i in range(7)]
        results = batcher.embed_texts(texts)

        assert len(results) == 7
        # 7 texts / batch_size 3 → 3 calls (3 + 3 + 1)
        assert mock_embedder.embed_documents.call_count == 3

    def test_single_batch_when_texts_fit(self, mock_embedder: MagicMock) -> None:
        mock_embedder.embed_documents.return_value = [[0.1] * 768] * 2

        batcher = BatchEmbedder(mock_embedder, batch_size=10)
        results = batcher.embed_texts(["a", "b"])

        assert mock_embedder.embed_documents.call_count == 1
        assert len(results) == 2

    def test_embed_documents_from_docs(self, mock_embedder: MagicMock) -> None:
        mock_embedder.embed_documents.return_value = [[0.2] * 768] * 2

        batcher = BatchEmbedder(mock_embedder, batch_size=32)
        docs = [
            Document(page_content="First doc", metadata={}),
            Document(page_content="Second doc", metadata={}),
        ]
        results = batcher.embed_documents(docs)

        assert len(results) == 2
        # verify text content was extracted correctly
        called_texts = mock_embedder.embed_documents.call_args[0][0]
        assert called_texts == ["First doc", "Second doc"]

    def test_embed_query_delegates(self, mock_embedder: MagicMock) -> None:
        mock_embedder.embed_query.return_value = [0.5] * 768

        batcher = BatchEmbedder(mock_embedder, batch_size=32)
        result = batcher.embed_query("What is RAG?")

        assert result == [0.5] * 768
        mock_embedder.embed_query.assert_called_once_with("What is RAG?")

    def test_empty_texts_returns_empty(self, mock_embedder: MagicMock) -> None:
        mock_embedder.embed_documents.return_value = []

        batcher = BatchEmbedder(mock_embedder, batch_size=32)
        results = batcher.embed_texts([])

        assert results == []
        mock_embedder.embed_documents.assert_not_called()

    def test_batch_content_correct(self, mock_embedder: MagicMock) -> None:
        """Each batch should contain the right slice of texts."""
        mock_embedder.embed_documents.side_effect = lambda texts: [[0.1] * 3] * len(texts)

        batcher = BatchEmbedder(mock_embedder, batch_size=2)
        texts = ["a", "b", "c", "d", "e"]
        batcher.embed_texts(texts)

        calls = mock_embedder.embed_documents.call_args_list
        assert calls[0] == call(["a", "b"])
        assert calls[1] == call(["c", "d"])
        assert calls[2] == call(["e"])


class TestOllamaEmbedderInit:
    def test_initialization_with_settings(self) -> None:
        from src.config import EmbeddingSettings
        from src.embedding.ollama import OllamaEmbedder

        settings = EmbeddingSettings(
            model="nomic-embed-text",
            base_url="http://localhost:11434",
        )

        with patch("src.embedding.ollama.OllamaEmbeddings") as mock_cls:
            embedder = OllamaEmbedder(settings)
            mock_cls.assert_called_once_with(
                model="nomic-embed-text",
                base_url="http://localhost:11434",
            )
            assert embedder is not None
