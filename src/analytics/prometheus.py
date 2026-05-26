from __future__ import annotations

from prometheus_client import Counter, Histogram

from src.generation.chain import RAGResponse

RAG_QUERIES = Counter(
    "rag_query_total",
    "Total RAG queries processed",
    ["tenant_id", "cached", "prompt_version"],
)

RAG_LATENCY = Histogram(
    "rag_query_latency_seconds",
    "RAG query end-to-end latency",
    ["tenant_id"],
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0],
)

RAG_INGEST_JOBS = Counter(
    "rag_ingest_total",
    "Total document ingestion jobs queued",
    ["tenant_id"],
)


def record_query(response: RAGResponse, tenant_id: str) -> None:
    """Update Prometheus counters/histograms for a completed RAG query."""
    RAG_QUERIES.labels(
        tenant_id=tenant_id,
        cached=str(response.cached).lower(),
        prompt_version=response.prompt_version,
    ).inc()
    RAG_LATENCY.labels(tenant_id=tenant_id).observe(response.latency_ms / 1000)
