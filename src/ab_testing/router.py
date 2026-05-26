from __future__ import annotations

import hashlib
import random
from collections import Counter
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class Variant:
    name: str
    weight: float  # fraction of traffic; all variant weights must sum to 1.0
    config: dict[str, Any] = field(default_factory=dict)


@dataclass
class ABExperiment:
    name: str
    variants: list[Variant]

    def __post_init__(self) -> None:
        total = sum(v.weight for v in self.variants)
        if not (0.999 < total < 1.001):
            raise ValueError(f"Variant weights must sum to 1.0, got {total:.4f} for '{self.name}'")

    def select_variant(self, user_id: str | None = None) -> Variant:
        """Sticky selection by user_id hash; random otherwise."""
        if user_id is not None:
            return _hash_select(self.variants, user_id)
        r = random.random()  # noqa: S311  # nosec B311
        cumulative = 0.0
        for variant in self.variants:
            cumulative += variant.weight
            if r < cumulative:
                return variant
        return self.variants[-1]


class ABRouter:
    """Thread-safe router for A/B experiments with impression/conversion tracking."""

    def __init__(self) -> None:
        self._experiments: dict[str, ABExperiment] = {}
        self._impressions: dict[str, Counter[str]] = {}
        self._conversions: dict[str, Counter[str]] = {}
        self._lock = Lock()

    def register(self, experiment: ABExperiment) -> None:
        with self._lock:
            self._experiments[experiment.name] = experiment
            self._impressions[experiment.name] = Counter()
            self._conversions[experiment.name] = Counter()
        logger.info(
            "ab_experiment_registered",
            name=experiment.name,
            variants=[v.name for v in experiment.variants],
        )

    def select(self, experiment_name: str, user_id: str | None = None) -> Variant:
        with self._lock:
            experiment = self._experiments[experiment_name]
        variant = experiment.select_variant(user_id)
        with self._lock:
            self._impressions[experiment_name][variant.name] += 1
        return variant

    def record_conversion(self, experiment_name: str, variant_name: str) -> None:
        with self._lock:
            self._conversions[experiment_name][variant_name] += 1

    def stats(self, experiment_name: str) -> dict[str, Any]:
        with self._lock:
            if experiment_name not in self._experiments:
                raise KeyError(f"Experiment not found: {experiment_name!r}")
            impressions = dict(self._impressions[experiment_name])
            conversions = dict(self._conversions[experiment_name])
            variants = list(self._experiments[experiment_name].variants)

        variants_stats: list[dict[str, Any]] = []
        for v in variants:
            n = impressions.get(v.name, 0)
            c = conversions.get(v.name, 0)
            variants_stats.append(
                {
                    "name": v.name,
                    "weight": v.weight,
                    "impressions": n,
                    "conversions": c,
                    "conversion_rate": round(c / n, 4) if n > 0 else 0.0,
                }
            )
        return {"experiment": experiment_name, "variants": variants_stats}


def _hash_select(variants: list[Variant], user_id: str) -> Variant:
    """Deterministic variant selection via SHA-256 hash (sticky sessions)."""
    digest = hashlib.sha256(user_id.encode()).hexdigest()
    normalized = (int(digest, 16) % 10000) / 10000.0
    cumulative = 0.0
    for variant in variants:
        cumulative += variant.weight
        if normalized < cumulative:
            return variant
    return variants[-1]
