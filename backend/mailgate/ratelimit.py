"""In-memory rate limiting for a single-node MailGate host."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, Request, status

_lock = Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)


def allow(key: str, limit: int, window_seconds: int) -> bool:
    now = time.time()
    with _lock:
        bucket = _hits[key]
        cutoff = now - window_seconds
        while bucket and bucket[0] < cutoff:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
        return True


def enforce(request: Request, *, name: str, limit: int, window_seconds: int = 60) -> None:
    host = request.client.host if request.client else "unknown"
    key = f"{name}:{host}"
    if not allow(key, limit, window_seconds):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Try again later.",
        )
