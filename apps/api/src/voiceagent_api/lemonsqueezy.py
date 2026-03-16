from __future__ import annotations

import hashlib
import hmac

import httpx

from voiceagent_api.config import settings


def verify_webhook_signature(raw_body: bytes, signature: str) -> bool:
    digest = hmac.new(
        settings.lemon_squeezy_webhook_secret.encode("utf-8"),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(digest, signature)


def extract_event_metadata(payload: dict) -> dict[str, str | None]:
    meta = payload.get("meta", {}) or {}
    data = payload.get("data", {}) or {}
    return {
        "event_name": meta.get("event_name"),
        "resource_type": data.get("type"),
        "resource_id": data.get("id"),
    }


def validate_license_key(*, license_key: str, instance_name: str | None, instance_id: str | None) -> dict:
    form = {"license_key": license_key}
    if instance_name:
        form["instance_name"] = instance_name
    if instance_id:
        form["instance_id"] = instance_id

    url = f"{settings.lemon_squeezy_api_base.rstrip('/')}/v1/licenses/validate"
    with httpx.Client(timeout=10) as client:
        response = client.post(
            url,
            data=form,
            headers={"Accept": "application/json"},
        )
    response.raise_for_status()
    return response.json()
