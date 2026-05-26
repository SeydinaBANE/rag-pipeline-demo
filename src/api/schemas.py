from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    stream: bool = False
    prompt_version: str = "v1"


class SourceDocument(BaseModel):
    content: str
    source: str
    score: float | None = None


class QueryResponse(BaseModel):
    query: str
    answer: str
    sources: list[SourceDocument]
    cached: bool
    prompt_version: str
    latency_ms: float


class IngestResponse(BaseModel):
    job_id: str
    status: str
    filename: str


class FeedbackRequest(BaseModel):
    query: str
    answer: str
    rating: Literal[1, -1]
    comment: str | None = None


class FeedbackResponse(BaseModel):
    status: str


class HealthResponse(BaseModel):
    status: str
    version: str
    environment: str


class TokenData(BaseModel):
    sub: str
    tenant_id: str
