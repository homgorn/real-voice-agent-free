from __future__ import annotations

import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from voiceagent_api.cache import rate_limit_check
from voiceagent_api.config import settings

logger = logging.getLogger(__name__)

STRICT_PATHS = {
    "/v1/calls",
    "/v1/calls/",
}


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if not settings.valkey_url:
            return await call_next(request)

        path = request.url.path
        client_ip = request.client.host if request.client else "unknown"

        if path in STRICT_PATHS or path.startswith("/v1/calls/"):
            limit = settings.rate_limit_strict
        else:
            limit = settings.rate_limit_default

        key = f"ratelimit:{client_ip}:{path}"
        allowed, remaining = rate_limit_check(key, limit=limit, window=60)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": "Rate limit exceeded. Try again in 60 seconds.",
                        "category": "rate_limit",
                    }
                },
                headers={"Retry-After": "60"},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
