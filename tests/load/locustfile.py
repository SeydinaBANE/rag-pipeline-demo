"""Locust load-test scenarios for the RAG Pipeline API."""

from __future__ import annotations

import os
import random
import time

from jose import jwt
from locust import HttpUser, between, task

_TENANT = os.environ.get("LOAD_TEST_TENANT", "load-test")
_SECRET = os.environ.get("LOAD_TEST_JWT_SECRET", "change-me-in-production")  # noqa: S105
_ALGO = "HS256"

_QUERIES = [
    "What is Retrieval-Augmented Generation?",
    "How does BM25 work?",
    "What is LangChain used for?",
    "Explain hybrid search in RAG systems.",
    "What are the benefits of parent-child chunking?",
    "How does cross-encoder reranking improve retrieval?",
    "What is the role of a vector store in a RAG pipeline?",
    "How do embeddings enable semantic search?",
    "What is the difference between dense and sparse retrieval?",
    "How does reciprocal rank fusion combine retrieval results?",
]


def _make_token(user_id: str) -> str:
    return str(
        jwt.encode(
            {"sub": user_id, "tenant_id": _TENANT, "exp": int(time.time()) + 3600},
            _SECRET,
            algorithm=_ALGO,
        )
    )


class RAGUser(HttpUser):  # type: ignore[misc]
    """Simulates a typical end-user querying the RAG API."""

    wait_time = between(1, 3)

    def on_start(self) -> None:
        self._token = _make_token(f"load-user-{id(self)}")
        self._headers = {"Authorization": f"Bearer {self._token}"}

    @task(8)
    def query(self) -> None:
        payload = {"query": random.choice(_QUERIES)}  # noqa: S311
        with self.client.post(
            "/api/v1/query",
            json=payload,
            headers=self._headers,
            catch_response=True,
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            elif resp.status_code == 429:
                resp.failure(f"Rate limited: {resp.text}")
            else:
                resp.failure(f"Unexpected {resp.status_code}: {resp.text[:200]}")

    @task(2)
    def health_check(self) -> None:
        self.client.get("/health")

    @task(1)
    def metrics(self) -> None:
        self.client.get("/metrics")
