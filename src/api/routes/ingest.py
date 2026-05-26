from __future__ import annotations

import uuid

import structlog
from fastapi import APIRouter, BackgroundTasks, UploadFile

from src.api.deps import CurrentUser, RateLimiter
from src.api.schemas import IngestResponse

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/", response_model=IngestResponse)
async def ingest(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    current_user: CurrentUser,
    limiter: RateLimiter,
) -> IngestResponse:
    limiter.check(current_user.tenant_id)
    content = await file.read()
    filename = file.filename or "upload"
    job_id = uuid.uuid4().hex[:12]
    background_tasks.add_task(
        _queue_indexing_job, content, filename, current_user.tenant_id, job_id
    )
    return IngestResponse(job_id=job_id, status="queued", filename=filename)


def _queue_indexing_job(content: bytes, filename: str, tenant_id: str, job_id: str) -> None:
    logger.info(
        "indexing_queued",
        job_id=job_id,
        filename=filename,
        tenant=tenant_id,
        size_bytes=len(content),
    )
