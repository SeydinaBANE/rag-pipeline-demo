from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import structlog
from langchain_core.documents import Document

logger = structlog.get_logger(__name__)


class DocumentVersioner:
    """
    Track document versions to support upsert strategy.

    When a document changes, returns the old chunk IDs to delete and the
    new document content to re-index. Prevents stale chunks from persisting.
    """

    def __init__(self, store_path: Path) -> None:
        self.store_path = store_path
        # {source_path: {"hash": str, "chunk_ids": list[str]}}
        self._versions: dict[str, dict[str, Any]] = self._load()

    def get_changed(self, documents: list[Document]) -> tuple[list[Document], list[str]]:
        """
        Returns (new_or_changed_docs, chunk_ids_to_delete).

        Groups input documents by source path and compares against stored versions.
        """
        by_source: dict[str, list[Document]] = {}
        for doc in documents:
            source = doc.metadata.get("source", "unknown")
            by_source.setdefault(source, []).append(doc)

        changed: list[Document] = []
        to_delete: list[str] = []

        for source, docs in by_source.items():
            new_hash = self._hash_docs(docs)
            existing = self._versions.get(source)

            if existing is None:
                logger.info("new_document", source=source)
                changed.extend(docs)
            elif existing["hash"] != new_hash:
                old_ids: list[str] = existing.get("chunk_ids", [])
                to_delete.extend(old_ids)
                logger.info("document_changed", source=source, old_chunks=len(old_ids))
                changed.extend(docs)
            else:
                logger.debug("document_unchanged", source=source)

        return changed, to_delete

    def update(self, source: str, chunk_ids: list[str], docs: list[Document]) -> None:
        """Record new version after successful indexation."""
        self._versions[source] = {
            "hash": self._hash_docs(docs),
            "chunk_ids": chunk_ids,
        }
        self._save()

    def remove(self, source: str) -> None:
        """Remove a document from version tracking (e.g. after deletion)."""
        self._versions.pop(source, None)
        self._save()

    @staticmethod
    def _hash_docs(docs: list[Document]) -> str:
        combined = "".join(d.page_content for d in docs)
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def _load(self) -> dict[str, dict[str, Any]]:
        if self.store_path.exists():
            return json.loads(self.store_path.read_text())  # type: ignore[no-any-return]
        return {}

    def _save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(json.dumps(self._versions, indent=2))
