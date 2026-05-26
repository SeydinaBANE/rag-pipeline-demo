from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import structlog

from src.generation.chain import RAGChain

logger = structlog.get_logger(__name__)


@dataclass
class EvalReport:
    experiment_id: str
    metrics: dict[str, float]
    sample_size: int
    timestamp: float
    config: dict[str, Any] = field(default_factory=dict)

    def summary(self) -> str:
        lines = [
            f"Experiment : {self.experiment_id}",
            f"Samples    : {self.sample_size}",
            f"Timestamp  : {self.timestamp:.0f}",
        ]
        for name, value in sorted(self.metrics.items()):
            lines.append(f"  {name:<28} {value:.4f}")
        return "\n".join(lines)


class RAGASEvaluator:
    """Run RAGAS metrics against a golden dataset (JSONL with question/ground_truth fields)."""

    def __init__(
        self,
        chain: RAGChain,
        tenant_id: str = "eval",
        experiment_name: str = "default",
    ) -> None:
        self._chain = chain
        self._tenant_id = tenant_id
        self._experiment_name = experiment_name

    def run(
        self,
        dataset_path: Path,
        sample_size: int | None = None,
    ) -> EvalReport:
        samples = _load_jsonl(dataset_path, sample_size)
        questions: list[str] = []
        answers: list[str] = []
        contexts: list[list[str]] = []
        ground_truths: list[str] = []

        for sample in samples:
            response = self._chain.invoke(sample["question"], tenant_id=self._tenant_id)
            questions.append(sample["question"])
            answers.append(response.answer)
            contexts.append([doc.page_content for doc in response.sources])
            ground_truths.append(sample["ground_truth"])

        metrics = _compute_ragas(questions, answers, contexts, ground_truths)
        report = EvalReport(
            experiment_id=uuid.uuid4().hex[:8],
            metrics=metrics,
            sample_size=len(samples),
            timestamp=time.time(),
            config={"experiment_name": self._experiment_name},
        )
        logger.info(
            "ragas_eval_done",
            experiment_id=report.experiment_id,
            sample_size=report.sample_size,
            metrics=metrics,
        )
        return report


def _load_jsonl(path: Path, limit: int | None = None) -> list[dict[str, str]]:
    samples: list[dict[str, str]] = []
    with open(path) as f:
        for raw in f:
            stripped = raw.strip()
            if not stripped:
                continue
            data: dict[str, str] = json.loads(stripped)
            samples.append(data)
            if limit is not None and len(samples) >= limit:
                break
    return samples


def _compute_ragas(
    questions: list[str],
    answers: list[str],
    contexts: list[list[str]],
    ground_truths: list[str],
) -> dict[str, float]:
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )

    dataset = Dataset.from_dict(
        {
            "question": questions,
            "answer": answers,
            "contexts": contexts,
            "ground_truths": [[gt] for gt in ground_truths],
        }
    )
    result = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )
    return {k: round(float(v), 4) for k, v in dict(result).items()}
