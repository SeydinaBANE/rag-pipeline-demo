from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document
from src.analytics.langfuse import LangFuseTracer
from src.analytics.prometheus import RAG_QUERIES, record_query
from src.analytics.tracker import QueryRecord, QueryTracker
from src.generation.chain import RAGResponse

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def tracker(tmp_path: Path) -> QueryTracker:
    return QueryTracker(tmp_path / "analytics")


def _make_response(cached: bool = False, latency_ms: float = 250.0) -> RAGResponse:
    return RAGResponse(
        query="What is RAG?",
        answer="RAG is retrieval-augmented generation.",
        sources=[Document(page_content="context", metadata={"source": "doc.txt"})],
        cached=cached,
        prompt_version="v1",
        latency_ms=latency_ms,
    )


# ── QueryTracker ──────────────────────────────────────────────────────────────


class TestQueryTracker:
    def test_record_and_recent(self, tracker: QueryTracker) -> None:
        record = QueryRecord(
            query="q",
            tenant_id="acme",
            answer_length=42,
            latency_ms=100.0,
            cached=False,
            prompt_version="v1",
            num_sources=2,
        )
        tracker.record(record)
        recent = tracker.recent("acme")
        assert len(recent) == 1
        assert recent[0].query == "q"
        assert recent[0].latency_ms == 100.0

    def test_tenant_isolation(self, tracker: QueryTracker) -> None:
        tracker.record(QueryRecord("q1", "acme", 10, 50.0, False, "v1", 1))
        tracker.record(QueryRecord("q2", "other", 10, 80.0, False, "v1", 1))
        assert len(tracker.recent("acme")) == 1
        assert len(tracker.recent("other")) == 1

    def test_recent_respects_limit(self, tracker: QueryTracker) -> None:
        for i in range(10):
            tracker.record(QueryRecord(f"q{i}", "t1", 5, 10.0 * i, False, "v1", 1))
        assert len(tracker.recent("t1", limit=3)) == 3

    def test_recent_missing_tenant_returns_empty(self, tracker: QueryTracker) -> None:
        assert tracker.recent("ghost") == []

    def test_stats_total(self, tracker: QueryTracker) -> None:
        for i in range(5):
            tracker.record(QueryRecord(f"q{i}", "t1", 5, 100.0, i % 2 == 0, "v1", 1))
        stats = tracker.stats("t1")
        assert stats["total"] == 5

    def test_stats_cache_hit_rate(self, tracker: QueryTracker) -> None:
        for cached in [True, True, False, False, False]:
            tracker.record(QueryRecord("q", "t1", 5, 100.0, cached, "v1", 1))
        stats = tracker.stats("t1")
        assert stats["cache_hit_rate"] == pytest.approx(2 / 5, rel=1e-3)

    def test_stats_avg_latency(self, tracker: QueryTracker) -> None:
        for lat in [100.0, 200.0, 300.0]:
            tracker.record(QueryRecord("q", "t1", 5, lat, False, "v1", 1))
        stats = tracker.stats("t1")
        assert stats["avg_latency_ms"] == pytest.approx(200.0, rel=1e-3)

    def test_stats_empty_returns_zeros(self, tracker: QueryTracker) -> None:
        stats = tracker.stats("nobody")
        assert stats["total"] == 0
        assert stats["cache_hit_rate"] == 0.0
        assert stats["avg_latency_ms"] == 0.0


# ── Prometheus record_query ────────────────────────────────────────────────────


class TestRecordQuery:
    def test_increments_counter(self) -> None:
        before = RAG_QUERIES.labels(
            tenant_id="prom-test", cached="false", prompt_version="v1"
        )._value.get()
        record_query(_make_response(cached=False), tenant_id="prom-test")
        after = RAG_QUERIES.labels(
            tenant_id="prom-test", cached="false", prompt_version="v1"
        )._value.get()
        assert after == before + 1

    def test_observes_latency(self) -> None:
        from prometheus_client import REGISTRY

        before_count = (
            REGISTRY.get_sample_value("rag_query_latency_seconds_count", {"tenant_id": "prom-lat"})
            or 0.0
        )
        record_query(_make_response(latency_ms=500.0), tenant_id="prom-lat")
        after_count = (
            REGISTRY.get_sample_value("rag_query_latency_seconds_count", {"tenant_id": "prom-lat"})
            or 0.0
        )
        assert after_count == before_count + 1

    def test_cached_true_sets_label(self) -> None:
        before = RAG_QUERIES.labels(
            tenant_id="prom-cache", cached="true", prompt_version="v1"
        )._value.get()
        record_query(_make_response(cached=True), tenant_id="prom-cache")
        after = RAG_QUERIES.labels(
            tenant_id="prom-cache", cached="true", prompt_version="v1"
        )._value.get()
        assert after == before + 1


# ── LangFuseTracer ────────────────────────────────────────────────────────────


class TestLangFuseTracer:
    def test_disabled_by_default(self) -> None:
        tracer = LangFuseTracer(enabled=False)
        assert not tracer.enabled

    def test_trace_is_noop_when_disabled(self) -> None:
        tracer = LangFuseTracer(enabled=False)
        tracer.trace("exp-1", _make_response(), "acme")  # must not raise

    def test_enabled_with_mock_langfuse(self) -> None:
        mock_client = MagicMock()
        mock_trace = MagicMock()
        mock_client.trace.return_value = mock_trace

        with patch("langfuse.Langfuse", return_value=mock_client):
            tracer = LangFuseTracer(enabled=True, host="http://lf", secret_key="s", public_key="p")  # noqa: S106

        assert tracer.enabled
        tracer.trace("exp-1", _make_response(), "acme")
        mock_client.trace.assert_called_once()
        mock_trace.generation.assert_called_once()

    def test_init_failure_degrades_gracefully(self) -> None:
        with patch("langfuse.Langfuse", side_effect=RuntimeError("conn refused")):
            tracer = LangFuseTracer(enabled=True, host="http://bad", secret_key="s", public_key="p")  # noqa: S106
        assert not tracer.enabled

    def test_trace_failure_degrades_gracefully(self) -> None:
        mock_client = MagicMock()
        mock_client.trace.side_effect = RuntimeError("timeout")

        with patch("langfuse.Langfuse", return_value=mock_client):
            tracer = LangFuseTracer(enabled=True, host="http://lf", secret_key="s", public_key="p")  # noqa: S106

        tracer.trace("exp-1", _make_response(), "acme")  # must not raise
