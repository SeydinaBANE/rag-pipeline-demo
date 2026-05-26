from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import Lock
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class QueryRecord:
    query: str
    tenant_id: str
    answer_length: int
    latency_ms: float
    cached: bool
    prompt_version: str
    num_sources: int
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


class QueryTracker:
    """JSONL-backed per-tenant query history store."""

    def __init__(self, storage_dir: str | Path = "data/analytics") -> None:
        self._dir = Path(storage_dir)
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    def _path(self, tenant_id: str) -> Path:
        return self._dir / f"{tenant_id}.jsonl"

    def record(self, record: QueryRecord) -> None:
        path = self._path(record.tenant_id)
        with self._lock:
            with path.open("a") as f:
                f.write(json.dumps(asdict(record)) + "\n")
        logger.debug("query_recorded", tenant_id=record.tenant_id, latency_ms=record.latency_ms)

    def recent(self, tenant_id: str, limit: int = 100) -> list[QueryRecord]:
        path = self._path(tenant_id)
        if not path.exists():
            return []
        with self._lock:
            lines = path.read_text().splitlines()
        records = [QueryRecord(**json.loads(line)) for line in lines if line.strip()]
        return records[-limit:]

    def stats(self, tenant_id: str) -> dict[str, Any]:
        records = self.recent(tenant_id, limit=10_000)
        if not records:
            return {"total": 0, "cache_hit_rate": 0.0, "avg_latency_ms": 0.0}
        total = len(records)
        cached = sum(1 for r in records if r.cached)
        avg_latency = sum(r.latency_ms for r in records) / total
        return {
            "total": total,
            "cache_hit_rate": round(cached / total, 4),
            "avg_latency_ms": round(avg_latency, 2),
        }
