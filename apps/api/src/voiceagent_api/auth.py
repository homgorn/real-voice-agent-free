from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

import bcrypt
from fastapi import Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from voiceagent_api.db import SessionLocal
from voiceagent_api.errors import AuthenticationError, AuthorizationError
from voiceagent_api.models import ApiKeyModel
from voiceagent_api.schemas import utc_now


@dataclass(slots=True)
class AuthContext:
    api_key_id: str
    organization_id: str
    scopes: set[str]


_BCRYPT_PREFIXES = ("$2a$", "$2b$", "$2y$")


def legacy_hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def hash_api_key(raw_key: str) -> str:
    return bcrypt.hashpw(raw_key.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def is_bcrypt_api_key_hash(stored_hash: str) -> bool:
    return stored_hash.startswith(_BCRYPT_PREFIXES)


def verify_api_key(raw_key: str, stored_hash: str) -> bool:
    raw_key_bytes = raw_key.encode("utf-8")
    if is_bcrypt_api_key_hash(stored_hash):
        try:
            return bcrypt.checkpw(raw_key_bytes, stored_hash.encode("utf-8"))
        except ValueError:
            return False
    return hmac.compare_digest(legacy_hash_api_key(raw_key), stored_hash)


def find_api_key_model(
    session: Session,
    raw_key: str,
    *,
    organization_id: str | None = None,
) -> ApiKeyModel | None:
    filters = [ApiKeyModel.is_active.is_(True)]
    if organization_id is not None:
        filters.append(ApiKeyModel.organization_id == organization_id)

    legacy_hash = legacy_hash_api_key(raw_key)
    legacy_match = session.scalar(
        select(ApiKeyModel).where(
            *filters,
            ApiKeyModel.key_hash == legacy_hash,
        )
    )
    if legacy_match is not None:
        return legacy_match

    candidates = session.scalars(select(ApiKeyModel).where(*filters)).all()
    for candidate in candidates:
        if candidate.key_hash == legacy_hash:
            continue
        if verify_api_key(raw_key, candidate.key_hash):
            return candidate
    return None


def require_scope(required_scope: str):
    async def _dependency(authorization: str | None = Header(default=None)) -> AuthContext:
        if not authorization or not authorization.startswith("Bearer "):
            raise AuthenticationError()

        api_key = authorization.removeprefix("Bearer ").strip()
        with SessionLocal() as session:
            key_model = find_api_key_model(session, api_key)
            if key_model is None:
                raise AuthenticationError()
            scopes = set(key_model.scopes or [])
            if required_scope not in scopes:
                raise AuthorizationError()
            if not is_bcrypt_api_key_hash(key_model.key_hash):
                key_model.key_hash = hash_api_key(api_key)
            key_model.last_used_at = utc_now()
            session.add(key_model)
            session.commit()
            return AuthContext(
                api_key_id=key_model.id,
                organization_id=key_model.organization_id,
                scopes=scopes,
            )

    return _dependency
