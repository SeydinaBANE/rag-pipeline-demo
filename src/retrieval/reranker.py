from __future__ import annotations

import structlog
from langchain_core.documents import Document
from sentence_transformers import CrossEncoder

logger = structlog.get_logger(__name__)

_DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


class Reranker:
    """
    Cross-encoder reranker using sentence-transformers.

    Takes (query, document) pairs and assigns a relevance score.
    More accurate than bi-encoder cosine similarity but slower —
    used after initial retrieval to reorder a small candidate set.
    """

    def __init__(self, model_name: str = _DEFAULT_MODEL) -> None:
        self._model: CrossEncoder = CrossEncoder(model_name)
        logger.info("reranker_initialized", model=model_name)

    def rerank(
        self,
        query: str,
        documents: list[Document],
        top_k: int | None = None,
    ) -> list[Document]:
        """Reorder documents by cross-encoder score, highest first."""
        if not documents:
            return []

        pairs = [(query, doc.page_content) for doc in documents]
        scores: list[float] = self._model.predict(pairs).tolist()

        ranked = sorted(
            zip(documents, scores, strict=False),
            key=lambda x: x[1],
            reverse=True,
        )

        # Attach reranker score to metadata for observability
        result = []
        for doc, score in ranked[:top_k]:
            doc.metadata["reranker_score"] = round(score, 6)
            result.append(doc)

        logger.info(
            "reranking_done",
            input_docs=len(documents),
            output_docs=len(result),
            top_score=round(scores[0], 4) if scores else None,
        )
        return result

    def score(self, query: str, document: Document) -> float:
        """Score a single (query, document) pair."""
        scores: list[float] = self._model.predict([(query, document.page_content)]).tolist()
        return scores[0]
