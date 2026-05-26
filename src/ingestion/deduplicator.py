from __future__ import annotations

import hashlib
import json
from pathlib import Path

import structlog
from langchain_core.documents import Document

logger = structlog.get_logger(__name__)


class Deduplicator:
    """Hash-based document deduplication — skips content already indexed."""

    def __init__(self, store_path: Path) -> None:
        self.store_path = store_path
        # {sha256_hex: source_path}
        self._hashes: dict[str, str] = self._load()

    def filter_new(self, documents: list[Document]) -> list[Document]:
        """Return only documents whose content hasn't been indexed yet."""
        new_docs: list[Document] = []
        duplicates = 0

        for doc in documents:
            h = self._hash(doc)
            if h not in self._hashes:
                doc.metadata["content_hash"] = h
                new_docs.append(doc)
            else:
                duplicates += 1
                logger.debug(
                    "duplicate_skipped",
                    source=doc.metadata.get("source"),
                    hash=h[:8],
                )

        logger.info("deduplication_done", new=len(new_docs), duplicates=duplicates)
        return new_docs

    def mark_indexed(self, documents: list[Document]) -> None:
        """Persist hashes of successfully indexed documents."""
        for doc in documents:
            h = doc.metadata.get("content_hash") or self._hash(doc)
            self._hashes[h] = doc.metadata.get("source", "unknown")
        self._save()

    def is_known(self, doc: Document) -> bool:
        return self._hash(doc) in self._hashes

    @staticmethod
    def _hash(doc: Document) -> str:
        return hashlib.sha256(doc.page_content.encode("utf-8")).hexdigest()

    def _load(self) -> dict[str, str]:
        if self.store_path.exists():
            return json.loads(self.store_path.read_text())  # type: ignore[no-any-return]
        return {}

    def _save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        self.store_path.write_text(json.dumps(self._hashes, indent=2))
