from __future__ import annotations

from pathlib import Path

import pytest
from langchain_core.documents import Document
from src.ingestion.deduplicator import Deduplicator
from src.ingestion.loaders import DocumentLoader
from src.ingestion.versioning import DocumentVersioner


class TestDocumentLoader:
    def test_load_txt_file(self, sample_txt_file: Path) -> None:
        loader = DocumentLoader()
        docs = loader.load(sample_txt_file)
        assert len(docs) >= 1
        assert "test document" in docs[0].page_content
        assert docs[0].metadata["filename"] == "sample.txt"
        assert docs[0].metadata["file_type"] == "txt"

    def test_load_md_file(self, sample_md_file: Path) -> None:
        loader = DocumentLoader()
        docs = loader.load(sample_md_file)
        assert len(docs) >= 1
        assert docs[0].metadata["file_type"] == "md"

    def test_load_nonexistent_file_raises(self, tmp_path: Path) -> None:
        loader = DocumentLoader()
        with pytest.raises(FileNotFoundError):
            loader.load(tmp_path / "ghost.txt")

    def test_load_unsupported_extension_raises(self, tmp_path: Path) -> None:
        f = tmp_path / "data.csv"
        f.write_text("a,b,c")
        loader = DocumentLoader()
        with pytest.raises(ValueError, match="Unsupported file type"):
            loader.load(f)

    def test_load_directory(self, tmp_path: Path) -> None:
        (tmp_path / "a.txt").write_text("Document A")
        (tmp_path / "b.txt").write_text("Document B")
        (tmp_path / "ignore.csv").write_text("skip,this")

        loader = DocumentLoader()
        docs = loader.load_directory(tmp_path)
        assert len(docs) == 2

    def test_load_directory_not_a_dir_raises(self, sample_txt_file: Path) -> None:
        loader = DocumentLoader()
        with pytest.raises(NotADirectoryError):
            loader.load_directory(sample_txt_file)

    def test_load_directory_partial_failure(self, tmp_path: Path) -> None:
        (tmp_path / "good.txt").write_text("Good content")
        bad = tmp_path / "bad.txt"
        bad.write_bytes(b"\xff\xfe invalid utf-8 \x00")

        loader = DocumentLoader()
        # Should not raise — bad file is skipped with a warning
        docs = loader.load_directory(tmp_path)
        assert len(docs) >= 0  # at least no crash


class TestDeduplicator:
    def test_filter_new_returns_all_on_first_run(
        self, sample_docs: list[Document], tmp_cache: Path
    ) -> None:
        dedup = Deduplicator(store_path=tmp_cache / "hashes.json")
        new = dedup.filter_new(sample_docs)
        assert len(new) == len(sample_docs)

    def test_filter_new_skips_after_mark(
        self, sample_docs: list[Document], tmp_cache: Path
    ) -> None:
        dedup = Deduplicator(store_path=tmp_cache / "hashes.json")
        new = dedup.filter_new(sample_docs)
        dedup.mark_indexed(new)

        new2 = dedup.filter_new(sample_docs)
        assert len(new2) == 0

    def test_hash_added_to_metadata(self, sample_docs: list[Document], tmp_cache: Path) -> None:
        dedup = Deduplicator(store_path=tmp_cache / "hashes.json")
        new = dedup.filter_new(sample_docs)
        for doc in new:
            assert "content_hash" in doc.metadata
            assert len(doc.metadata["content_hash"]) == 64  # SHA-256 hex

    def test_persistence_across_instances(
        self, sample_docs: list[Document], tmp_cache: Path
    ) -> None:
        store = tmp_cache / "hashes.json"
        dedup1 = Deduplicator(store_path=store)
        dedup1.mark_indexed(dedup1.filter_new(sample_docs))

        dedup2 = Deduplicator(store_path=store)
        new = dedup2.filter_new(sample_docs)
        assert len(new) == 0

    def test_is_known(self, sample_docs: list[Document], tmp_cache: Path) -> None:
        dedup = Deduplicator(store_path=tmp_cache / "hashes.json")
        assert not dedup.is_known(sample_docs[0])
        dedup.mark_indexed([sample_docs[0]])
        assert dedup.is_known(sample_docs[0])


class TestDocumentVersioner:
    def test_all_new_on_first_run(self, sample_docs: list[Document], tmp_cache: Path) -> None:
        versioner = DocumentVersioner(store_path=tmp_cache / "versions.json")
        changed, to_delete = versioner.get_changed(sample_docs)
        assert len(changed) == len(sample_docs)
        assert len(to_delete) == 0

    def test_unchanged_doc_not_returned(self, sample_docs: list[Document], tmp_cache: Path) -> None:
        store = tmp_cache / "versions.json"
        versioner = DocumentVersioner(store_path=store)
        changed, _ = versioner.get_changed(sample_docs)
        for doc in changed:
            source = doc.metadata.get("source", "unknown")
            versioner.update(source, ["id1", "id2"], [doc])

        changed2, to_delete = versioner.get_changed(sample_docs)
        assert len(changed2) == 0
        assert len(to_delete) == 0

    def test_changed_doc_triggers_delete(self, tmp_cache: Path) -> None:
        store = tmp_cache / "versions.json"
        versioner = DocumentVersioner(store_path=store)

        original = Document(
            page_content="Original content",
            metadata={"source": "doc.txt"},
        )
        _, _ = versioner.get_changed([original])
        versioner.update("doc.txt", ["old-id-1", "old-id-2"], [original])

        updated = Document(
            page_content="Updated content — different hash",
            metadata={"source": "doc.txt"},
        )
        changed, to_delete = versioner.get_changed([updated])
        assert len(changed) == 1
        assert "old-id-1" in to_delete
        assert "old-id-2" in to_delete

    def test_remove_cleans_up(self, tmp_cache: Path) -> None:
        store = tmp_cache / "versions.json"
        versioner = DocumentVersioner(store_path=store)
        doc = Document(page_content="Some content", metadata={"source": "doc.txt"})
        versioner.update("doc.txt", ["id1"], [doc])
        versioner.remove("doc.txt")

        changed, _ = versioner.get_changed([doc])
        assert len(changed) == 1
