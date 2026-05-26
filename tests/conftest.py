from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from langchain_core.documents import Document


@pytest.fixture
def sample_docs() -> list[Document]:
    return [
        Document(
            page_content="LangChain is a framework for building LLM-powered applications.",
            metadata={"source": "langchain.txt", "filename": "langchain.txt", "file_type": "txt"},
        ),
        Document(
            page_content="RAG combines retrieval with generation for factual responses.",
            metadata={"source": "rag.txt", "filename": "rag.txt", "file_type": "txt"},
        ),
        Document(
            page_content="Vector databases store embeddings for semantic similarity search.",
            metadata={"source": "vectors.txt", "filename": "vectors.txt", "file_type": "txt"},
        ),
    ]


@pytest.fixture
def long_doc() -> Document:
    """A document long enough to produce multiple chunks."""
    paragraphs = [
        "LangChain provides abstractions for chains, agents, and memory.",
        "Retrieval-Augmented Generation (RAG) improves LLM factuality.",
        "Chunking splits documents into smaller pieces for indexing.",
        "Embeddings represent text as dense vectors in high-dimensional space.",
        "Similarity search finds the most relevant chunks for a given query.",
        "Reranking re-orders retrieved chunks by relevance before sending to LLM.",
        "Parent-child chunking uses small chunks for retrieval, large for generation.",
        "Hybrid search combines BM25 sparse retrieval with dense vector search.",
        "RAGAS provides automated evaluation metrics for RAG pipelines.",
        "LangGraph enables building stateful multi-agent workflows.",
    ]
    return Document(
        page_content="\n\n".join(paragraphs),
        metadata={"source": "long_doc.txt", "filename": "long_doc.txt", "file_type": "txt"},
    )


@pytest.fixture
def mock_embedder() -> MagicMock:
    """Mock embedder that returns deterministic 768-dim vectors."""
    embedder = MagicMock()
    vector = [0.1] * 768
    embedder.embed_documents.return_value = [vector]
    embedder.embed_query.return_value = vector
    return embedder


@pytest.fixture
def tmp_cache(tmp_path: Path) -> Path:
    cache = tmp_path / ".cache"
    cache.mkdir()
    return cache


@pytest.fixture
def sample_txt_file(tmp_path: Path) -> Path:
    f = tmp_path / "sample.txt"
    f.write_text("This is a test document.\nIt has two lines.")
    return f


@pytest.fixture
def sample_md_file(tmp_path: Path) -> Path:
    f = tmp_path / "sample.md"
    f.write_text("# Title\n\nThis is a markdown document.\n\n## Section\n\nContent here.")
    return f
