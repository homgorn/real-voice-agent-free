from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass

import httpx

from voiceagent_api.config import settings


@dataclass(slots=True)
class DeliveryResult:
    status: str
    response_code: int | None
    response_body: str | None


class WebhookDispatcher:
    def __init__(self, *, timeout_seconds: float | None = None) -> None:
        self.timeout_seconds = timeout_seconds or settings.webhook_timeout_seconds

    def deliver(self, *, target_url: str, secret: str, event: dict) -> DeliveryResult:
        body = json.dumps(event, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        headers = {
            "Content-Type": "application/json",
            "X-VoiceAgent-Signature": signature,
            "X-VoiceAgent-Event": event["event_type"],
            "X-VoiceAgent-Event-Id": event["event_id"],
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(target_url, content=body, headers=headers)
            status = "delivered" if 200 <= response.status_code < 300 else "failed"
            return DeliveryResult(
                status=status,
                response_code=response.status_code,
                response_body=response.text[:2000],
            )
        except httpx.HTTPError as exc:
            return DeliveryResult(
                status="failed",
                response_code=None,
                response_body=str(exc)[:2000],
            )


dispatcher = WebhookDispatcher()
