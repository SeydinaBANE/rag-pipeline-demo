from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import structlog
from langchain_core.documents import Document

logger = structlog.get_logger(__name__)


@dataclass
class CachedEntry:
    query: str
    answer: str
    sources: list[dict[str, Any]]
    created_at: float

    @classmethod
    def from_result(
        cls,
        query: str,
        answer: str,
        source_docs: list[Document],
    ) -> CachedEntry:
        return cls(
            query=query,
            answer=answer,
            sources=[
                {"content": d.page_content[:300], "metadata": d.metadata} for d in source_docs
            ],
            created_at=time.time(),
        )

    def to_documents(self) -> list[Document]:
        return [Document(page_content=s["content"], metadata=s["metadata"]) for s in self.sources]


class SemanticCache:
    """
    Redis-backed semantic cache for RAG queries.

    Caches (query, answer, sources) tuples indexed by query embeddings.
    On lookup, computes cosine similarity between the incoming query embedding
    and all cached embeddings for the tenant. Returns a hit if similarity
    exceeds the configured threshold.

    Redis key layout:
      cache:{tenant_id}:embeddings  — Hash { entry_id → embedding bytes (float32) }
      cache:{tenant_id}:entries     — Hash { entry_id → JSON entry data }
    """

    def __init__(
        self,
        redis_client: Any,  # noqa: ANN401
        embedder: Any,  # noqa: ANN401
        ttl: int = 3600,
        similarity_threshold: float = 0.95,
    ) -> None:
        self._redis = redis_client
        self._embedder = embedder
        self._ttl = ttl
        self._threshold = similarity_threshold

    def get(self, query: str, tenant_id: str) -> CachedEntry | None:
        emb_key = f"cache:{tenant_id}:embeddings"
        entry_key = f"cache:{tenant_id}:entries"

        raw_embeddings: dict[bytes, bytes] = self._redis.hgetall(emb_key)
        if not raw_embeddings:
            return None

        query_vec = np.array(self._embedder.embed_query(query), dtype=np.float32)

        best_score = 0.0
        best_entry_id: str | None = None

        for entry_id_bytes, emb_bytes in raw_embeddings.items():
            cached_vec = np.frombuffer(emb_bytes, dtype=np.float32)
            score = float(_cosine_similarity(query_vec, cached_vec))
            if score > best_score:
                best_score = score
                best_entry_id = entry_id_bytes.decode()

        if best_score < self._threshold or best_entry_id is None:
            logger.debug("cache_miss", tenant=tenant_id, best_score=round(best_score, 4))
            return None

        raw_entry = self._redis.hget(entry_key, best_entry_id)
        if raw_entry is None:
            return None

        logger.info("cache_hit", tenant=tenant_id, score=round(best_score, 4))
        data: dict[str, Any] = json.loads(raw_entry)
        return CachedEntry(**data)

    def set(
        self,
        query: str,
        answer: str,
        source_docs: list[Document],
        tenant_id: str,
    ) -> None:
        entry = CachedEntry.from_result(query, answer, source_docs)
        entry_id = _entry_id(query, tenant_id)

        emb_key = f"cache:{tenant_id}:embeddings"
        entry_key = f"cache:{tenant_id}:entries"

        query_vec = np.array(self._embedder.embed_query(query), dtype=np.float32)

        pipe = self._redis.pipeline()
        pipe.hset(emb_key, entry_id, query_vec.tobytes())
        pipe.hset(entry_key, entry_id, json.dumps(asdict(entry)))
        pipe.expire(emb_key, self._ttl)
        pipe.expire(entry_key, self._ttl)
        pipe.execute()

        logger.debug("cache_set", tenant=tenant_id, entry_id=entry_id[:8])

    def invalidate(self, tenant_id: str) -> None:
        """Clear all cached entries for a tenant."""
        self._redis.delete(
            f"cache:{tenant_id}:embeddings",
            f"cache:{tenant_id}:entries",
        )
        logger.info("cache_invalidated", tenant=tenant_id)

    def stats(self, tenant_id: str) -> dict[str, object]:
        count = self._redis.hlen(f"cache:{tenant_id}:entries")
        return {"tenant": tenant_id, "cached_entries": int(count)}


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> np.floating[Any]:
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return np.float32(0.0)
    return np.dot(a, b) / (norm_a * norm_b)


def _entry_id(query: str, tenant_id: str) -> str:
    return hashlib.sha256(f"{tenant_id}:{query}".encode()).hexdigest()[:16]
