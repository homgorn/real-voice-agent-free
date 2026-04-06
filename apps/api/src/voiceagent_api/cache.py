from __future__ import annotations

import json
import logging
from typing import Any

try:
    import valkey

    HAS_VALKEY = True
except ImportError:
    HAS_VALKEY = False

from voiceagent_api.config import settings

logger = logging.getLogger(__name__)

_client: valkey.Valkey | None = None


def get_client() -> valkey.Valkey | None:
    global _client
    if _client is not None:
        return _client
    if not HAS_VALKEY:
        return None
    url = getattr(settings, "valkey_url", None)
    if not url:
        return None
    try:
        _client = valkey.from_url(
            url,
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
            retry_on_timeout=True,
        )
        _client.ping()
        logger.info("Valkey connected: %s", url.split("@")[-1] if "@" in url else url)
        return _client
    except Exception:
        logger.warning("Valkey not available, falling back to SQL")
        return None


def close_client() -> None:
    global _client
    if _client is not None:
        _client.close()
        _client = None


def get(key: str) -> Any | None:
    client = get_client()
    if client is None:
        return None
    try:
        data = client.get(key)
        if data is None:
            return None
        return json.loads(data)
    except Exception:
        return None


def set(key: str, value: Any, ttl: int = 86400) -> bool:
    client = get_client()
    if client is None:
        return False
    try:
        client.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception:
        return False


def delete(key: str) -> bool:
    client = get_client()
    if client is None:
        return False
    try:
        client.delete(key)
        return True
    except Exception:
        return False


def rate_limit_check(key: str, limit: int, window: int = 60) -> tuple[bool, int]:
    """Sliding window rate limiter. Returns (allowed, remaining)."""
    client = get_client()
    if client is None:
        return True, limit
    import time

    now = time.time()
    pipe = client.pipeline()
    pipe.zremrangebyscore(key, 0, now - window)
    pipe.zadd(key, {str(now): now})
    pipe.zcard(key)
    pipe.expire(key, window)
    _, _, count, _ = pipe.execute()
    remaining = max(0, limit - count)
    return count < limit, remaining
