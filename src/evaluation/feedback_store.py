from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class FeedbackEntry:
    query: str
    answer: str
    rating: int  # 1 = positive, -1 = negative
    tenant_id: str
    comment: str | None = None
    timestamp: float = field(default_factory=time.time)


class FeedbackStore:
    """Append-only JSONL store for user feedback, partitioned by tenant."""

    def __init__(self, store_dir: Path) -> None:
        self._dir = store_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, tenant_id: str) -> Path:
        return self._dir / f"{tenant_id}.jsonl"

    def append(self, entry: FeedbackEntry) -> None:
        path = self._path(entry.tenant_id)
        with open(path, "a") as f:
            f.write(json.dumps(asdict(entry)) + "\n")
        logger.debug("feedback_stored", tenant=entry.tenant_id, rating=entry.rating)

    def load(self, tenant_id: str | None = None) -> list[FeedbackEntry]:
        if tenant_id is not None:
            paths: list[Path] = [self._path(tenant_id)]
        else:
            paths = sorted(self._dir.glob("*.jsonl"))

        entries: list[FeedbackEntry] = []
        for path in paths:
            if not path.exists():
                continue
            with open(path) as f:
                for raw in f:
                    stripped = raw.strip()
                    if not stripped:
                        continue
                    data: dict[str, Any] = json.loads(stripped)
                    entries.append(
                        FeedbackEntry(
                            query=data["query"],
                            answer=data["answer"],
                            rating=int(data["rating"]),
                            tenant_id=data["tenant_id"],
                            comment=data.get("comment"),
                            timestamp=float(data.get("timestamp", time.time())),
                        )
                    )
        return entries

    def stats(self, tenant_id: str | None = None) -> dict[str, Any]:
        entries = self.load(tenant_id)
        total = len(entries)
        positive = sum(1 for e in entries if e.rating == 1)
        negative = total - positive
        return {
            "total": total,
            "positive": positive,
            "negative": negative,
            "positive_rate": round(positive / total, 3) if total > 0 else 0.0,
        }
