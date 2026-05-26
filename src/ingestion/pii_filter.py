from __future__ import annotations

import structlog
from langchain_core.documents import Document

logger = structlog.get_logger(__name__)

try:
    from presidio_analyzer import AnalyzerEngine
    from presidio_anonymizer import AnonymizerEngine

    _PRESIDIO_AVAILABLE = True
except ImportError:
    _PRESIDIO_AVAILABLE = False
    logger.warning(
        "presidio_not_available",
        message="PII detection disabled — install presidio-analyzer presidio-anonymizer",
    )

_PII_ENTITIES = [
    "PERSON",
    "EMAIL_ADDRESS",
    "PHONE_NUMBER",
    "IBAN_CODE",
    "CREDIT_CARD",
    "IP_ADDRESS",
    "LOCATION",
]


class PIIFilter:
    """Detect and anonymize PII in documents before indexing."""

    def __init__(self, language: str = "en", enabled: bool = True) -> None:
        self.enabled = enabled and _PRESIDIO_AVAILABLE
        self.language = language

        if self.enabled:
            self._analyzer = AnalyzerEngine()
            self._anonymizer = AnonymizerEngine()
        elif enabled and not _PRESIDIO_AVAILABLE:
            logger.warning("pii_filter_disabled", reason="presidio not installed")

    def anonymize(self, documents: list[Document]) -> list[Document]:
        """Anonymize PII in all documents. No-op if presidio is unavailable."""
        if not self.enabled:
            return documents

        result: list[Document] = []
        total_pii = 0

        for doc in documents:
            clean_doc, pii_count = self._anonymize_doc(doc)
            result.append(clean_doc)
            total_pii += pii_count

        if total_pii:
            logger.info(
                "pii_anonymized",
                total_entities=total_pii,
                documents=len(documents),
            )

        return result

    def scan(self, documents: list[Document]) -> list[dict[str, object]]:
        """Scan without anonymizing — returns a report of detected PII."""
        if not self.enabled:
            return []

        report = []
        for doc in documents:
            results = self._analyzer.analyze(
                text=doc.page_content,
                entities=_PII_ENTITIES,
                language=self.language,
            )
            if results:
                report.append(
                    {
                        "source": doc.metadata.get("source"),
                        "entities": [{"type": r.entity_type, "score": r.score} for r in results],
                    }
                )
        return report

    def _anonymize_doc(self, doc: Document) -> tuple[Document, int]:
        results = self._analyzer.analyze(
            text=doc.page_content,
            entities=_PII_ENTITIES,
            language=self.language,
        )

        if not results:
            return doc, 0

        anonymized = self._anonymizer.anonymize(
            text=doc.page_content,
            analyzer_results=results,
        )

        new_doc = Document(
            page_content=anonymized.text,
            metadata={**doc.metadata, "pii_entities_removed": len(results)},
        )
        return new_doc, len(results)
