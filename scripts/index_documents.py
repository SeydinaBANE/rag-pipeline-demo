#!/usr/bin/env python3
"""CLI — index documents from data/docs/ into the vector store."""

from __future__ import annotations

import argparse
import sys
from itertools import groupby
from pathlib import Path

import structlog

# Ensure project root is on PYTHONPATH when run as a script
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.chunking.fixed import FixedChunker
from src.chunking.parent_child import ParentChildChunker
from src.config import ChunkingStrategy, get_settings
from src.embedding.batch import BatchEmbedder
from src.embedding.ollama import OllamaEmbedder
from src.ingestion.deduplicator import Deduplicator
from src.ingestion.loaders import DocumentLoader
from src.ingestion.pii_filter import PIIFilter
from src.ingestion.versioning import DocumentVersioner
from src.vectorstore.chroma import ChromaVectorStore

logger = structlog.get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Index documents from a directory into the RAG vector store"
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("data/docs"),
        help="Directory containing documents to index (default: data/docs)",
    )
    parser.add_argument(
        "--tenant",
        default="default",
        help="Tenant ID for namespace isolation (default: 'default')",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete the tenant's collection before indexing",
    )
    parser.add_argument(
        "--no-pii-filter",
        action="store_true",
        help="Skip PII detection and anonymization",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=Path(".cache"),
        help="Directory for dedup/version cache files (default: .cache)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()

    logger.info(
        "indexing_started",
        docs_dir=str(args.docs_dir),
        tenant=args.tenant,
        strategy=settings.chunking.strategy,
    )

    loader = DocumentLoader()
    deduplicator = Deduplicator(store_path=args.cache_dir / "hashes.json")
    versioner = DocumentVersioner(store_path=args.cache_dir / "versions.json")
    pii_filter = PIIFilter(enabled=not args.no_pii_filter)
    embedder = OllamaEmbedder(settings.embedding)
    batch_embedder = BatchEmbedder(embedder, batch_size=settings.embedding.batch_size)
    vectorstore = ChromaVectorStore(embedder, settings.vectorstore)

    if settings.chunking.strategy == ChunkingStrategy.PARENT_CHILD:
        chunker: ParentChildChunker | FixedChunker = ParentChildChunker(settings.chunking)
    else:
        chunker = FixedChunker(settings.chunking)

    # Optional reset
    if args.reset and vectorstore.collection_exists(args.tenant):
        vectorstore.delete_collection(args.tenant)
        logger.info("collection_reset", tenant=args.tenant)

    # Load
    docs = loader.load_directory(args.docs_dir)
    if not docs:
        logger.warning("no_documents_found", directory=str(args.docs_dir))
        return

    # Versioning — detect new/changed docs, get obsolete chunk IDs
    changed_docs, ids_to_delete = versioner.get_changed(docs)
    if not changed_docs:
        logger.info("all_documents_up_to_date")
        return

    if ids_to_delete:
        vectorstore.delete(ids_to_delete, args.tenant)
        logger.info("obsolete_chunks_deleted", count=len(ids_to_delete))

    # Dedup
    new_docs = deduplicator.filter_new(changed_docs)
    if not new_docs:
        logger.info("no_new_documents_after_dedup")
        return

    # PII filter
    clean_docs = pii_filter.anonymize(new_docs)

    # Chunk
    chunks = chunker.split(clean_docs)

    # Index — use batch embedder implicitly via vectorstore (Chroma calls embedder)
    _ = batch_embedder  # used for explicit batch calls if needed
    ids = vectorstore.add_documents(chunks, args.tenant)

    # Update version tracking per source document
    for source, group in groupby(
        sorted(clean_docs, key=lambda d: d.metadata.get("source", "")),
        key=lambda d: d.metadata.get("source", "unknown"),
    ):
        versioner.update(str(source), ids, list(group))

    deduplicator.mark_indexed(new_docs)

    logger.info(
        "indexing_complete",
        tenant=args.tenant,
        documents=len(new_docs),
        chunks=len(chunks),
        vector_ids=len(ids),
    )


if __name__ == "__main__":
    main()
