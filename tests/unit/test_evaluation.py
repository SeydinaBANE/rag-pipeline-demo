from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document
from src.evaluation.experiment import ExperimentResult, ExperimentTracker
from src.evaluation.feedback_store import FeedbackEntry, FeedbackStore
from src.evaluation.ragas_eval import EvalReport, RAGASEvaluator, _load_jsonl
from src.generation.chain import RAGResponse

# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def golden_dataset(tmp_path: Path) -> Path:
    path = tmp_path / "golden.jsonl"
    samples = [
        {"question": "What is RAG?", "ground_truth": "RAG is retrieval-augmented generation."},
        {"question": "What is BM25?", "ground_truth": "BM25 is a sparse retrieval algorithm."},
        {"question": "What is LangChain?", "ground_truth": "LangChain is a framework for LLMs."},
    ]
    with open(path, "w") as f:
        for s in samples:
            f.write(json.dumps(s) + "\n")
    return path


@pytest.fixture
def mock_chain() -> MagicMock:
    chain = MagicMock()
    chain.invoke.return_value = RAGResponse(
        query="What is RAG?",
        answer="RAG is retrieval-augmented generation.",
        sources=[Document(page_content="RAG combines retrieval.", metadata={"source": "rag.txt"})],
    )
    return chain


@pytest.fixture
def tracker(tmp_path: Path) -> ExperimentTracker:
    return ExperimentTracker(tmp_path / "experiments")


@pytest.fixture
def store(tmp_path: Path) -> FeedbackStore:
    return FeedbackStore(tmp_path / "feedback")


# ── EvalReport ────────────────────────────────────────────────────────────────


class TestEvalReport:
    def test_summary_contains_metrics(self) -> None:
        report = EvalReport(
            experiment_id="abc123",
            metrics={"faithfulness": 0.9, "answer_relevancy": 0.85},
            sample_size=5,
            timestamp=time.time(),
        )
        summary = report.summary()
        assert "abc123" in summary
        assert "faithfulness" in summary
        assert "0.9000" in summary

    def test_summary_shows_sample_size(self) -> None:
        report = EvalReport(experiment_id="xyz", metrics={}, sample_size=42, timestamp=time.time())
        assert "42" in report.summary()


# ── _load_jsonl ───────────────────────────────────────────────────────────────


class TestLoadJsonl:
    def test_loads_all_lines(self, golden_dataset: Path) -> None:
        samples = _load_jsonl(golden_dataset)
        assert len(samples) == 3

    def test_respects_limit(self, golden_dataset: Path) -> None:
        samples = _load_jsonl(golden_dataset, limit=2)
        assert len(samples) == 2

    def test_each_sample_has_question_and_ground_truth(self, golden_dataset: Path) -> None:
        for sample in _load_jsonl(golden_dataset):
            assert "question" in sample
            assert "ground_truth" in sample


# ── RAGASEvaluator ────────────────────────────────────────────────────────────


class TestRAGASEvaluator:
    def test_run_calls_chain_for_each_sample(
        self, mock_chain: MagicMock, golden_dataset: Path
    ) -> None:
        with patch("src.evaluation.ragas_eval._compute_ragas") as mock_compute:
            mock_compute.return_value = {"faithfulness": 0.9, "answer_relevancy": 0.8}
            evaluator = RAGASEvaluator(mock_chain, tenant_id="eval")
            report = evaluator.run(golden_dataset, sample_size=3)

        assert mock_chain.invoke.call_count == 3
        assert report.sample_size == 3

    def test_run_returns_eval_report(self, mock_chain: MagicMock, golden_dataset: Path) -> None:
        with patch("src.evaluation.ragas_eval._compute_ragas") as mock_compute:
            mock_compute.return_value = {"faithfulness": 0.88}
            evaluator = RAGASEvaluator(mock_chain)
            report = evaluator.run(golden_dataset, sample_size=1)

        assert isinstance(report, EvalReport)
        assert report.metrics["faithfulness"] == 0.88
        assert len(report.experiment_id) == 8

    def test_run_respects_sample_size(self, mock_chain: MagicMock, golden_dataset: Path) -> None:
        with patch("src.evaluation.ragas_eval._compute_ragas") as mock_compute:
            mock_compute.return_value = {}
            evaluator = RAGASEvaluator(mock_chain)
            report = evaluator.run(golden_dataset, sample_size=2)

        assert report.sample_size == 2
        assert mock_chain.invoke.call_count == 2


# ── ExperimentTracker ─────────────────────────────────────────────────────────


def _make_result(exp_id: str, name: str, metrics: dict[str, float]) -> ExperimentResult:
    return ExperimentResult(
        experiment_id=exp_id,
        name=name,
        config={"prompt_version": "v1"},
        metrics=metrics,
        sample_size=10,
        timestamp=time.time(),
    )


class TestExperimentTracker:
    def test_save_and_load_round_trip(self, tracker: ExperimentTracker) -> None:
        result = _make_result("exp001", "baseline", {"faithfulness": 0.85})
        tracker.save(result)
        loaded = tracker.load_all()
        assert len(loaded) == 1
        assert loaded[0].experiment_id == "exp001"
        assert loaded[0].metrics["faithfulness"] == pytest.approx(0.85)

    def test_load_all_returns_empty_for_new_dir(self, tmp_path: Path) -> None:
        t = ExperimentTracker(tmp_path / "empty")
        assert t.load_all() == []

    def test_compare_shows_delta(self, tracker: ExperimentTracker) -> None:
        tracker.save(_make_result("e1", "v1", {"faithfulness": 0.80}))
        tracker.save(_make_result("e2", "v2", {"faithfulness": 0.90}))
        diff = tracker.compare("e1", "e2")
        assert diff["metrics"]["faithfulness"]["delta"] == pytest.approx(0.10)

    def test_compare_raises_on_missing_experiment(self, tracker: ExperimentTracker) -> None:
        tracker.save(_make_result("real", "real", {}))
        with pytest.raises(KeyError):
            tracker.compare("real", "ghost")

    def test_best_returns_highest_metric(self, tracker: ExperimentTracker) -> None:
        tracker.save(_make_result("e1", "low", {"faithfulness": 0.60}))
        tracker.save(_make_result("e2", "high", {"faithfulness": 0.95}))
        best = tracker.best("faithfulness")
        assert best is not None
        assert best.experiment_id == "e2"

    def test_best_returns_none_when_empty(self, tracker: ExperimentTracker) -> None:
        assert tracker.best("faithfulness") is None


# ── FeedbackStore ─────────────────────────────────────────────────────────────


class TestFeedbackStore:
    def test_append_and_load(self, store: FeedbackStore) -> None:
        entry = FeedbackEntry(
            query="What is RAG?",
            answer="RAG is ...",
            rating=1,
            tenant_id="acme",
        )
        store.append(entry)
        loaded = store.load("acme")
        assert len(loaded) == 1
        assert loaded[0].query == "What is RAG?"
        assert loaded[0].rating == 1

    def test_tenant_isolation(self, store: FeedbackStore) -> None:
        store.append(FeedbackEntry("q", "a", 1, "acme"))
        store.append(FeedbackEntry("q", "a", -1, "other"))
        assert len(store.load("acme")) == 1
        assert len(store.load("other")) == 1

    def test_load_all_tenants(self, store: FeedbackStore) -> None:
        store.append(FeedbackEntry("q1", "a1", 1, "t1"))
        store.append(FeedbackEntry("q2", "a2", -1, "t2"))
        all_entries = store.load()
        assert len(all_entries) == 2

    def test_stats_counts_ratings(self, store: FeedbackStore) -> None:
        store.append(FeedbackEntry("q1", "a1", 1, "acme"))
        store.append(FeedbackEntry("q2", "a2", 1, "acme"))
        store.append(FeedbackEntry("q3", "a3", -1, "acme"))
        stats = store.stats("acme")
        assert stats["total"] == 3
        assert stats["positive"] == 2
        assert stats["negative"] == 1
        assert stats["positive_rate"] == pytest.approx(2 / 3, rel=1e-2)

    def test_stats_empty_returns_zeros(self, store: FeedbackStore) -> None:
        stats = store.stats("nobody")
        assert stats["total"] == 0
        assert stats["positive_rate"] == 0.0

    def test_load_missing_tenant_returns_empty(self, store: FeedbackStore) -> None:
        assert store.load("ghost") == []
