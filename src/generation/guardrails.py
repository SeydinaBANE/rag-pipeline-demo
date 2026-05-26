from __future__ import annotations

from dataclasses import dataclass

import structlog

logger = structlog.get_logger(__name__)

_NO_ANSWER_MARKERS = (
    "i don't have enough information",
    "i cannot answer",
    "i don't know",
    "not mentioned in the context",
    "not provided in the context",
)


@dataclass
class GuardrailResult:
    passed: bool
    reason: str | None = None


class InputGuardrail:
    def __init__(self, min_length: int = 3, max_length: int = 1000) -> None:
        self._min = min_length
        self._max = max_length

    def check(self, query: str) -> GuardrailResult:
        stripped = query.strip()
        if not stripped:
            logger.warning("input_guardrail_blocked", reason="empty_query")
            return GuardrailResult(passed=False, reason="empty_query")
        if len(stripped) < self._min:
            logger.warning(
                "input_guardrail_blocked", reason="query_too_short", length=len(stripped)
            )
            return GuardrailResult(passed=False, reason="query_too_short")
        if len(stripped) > self._max:
            logger.warning("input_guardrail_blocked", reason="query_too_long", length=len(stripped))
            return GuardrailResult(passed=False, reason="query_too_long")
        return GuardrailResult(passed=True)


class OutputGuardrail:
    def check(self, answer: str, query: str) -> GuardrailResult:  # noqa: ARG002
        if not answer.strip():
            logger.warning("output_guardrail_blocked", reason="empty_answer")
            return GuardrailResult(passed=False, reason="empty_answer")
        lower = answer.strip().lower()
        for marker in _NO_ANSWER_MARKERS:
            if marker in lower:
                logger.info("output_no_answer_detected", marker=marker)
                break
        return GuardrailResult(passed=True)
