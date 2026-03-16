from __future__ import annotations

import hashlib
from dataclasses import dataclass

from fastapi import Header
from sqlalchemy import select

from voiceagent_api.db import SessionLocal
from voiceagent_api.errors import AuthenticationError, AuthorizationError
from voiceagent_api.models import ApiKeyModel
from voiceagent_api.schemas import utc_now


@dataclass(slots=True)
class AuthContext:
    api_key_id: str
    organization_id: str
    scopes: set[str]


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def require_scope(required_scope: str):
    async def _dependency(authorization: str | None = Header(default=None)) -> AuthContext:
        if not authorization or not authorization.startswith("Bearer "):
            raise AuthenticationError()

        api_key = authorization.removeprefix("Bearer ").strip()
        key_hash = hash_api_key(api_key)
        with SessionLocal() as session:
            key_model = session.scalar(
                select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash, ApiKeyModel.is_active.is_(True))
            )
            if key_model is None:
                raise AuthenticationError()
            scopes = set(key_model.scopes or [])
            if required_scope not in scopes:
                raise AuthorizationError()
            key_model.last_used_at = utc_now()
            session.add(key_model)
            session.commit()
            return AuthContext(
                api_key_id=key_model.id,
                organization_id=key_model.organization_id,
                scopes=scopes,
            )

    return _dependency
