from __future__ import annotations

import hashlib
import json
import uuid

from fastapi import Request
from fastapi.encoders import jsonable_encoder

from voiceagent_api.errors import IdempotencyRequiredError


def trace_id_from_request(request: Request) -> str:
    return request.headers.get("x-trace-id", str(uuid.uuid4()))


def idempotency_key_from_request(request: Request) -> str | None:
    key = request.headers.get("Idempotency-Key") or request.headers.get("idempotency-key")
    if key is None:
        return None
    key = key.strip()
    return key or None


def require_idempotency_key(request: Request) -> str:
    key = idempotency_key_from_request(request)
    if not key:
        raise IdempotencyRequiredError()
    return key


def idempotency_request_hash(payload: object, *, path: str, method: str) -> str:
    body = jsonable_encoder({"payload": payload, "path": path, "method": method.upper()})
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def apply_pagination(
    items: list[object], *, limit: int | None, offset: int, max_limit: int = 100
) -> tuple[list[object], int]:
    total = len(items)
    if offset < 0:
        offset = 0
    if limit is None:
        limit = total
    else:
        limit = max(0, min(limit, max_limit))
    if offset >= total:
        return [], total
    return items[offset : offset + limit], total


def normalize_pagination(limit: int | None, offset: int, max_limit: int = 100) -> tuple[int, int]:
    if offset < 0:
        offset = 0
    if limit is None:
        limit = max_limit
    else:
        limit = max(0, min(limit, max_limit))
    return limit, offset
