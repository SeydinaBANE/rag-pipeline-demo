from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

import structlog
from langchain_core.documents import Document
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import StrOutputParser

from src.generation.guardrails import InputGuardrail, OutputGuardrail
from src.generation.prompts import get_prompt
from src.retrieval.cache import SemanticCache
from src.retrieval.hybrid import HybridRetriever
from src.retrieval.query_transform import QueryTransformer
from src.retrieval.reranker import Reranker

logger = structlog.get_logger(__name__)

_CONTEXT_SEPARATOR = "\n\n---\n\n"


@dataclass
class RAGResponse:
    query: str
    answer: str
    sources: list[Document]
    cached: bool = False
    prompt_version: str = "v1"
    latency_ms: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


class RAGChain:
    """
    Full RAG pipeline: guardrail → cache → query transform → retrieve → rerank → generate.
    """

    def __init__(
        self,
        llm: BaseLanguageModel,
        retriever: HybridRetriever,
        prompt_version: str = "v1",
        reranker: Reranker | None = None,
        cache: SemanticCache | None = None,
        query_transformer: QueryTransformer | None = None,
        use_hyde: bool = False,
        use_multi_query: bool = False,
        max_context_docs: int = 5,
        min_input_length: int = 3,
        max_input_length: int = 1000,
    ) -> None:
        self._retriever = retriever
        self._prompt_version = prompt_version
        self._reranker = reranker
        self._cache = cache
        self._query_transformer = query_transformer
        self._use_hyde = use_hyde
        self._use_multi_query = use_multi_query
        self._max_context_docs = max_context_docs
        self._input_guard = InputGuardrail(min_input_length, max_input_length)
        self._output_guard = OutputGuardrail()
        self._chain = get_prompt(prompt_version) | llm | StrOutputParser()

    def invoke(self, query: str, tenant_id: str) -> RAGResponse:
        t0 = time.perf_counter()

        guard = self._input_guard.check(query)
        if not guard.passed:
            raise ValueError(f"Input blocked: {guard.reason}")

        if self._cache:
            cached = self._cache.get(query, tenant_id)
            if cached:
                return RAGResponse(
                    query=query,
                    answer=cached.answer,
                    sources=cached.to_documents(),
                    cached=True,
                    prompt_version=self._prompt_version,
                    latency_ms=_elapsed_ms(t0),
                )

        retrieval_query = self._transform_query(query)
        docs = self._retrieve(retrieval_query, query, tenant_id)
        context = _format_context(docs[: self._max_context_docs])
        answer = str(self._chain.invoke({"context": context, "question": query}))

        self._output_guard.check(answer, query)

        if self._cache:
            self._cache.set(query, answer, docs, tenant_id)

        latency = _elapsed_ms(t0)
        logger.info(
            "rag_invoke_done",
            tenant=tenant_id,
            prompt_version=self._prompt_version,
            sources=len(docs),
            latency_ms=round(latency, 1),
        )
        return RAGResponse(
            query=query,
            answer=answer,
            sources=docs,
            prompt_version=self._prompt_version,
            latency_ms=latency,
        )

    def stream(self, query: str, tenant_id: str) -> Iterator[str]:
        """Stream answer tokens. Does not read or write the cache."""
        guard = self._input_guard.check(query)
        if not guard.passed:
            raise ValueError(f"Input blocked: {guard.reason}")

        retrieval_query = self._transform_query(query)
        docs = self._retrieve(retrieval_query, query, tenant_id)
        context = _format_context(docs[: self._max_context_docs])

        for chunk in self._chain.stream({"context": context, "question": query}):
            yield str(chunk)

    def _transform_query(self, query: str) -> str:
        if self._query_transformer and self._use_hyde:
            return self._query_transformer.hyde(query)
        return query

    def _retrieve(
        self, retrieval_query: str, original_query: str, tenant_id: str
    ) -> list[Document]:
        if self._query_transformer and self._use_multi_query:
            queries = self._query_transformer.multi_query(original_query)
            seen: dict[str, Document] = {}
            for q in queries:
                for doc in self._retriever.retrieve(q, tenant_id):
                    key = str(doc.metadata.get("doc_id") or doc.page_content[:120])
                    seen.setdefault(key, doc)
            docs = list(seen.values())
        else:
            docs = self._retriever.retrieve(retrieval_query, tenant_id)

        if self._reranker and docs:
            docs = self._reranker.rerank(original_query, docs)

        return docs


def _format_context(docs: list[Document]) -> str:
    return _CONTEXT_SEPARATOR.join(
        f"[Source: {d.metadata.get('source', 'unknown')}]\n{d.page_content}" for d in docs
    )


def _elapsed_ms(t0: float) -> float:
    return (time.perf_counter() - t0) * 1000
