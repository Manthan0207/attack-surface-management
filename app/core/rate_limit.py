#in-memory rate limiter for auth login endpoint
from __future__ import annotations

import threading
import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

from app.core.config import settings

_lock = threading.Lock()
_attempts: dict[str, list[float]] = defaultdict(list)


def client_ip(request: Request) -> str:
    """best effort client ip """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def reset_rate_limits() -> None: #for test usecase
    with _lock:
        _attempts.clear()


def clear_client(key: str) -> None: #clear attempts after login success
    with _lock:
        _attempts.pop(key, None)


def enforce_login_rate_limit(request: Request) -> str:
    """Raise 429 if this client exceeded the login attempt budget"""
    key = client_ip(request)
    now = time.monotonic()
    window = settings.login_rate_window_seconds
    limit = settings.login_rate_limit

    with _lock:
        stamps = [t for t in _attempts[key] if now - t < window]
        if len(stamps) >= limit:
            _attempts[key] = stamps
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many login attempts. Please try again later.",
            )
        stamps.append(now)
        _attempts[key] = stamps

    return key
