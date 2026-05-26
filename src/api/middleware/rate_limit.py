from __future__ import annotations

import time
from collections import deque
from threading import Lock

from fastapi import HTTPException, status


class SlidingWindowRateLimiter:
    """In-memory sliding window rate limiter, keyed by tenant_id."""

    def __init__(self, max_requests: int, window_seconds: int = 60) -> None:
        self._max = max_requests
        self._window = window_seconds
        self._requests: dict[str, deque[float]] = {}
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = time.time()
        with self._lock:
            dq = self._requests.setdefault(key, deque())
            while dq and dq[0] < now - self._window:
                dq.popleft()
            if len(dq) >= self._max:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded — try again later",
                )
            dq.append(now)
