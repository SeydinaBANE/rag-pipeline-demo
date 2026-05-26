from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from langchain_core.documents import Document
from src.api.deps import get_rag_chain, get_rate_limiter
from src.api.main import app
from src.api.middleware.rate_limit import SlidingWindowRateLimiter
from src.generation.chain import RAGResponse

# ── Helpers ───────────────────────────────────────────────────────────────────

_SECRET = "change-me-in-production"  # noqa: S105
_ALGO = "HS256"


def make_token(tenant_id: str = "acme", sub: str = "user-1") -> str:
    return str(jwt.encode({"sub": sub, "tenant_id": tenant_id}, _SECRET, algorithm=_ALGO))


def _fake_rag_response() -> RAGResponse:
    return RAGResponse(
        query="What is RAG?",
        answer="RAG stands for Retrieval-Augmented Generation.",
        sources=[
            Document(
                page_content="RAG combines retrieval and generation.",
                metadata={"source": "rag.txt"},
            )
        ],
    )


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_chain() -> MagicMock:
    chain = MagicMock()
    chain.invoke.return_value = _fake_rag_response()
    chain.stream.side_effect = lambda q, tenant_id: iter(["RAG ", "is ", "great."])
    return chain


@pytest.fixture
def client(mock_chain: MagicMock) -> TestClient:
    app.dependency_overrides[get_rag_chain] = lambda: mock_chain
    app.dependency_overrides[get_rate_limiter] = lambda: SlidingWindowRateLimiter(1000)
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def token() -> str:
    return make_token()


# ── Health ────────────────────────────────────────────────────────────────────


class TestHealthEndpoints:
    def test_health_returns_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    def test_ready_returns_ok(self, client: TestClient) -> None:
        response = client.get("/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


# ── Query ─────────────────────────────────────────────────────────────────────


class TestQueryEndpoint:
    def test_query_returns_answer(self, client: TestClient, token: str) -> None:
        response = client.post(
            "/api/v1/query/",
            json={"query": "What is RAG?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "RAG stands for Retrieval-Augmented Generation."
        assert isinstance(data["sources"], list)
        assert data["cached"] is False

    def test_query_requires_auth(self, client: TestClient) -> None:
        response = client.post("/api/v1/query/", json={"query": "What is RAG?"})
        assert response.status_code == 403

    def test_query_invalid_token(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/query/",
            json={"query": "What is RAG?"},
            headers={"Authorization": "Bearer not.a.valid.token"},
        )
        assert response.status_code == 401

    def test_query_propagates_tenant(self, client: TestClient, mock_chain: MagicMock) -> None:
        token = make_token(tenant_id="tenant-xyz")
        client.post(
            "/api/v1/query/",
            json={"query": "test"},
            headers={"Authorization": f"Bearer {token}"},
        )
        _, kwargs = mock_chain.invoke.call_args
        assert kwargs.get("tenant_id") == "tenant-xyz"

    def test_query_stream_returns_sse(self, client: TestClient, token: str) -> None:
        response = client.post(
            "/api/v1/query/stream",
            json={"query": "What is RAG?"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        assert "data:" in response.text
        assert "[DONE]" in response.text


# ── Ingest ────────────────────────────────────────────────────────────────────


class TestIngestEndpoint:
    def test_ingest_returns_queued(self, client: TestClient, token: str) -> None:
        response = client.post(
            "/api/v1/ingest/",
            files={"file": ("test.txt", b"This is a test document.", "text/plain")},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert "job_id" in data
        assert data["filename"] == "test.txt"

    def test_ingest_requires_auth(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/ingest/",
            files={"file": ("test.txt", b"content", "text/plain")},
        )
        assert response.status_code == 403


# ── Feedback ──────────────────────────────────────────────────────────────────


class TestFeedbackEndpoint:
    def test_feedback_accepted(self, client: TestClient, token: str) -> None:
        response = client.post(
            "/api/v1/feedback/",
            json={"query": "What is RAG?", "answer": "RAG is...", "rating": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "accepted"

    def test_feedback_negative_rating(self, client: TestClient, token: str) -> None:
        response = client.post(
            "/api/v1/feedback/",
            json={"query": "test", "answer": "bad answer", "rating": -1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    def test_feedback_invalid_rating(self, client: TestClient, token: str) -> None:
        response = client.post(
            "/api/v1/feedback/",
            json={"query": "test", "answer": "answer", "rating": 5},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 422

    def test_feedback_requires_auth(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/feedback/",
            json={"query": "test", "answer": "ans", "rating": 1},
        )
        assert response.status_code == 403


# ── RateLimiter ───────────────────────────────────────────────────────────────


class TestSlidingWindowRateLimiter:
    def test_allows_requests_under_limit(self) -> None:
        limiter = SlidingWindowRateLimiter(max_requests=5)
        for _ in range(5):
            limiter.check("tenant-a")  # should not raise

    def test_blocks_after_limit_exceeded(self) -> None:
        from fastapi import HTTPException

        limiter = SlidingWindowRateLimiter(max_requests=3)
        for _ in range(3):
            limiter.check("tenant-b")
        with pytest.raises(HTTPException) as exc_info:
            limiter.check("tenant-b")
        assert exc_info.value.status_code == 429

    def test_tenants_have_independent_limits(self) -> None:
        limiter = SlidingWindowRateLimiter(max_requests=2)
        limiter.check("tenant-a")
        limiter.check("tenant-a")
        # Different tenant should still be allowed
        limiter.check("tenant-b")
