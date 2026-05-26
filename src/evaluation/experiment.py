from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class ExperimentResult:
    experiment_id: str
    name: str
    config: dict[str, Any]
    metrics: dict[str, float]
    sample_size: int
    timestamp: float


class ExperimentTracker:
    """Persist and compare RAGAS experiment results as JSON files."""

    def __init__(self, experiments_dir: Path) -> None:
        self._dir = experiments_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def save(self, result: ExperimentResult) -> None:
        path = self._dir / f"{result.experiment_id}.json"
        with open(path, "w") as f:
            json.dump(asdict(result), f, indent=2)
        logger.info("experiment_saved", id=result.experiment_id, name=result.name)

    def load_all(self) -> list[ExperimentResult]:
        results: list[ExperimentResult] = []
        for path in sorted(self._dir.glob("*.json")):
            with open(path) as f:
                data: dict[str, Any] = json.load(f)
            results.append(
                ExperimentResult(
                    experiment_id=str(data["experiment_id"]),
                    name=str(data["name"]),
                    config=dict(data["config"]),
                    metrics={k: float(v) for k, v in data["metrics"].items()},
                    sample_size=int(data["sample_size"]),
                    timestamp=float(data["timestamp"]),
                )
            )
        return results

    def compare(self, exp1_id: str, exp2_id: str) -> dict[str, Any]:
        by_id = {r.experiment_id: r for r in self.load_all()}
        if exp1_id not in by_id:
            raise KeyError(f"Experiment not found: {exp1_id}")
        if exp2_id not in by_id:
            raise KeyError(f"Experiment not found: {exp2_id}")
        e1, e2 = by_id[exp1_id], by_id[exp2_id]
        all_metrics = sorted(set(e1.metrics) | set(e2.metrics))
        diff = {
            m: {
                "exp1": e1.metrics.get(m, 0.0),
                "exp2": e2.metrics.get(m, 0.0),
                "delta": round(e2.metrics.get(m, 0.0) - e1.metrics.get(m, 0.0), 4),
            }
            for m in all_metrics
        }
        return {"exp1": e1.name, "exp2": e2.name, "metrics": diff}

    def best(self, metric: str) -> ExperimentResult | None:
        results = self.load_all()
        if not results:
            return None
        return max(results, key=lambda r: r.metrics.get(metric, 0.0))
