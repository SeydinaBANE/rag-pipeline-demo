from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document
from src.chunking.fixed import FixedChunker
from src.chunking.parent_child import ParentChildChunker
from src.chunking.semantic import SemanticSplitter
from src.config import ChunkingSettings


@pytest.fixture
def chunking_settings() -> ChunkingSettings:
    return ChunkingSettings(
        chunk_size=100,
        chunk_overlap=10,
        parent_chunk_size=300,
    )


class TestFixedChunker:
    def test_splits_long_document(
        self, long_doc: Document, chunking_settings: ChunkingSettings
    ) -> None:
        chunker = FixedChunker(chunking_settings)
        chunks = chunker.split([long_doc])
        assert len(chunks) > 1

    def test_chunk_size_respected(
        self, long_doc: Document, chunking_settings: ChunkingSettings
    ) -> None:
        chunker = FixedChunker(chunking_settings)
        chunks = chunker.split([long_doc])
        for chunk in chunks:
            assert len(chunk.page_content) <= chunking_settings.chunk_size * 1.2

    def test_metadata_preserved(
        self, sample_docs: list[Document], chunking_settings: ChunkingSettings
    ) -> None:
        chunker = FixedChunker(chunking_settings)
        chunks = chunker.split(sample_docs)
        sources = {c.metadata.get("source") for c in chunks}
        expected = {d.metadata["source"] for d in sample_docs}
        assert sources == expected

    def test_empty_input_returns_empty(self, chunking_settings: ChunkingSettings) -> None:
        chunker = FixedChunker(chunking_settings)
        assert chunker.split([]) == []

    def test_short_doc_returns_single_chunk(self, chunking_settings: ChunkingSettings) -> None:
        doc = Document(page_content="Short.", metadata={"source": "s.txt"})
        chunker = FixedChunker(chunking_settings)
        chunks = chunker.split([doc])
        assert len(chunks) == 1


class TestParentChildChunker:
    def test_children_have_parent_id(
        self, long_doc: Document, chunking_settings: ChunkingSettings
    ) -> None:
        chunker = ParentChildChunker(chunking_settings)
        children = chunker.split([long_doc])
        for child in children:
            assert "parent_id" in child.metadata

    def test_children_have_parent_content(
        self, long_doc: Document, chunking_settings: ChunkingSettings
    ) -> None:
        chunker = ParentChildChunker(chunking_settings)
        children = chunker.split([long_doc])
        for child in children:
            assert "parent_content" in child.metadata
            assert len(child.metadata["parent_content"]) > len(child.page_content)

    def test_more_children_than_parents(
        self, long_doc: Document, chunking_settings: ChunkingSettings
    ) -> None:
        chunker = ParentChildChunker(chunking_settings)
        children, parents = chunker.split_with_parents([long_doc])
        assert len(children) >= len(parents)

    def test_parent_ids_unique(
        self, long_doc: Document, chunking_settings: ChunkingSettings
    ) -> None:
        chunker = ParentChildChunker(chunking_settings)
        children, parents = chunker.split_with_parents([long_doc])
        parent_ids = [p.metadata["doc_id"] for p in parents]
        assert len(parent_ids) == len(set(parent_ids))

    def test_child_parent_id_matches_parent_doc_id(
        self, long_doc: Document, chunking_settings: ChunkingSettings
    ) -> None:
        chunker = ParentChildChunker(chunking_settings)
        children, parents = chunker.split_with_parents([long_doc])
        valid_parent_ids = {p.metadata["doc_id"] for p in parents}
        for child in children:
            assert child.metadata["parent_id"] in valid_parent_ids


class TestSemanticSplitter:
    def test_split_delegates_to_underlying_chunker(self, long_doc: Document) -> None:
        mock_embedder = MagicMock()
        # SemanticChunker calls embed_documents during split
        mock_embedder.embed_documents.return_value = [[0.1] * 768]

        splitter = SemanticSplitter(embeddings=mock_embedder)
        # We just verify it doesn't raise and returns documents
        # Actual semantic boundary detection requires real embeddings
        chunks = splitter.split([long_doc])
        assert isinstance(chunks, list)
        assert all(isinstance(c, Document) for c in chunks)
