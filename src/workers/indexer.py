"""SQS document indexing worker.

Polls the configured SQS queue for indexing jobs, processes each document,
and deletes the message on success. On failure, lets the visibility timeout
expire so SQS retries (up to the DLQ threshold).

Run with:
    python -m src.workers.indexer
"""

from __future__ import annotations

import json
import signal
import time
from pathlib import Path
from typing import Any

import boto3
import structlog

from src.config import get_settings

logger = structlog.get_logger(__name__)


class IndexingWorker:
    """Poll SQS for indexing jobs and process them."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._running = True
        self._sqs = boto3.client("sqs", region_name=self._settings.worker.aws_region)
        self._queue_url = self._settings.worker.sqs_queue_url

    def run(self) -> None:
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)
        logger.info("worker_started", queue=self._queue_url)

        while self._running:
            self._poll_once()

    def _handle_shutdown(self, signum: int, frame: object) -> None:
        self._running = False
        logger.info("worker_shutdown_signal", signal=signum)

    def _poll_once(self) -> None:
        if not self._queue_url:
            time.sleep(1)
            return

        response: dict[str, Any] = self._sqs.receive_message(
            QueueUrl=self._queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=self._settings.worker.poll_wait_seconds,
            VisibilityTimeout=self._settings.worker.visibility_timeout,
        )
        for msg in response.get("Messages", []):
            self._process(msg)

    def _process(self, message: dict[str, Any]) -> None:
        receipt: str = message["ReceiptHandle"]
        try:
            body: dict[str, Any] = json.loads(message["Body"])
            tenant_id: str = str(body["tenant_id"])
            file_path = Path(str(body["file_path"]))

            from src.chunking.parent_child import ParentChildChunker
            from src.embedding.ollama import OllamaEmbedder
            from src.ingestion.loaders import DocumentLoader
            from src.vectorstore.chroma import ChromaVectorStore

            s = self._settings
            docs = DocumentLoader().load(file_path)
            chunks = ParentChildChunker(s.chunking).split(docs)
            embedder = OllamaEmbedder(s.embedding)
            store = ChromaVectorStore(embedder, s.vectorstore)
            store.add_documents(chunks, tenant_id=tenant_id)

            self._sqs.delete_message(QueueUrl=self._queue_url, ReceiptHandle=receipt)
            logger.info(
                "message_processed",
                file=str(file_path),
                chunks=len(chunks),
                tenant=tenant_id,
            )
        except Exception as exc:
            logger.error(
                "message_failed",
                error=str(exc),
                message_id=message.get("MessageId"),
            )


if __name__ == "__main__":
    IndexingWorker().run()
