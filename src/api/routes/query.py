from __future__ import annotations

import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.analytics.prometheus import record_query
from src.api.deps import Chain, CurrentUser, RateLimiter
from src.api.schemas import QueryRequest, QueryResponse, SourceDocument

router = APIRouter()


@router.post("/", response_model=QueryResponse)
def query(
    request: QueryRequest,
    current_user: CurrentUser,
    chain: Chain,
    limiter: RateLimiter,
) -> QueryResponse:
    limiter.check(current_user.tenant_id)
    response = chain.invoke(request.query, tenant_id=current_user.tenant_id)
    record_query(response, tenant_id=current_user.tenant_id)
    sources = [
        SourceDocument(
            content=doc.page_content[:300],
            source=str(doc.metadata.get("source", "unknown")),
            score=doc.metadata.get("rrf_score") or doc.metadata.get("reranker_score"),
        )
        for doc in response.sources
    ]
    return QueryResponse(
        query=response.query,
        answer=response.answer,
        sources=sources,
        cached=response.cached,
        prompt_version=response.prompt_version,
        latency_ms=round(response.latency_ms, 1),
    )


@router.post("/stream")
def query_stream(
    request: QueryRequest,
    current_user: CurrentUser,
    chain: Chain,
    limiter: RateLimiter,
) -> StreamingResponse:
    limiter.check(current_user.tenant_id)

    def generate() -> object:
        for chunk in chain.stream(request.query, tenant_id=current_user.tenant_id):
            yield f"data: {json.dumps({'token': chunk})}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
