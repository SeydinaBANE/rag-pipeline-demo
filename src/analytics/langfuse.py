from __future__ import annotations

from collections.abc import Callable

import structlog

from src.generation.chain import RAGResponse

logger = structlog.get_logger(__name__)


class LangFuseTracer:
    """Wraps LangFuse tracing with graceful degradation when disabled or unavailable."""

    def __init__(  # nosec B107
        self,
        enabled: bool = False,
        host: str = "",
        secret_key: str = "",  # noqa: S107
        public_key: str = "",
    ) -> None:
        self._fn: Callable[[str, RAGResponse, str], None] | None = None
        if not enabled:
            return
        try:
            from langfuse import Langfuse

            client = Langfuse(host=host, secret_key=secret_key, public_key=public_key)

            def _trace(experiment_id: str, response: RAGResponse, tenant_id: str) -> None:
                trace = client.trace(
                    name="rag-query",
                    metadata={
                        "tenant_id": tenant_id,
                        "cached": response.cached,
                        "prompt_version": response.prompt_version,
                        "latency_ms": response.latency_ms,
                        "num_sources": len(response.sources),
                    },
                )
                trace.generation(
                    name="llm-generation",
                    input=response.query,
                    output=response.answer,
                    model="mistral-7b",
                )

            self._fn = _trace
            logger.info("langfuse_tracer_enabled", host=host)
        except Exception as exc:  # noqa: BLE001
            logger.warning("langfuse_tracer_init_failed", error=str(exc))

    @property
    def enabled(self) -> bool:
        return self._fn is not None

    def trace(self, experiment_id: str, response: RAGResponse, tenant_id: str) -> None:
        if self._fn is None:
            return
        try:
            self._fn(experiment_id, response, tenant_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("langfuse_trace_failed", error=str(exc))
