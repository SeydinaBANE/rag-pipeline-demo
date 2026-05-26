from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from src.api.middleware.auth import get_current_user
from src.api.middleware.rate_limit import SlidingWindowRateLimiter
from src.api.schemas import TokenData
from src.config import get_settings
from src.generation.chain import RAGChain

CurrentUser = Annotated[TokenData, Depends(get_current_user)]


@lru_cache(maxsize=1)
def get_rate_limiter() -> SlidingWindowRateLimiter:
    return SlidingWindowRateLimiter(get_settings().api.rate_limit_per_minute)


@lru_cache(maxsize=1)
def get_rag_chain() -> RAGChain:
    """Build the full RAG chain from settings. Override in tests via dependency_overrides."""
    from langchain_ollama import ChatOllama

    from src.embedding.ollama import OllamaEmbedder
    from src.retrieval.hybrid import HybridRetriever
    from src.vectorstore.chroma import ChromaVectorStore

    s = get_settings()
    llm = ChatOllama(
        model=s.llm.model,
        base_url=s.llm.base_url,
        temperature=s.llm.temperature,
    )
    embedder = OllamaEmbedder(s.embedding)
    vectorstore = ChromaVectorStore(embedder, s.vectorstore)
    retriever = HybridRetriever(vectorstore, s.retrieval)
    return RAGChain(
        llm=llm,
        retriever=retriever,
        prompt_version=s.generation.prompt_version,
        max_context_docs=s.generation.max_context_docs,
        min_input_length=s.generation.min_input_length,
        max_input_length=s.generation.max_input_length,
    )


RateLimiter = Annotated[SlidingWindowRateLimiter, Depends(get_rate_limiter)]
Chain = Annotated[RAGChain, Depends(get_rag_chain)]
