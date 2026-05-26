from __future__ import annotations

import structlog
from fastapi import APIRouter

from src.api.deps import CurrentUser
from src.api.schemas import FeedbackRequest, FeedbackResponse

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/", response_model=FeedbackResponse)
def feedback(
    request: FeedbackRequest,
    current_user: CurrentUser,
) -> FeedbackResponse:
    logger.info(
        "feedback_received",
        tenant=current_user.tenant_id,
        user=current_user.sub,
        rating=request.rating,
        query=request.query[:80],
        has_comment=request.comment is not None,
    )
    return FeedbackResponse(status="accepted")
