from __future__ import annotations

import pytest
from src.ab_testing.router import ABExperiment, ABRouter, Variant, _hash_select

# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_experiment(
    name: str = "test-exp",
    weights: tuple[float, float] = (0.5, 0.5),
) -> ABExperiment:
    return ABExperiment(
        name=name,
        variants=[
            Variant("control", weights[0], config={"prompt_version": "v1"}),
            Variant("treatment", weights[1], config={"prompt_version": "v2"}),
        ],
    )


# ── ABExperiment ──────────────────────────────────────────────────────────────


class TestABExperiment:
    def test_valid_weights_accepted(self) -> None:
        exp = _make_experiment(weights=(0.3, 0.7))
        assert len(exp.variants) == 2

    def test_invalid_weights_raise(self) -> None:
        with pytest.raises(ValueError, match="sum to 1.0"):
            ABExperiment(
                name="bad",
                variants=[Variant("a", 0.4), Variant("b", 0.4)],
            )

    def test_select_variant_for_user_id_is_deterministic(self) -> None:
        exp = _make_experiment()
        v1 = exp.select_variant(user_id="user-42")
        v2 = exp.select_variant(user_id="user-42")
        assert v1.name == v2.name

    def test_different_user_ids_may_get_different_variants(self) -> None:
        exp = _make_experiment()
        results = {exp.select_variant(user_id=f"user-{i}").name for i in range(50)}
        assert len(results) > 1  # both variants should appear

    def test_random_selection_returns_a_variant(self) -> None:
        exp = _make_experiment()
        variant = exp.select_variant()
        assert variant.name in ("control", "treatment")


# ── _hash_select ──────────────────────────────────────────────────────────────


class TestHashSelect:
    def test_consistent_for_same_input(self) -> None:
        variants = [Variant("a", 0.5), Variant("b", 0.5)]
        r1 = _hash_select(variants, "user-99")
        r2 = _hash_select(variants, "user-99")
        assert r1.name == r2.name

    def test_always_returns_a_variant(self) -> None:
        variants = [Variant("only", 1.0)]
        assert _hash_select(variants, "any-user").name == "only"


# ── ABRouter ──────────────────────────────────────────────────────────────────


class TestABRouter:
    @pytest.fixture
    def router(self) -> ABRouter:
        r = ABRouter()
        r.register(_make_experiment("prompt-test"))
        return r

    def test_select_returns_a_variant(self, router: ABRouter) -> None:
        variant = router.select("prompt-test")
        assert variant.name in ("control", "treatment")

    def test_impressions_incremented_on_select(self, router: ABRouter) -> None:
        for _ in range(5):
            router.select("prompt-test", user_id="user-1")
        stats = router.stats("prompt-test")
        total_impressions = sum(v["impressions"] for v in stats["variants"])
        assert total_impressions == 5

    def test_sticky_sessions_same_variant_per_user(self, router: ABRouter) -> None:
        variant_names = {router.select("prompt-test", user_id="alice").name for _ in range(10)}
        assert len(variant_names) == 1  # always the same

    def test_different_users_can_get_different_variants(self, router: ABRouter) -> None:
        variants = {router.select("prompt-test", user_id=f"u{i}").name for i in range(100)}
        assert len(variants) > 1

    def test_conversion_tracking(self, router: ABRouter) -> None:
        router.select("prompt-test", user_id="buyer-1")
        router.record_conversion("prompt-test", "control")
        stats = router.stats("prompt-test")
        total_conversions = sum(v["conversions"] for v in stats["variants"])
        assert total_conversions == 1

    def test_stats_shows_all_variants(self, router: ABRouter) -> None:
        stats = router.stats("prompt-test")
        variant_names = {v["name"] for v in stats["variants"]}
        assert "control" in variant_names
        assert "treatment" in variant_names

    def test_stats_raises_for_unknown_experiment(self, router: ABRouter) -> None:
        with pytest.raises(KeyError):
            router.stats("ghost-experiment")

    def test_tenants_have_independent_counters(self) -> None:
        router = ABRouter()
        router.register(_make_experiment("exp-a"))
        router.register(_make_experiment("exp-b"))
        router.select("exp-a", user_id="u1")
        router.select("exp-a", user_id="u2")
        stats_a = router.stats("exp-a")
        stats_b = router.stats("exp-b")
        total_a = sum(v["impressions"] for v in stats_a["variants"])
        total_b = sum(v["impressions"] for v in stats_b["variants"])
        assert total_a == 2
        assert total_b == 0

    def test_conversion_rate_computed_correctly(self, router: ABRouter) -> None:
        for _ in range(4):
            router.select("prompt-test", user_id="u1")
        router.record_conversion("prompt-test", "control")
        router.record_conversion("prompt-test", "control")
        stats = router.stats("prompt-test")
        control = next(v for v in stats["variants"] if v["name"] == "control")
        if control["impressions"] > 0:
            assert control["conversion_rate"] == pytest.approx(
                control["conversions"] / control["impressions"], rel=1e-3
            )
