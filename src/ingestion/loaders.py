from __future__ import annotations

from pathlib import Path
from typing import cast

import structlog
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document

logger = structlog.get_logger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md"}


class DocumentLoader:
    """Load documents from files or directories."""

    def load(self, path: Path) -> list[Document]:
        if not path.exists():
            raise FileNotFoundError(f"Path does not exist: {path}")

        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {suffix}. Supported: {SUPPORTED_EXTENSIONS}")

        logger.info("loading_document", path=str(path), type=suffix)

        try:
            if suffix == ".pdf":
                loader: PyPDFLoader | TextLoader = PyPDFLoader(str(path))
            else:
                # .txt and .md both work fine with TextLoader
                loader = TextLoader(str(path), encoding="utf-8")

            docs = cast(list[Document], loader.load())

            for doc in docs:
                doc.metadata["source"] = str(path)
                doc.metadata["filename"] = path.name
                doc.metadata["file_type"] = suffix.lstrip(".")

            logger.info("document_loaded", path=str(path), chunks=len(docs))
            return docs

        except Exception as e:
            logger.error("document_load_failed", path=str(path), error=str(e))
            raise

    def load_directory(self, directory: Path, recursive: bool = True) -> list[Document]:
        if not directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory}")

        pattern = "**/*" if recursive else "*"
        files = sorted(
            f
            for f in directory.glob(pattern)
            if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
        )

        logger.info("loading_directory", directory=str(directory), files_found=len(files))

        all_docs: list[Document] = []
        errors: list[str] = []

        for file in files:
            try:
                all_docs.extend(self.load(file))
            except Exception as e:
                errors.append(f"{file}: {e}")
                logger.warning("document_skipped", path=str(file), error=str(e))

        if errors:
            logger.warning("some_documents_failed", count=len(errors))

        logger.info(
            "directory_loaded",
            directory=str(directory),
            total_docs=len(all_docs),
            files_processed=len(files) - len(errors),
            errors=len(errors),
        )
        return all_docs
