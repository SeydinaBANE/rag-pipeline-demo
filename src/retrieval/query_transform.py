from __future__ import annotations

import structlog
from langchain_core.language_models import BaseLanguageModel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

logger = structlog.get_logger(__name__)

_HYDE_PROMPT = PromptTemplate.from_template(
    "Write a concise document (2-4 sentences) that would directly answer the following question.\n"
    "Do not mention the question. Only write the answer document.\n\n"
    "Question: {query}\n\n"
    "Document:"
)

_MULTI_QUERY_PROMPT = PromptTemplate.from_template(
    "You are an AI assistant. Generate {n} different phrasings of the following question "
    "to improve document retrieval. Each variation should have "
    "a different perspective or wording.\n"
    "Return only the questions, one per line, without numbering.\n\n"
    "Original question: {query}\n\n"
    "Variations:"
)


class QueryTransformer:
    """
    Query transformation strategies to improve retrieval recall.

    - HyDE: generates a hypothetical answer document, then uses its embedding
      for retrieval — bridges the vocabulary gap between queries and documents.
    - Multi-Query: generates N paraphrases of the query, retrieves for each,
      then deduplicates — improves recall for ambiguous or under-specified queries.
    """

    def __init__(self, llm: BaseLanguageModel) -> None:
        self._llm = llm
        self._hyde_chain = _HYDE_PROMPT | llm | StrOutputParser()
        self._multi_query_chain = _MULTI_QUERY_PROMPT | llm | StrOutputParser()

    def hyde(self, query: str) -> str:
        """Generate a hypothetical document that would answer the query."""
        hypothetical_doc: str = self._hyde_chain.invoke({"query": query})
        logger.debug("hyde_generated", query=query[:60], doc_length=len(hypothetical_doc))
        return hypothetical_doc

    async def ahyde(self, query: str) -> str:
        """Async version of HyDE."""
        hypothetical_doc = await self._hyde_chain.ainvoke({"query": query})
        return str(hypothetical_doc)

    def multi_query(self, query: str, n: int = 3) -> list[str]:
        """
        Generate N paraphrases of the query.
        Always includes the original query as the first element.
        """
        raw = self._multi_query_chain.invoke({"query": query, "n": n})
        variations = [
            line.strip()
            for line in str(raw).strip().splitlines()
            if line.strip() and line.strip() != query
        ][:n]

        queries = [query] + variations
        logger.debug("multi_query_generated", original=query[:60], n_variations=len(variations))
        return queries

    async def amulti_query(self, query: str, n: int = 3) -> list[str]:
        """Async version of multi-query."""
        raw = await self._multi_query_chain.ainvoke({"query": query, "n": n})
        variations = [
            line.strip()
            for line in str(raw).strip().splitlines()
            if line.strip() and line.strip() != query
        ][:n]
        return [query] + variations
