from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from voiceagent_api.app import app
from voiceagent_api.db import SessionLocal
from voiceagent_api.models import WebhookDeliveryModel
from voiceagent_api.store import store
from voiceagent_api.webhooks import DeliveryResult
from voiceagent_api.worker import WebhookDeliveryWorker

WRITE_HEADERS = {"Authorization": "Bearer dev-secret-key"}


def setup_function() -> None:
    store.reset()


def test_worker_run_once_processes_due_delivery(monkeypatch) -> None:
    attempts = iter(
        [
            DeliveryResult(status="failed", response_code=500, response_body="boom"),
            DeliveryResult(status="delivered", response_code=202, response_body="accepted"),
        ]
    )
    monkeypatch.setattr("voiceagent_api.store.dispatcher.deliver", lambda **kwargs: next(attempts))

    client = TestClient(app)
    hook = client.post(
        "/v1/webhooks",
        json={
            "target_url": "https://example.com/webhooks/voiceagent",
            "event_types": ["webhook.test"],
        },
        headers={**WRITE_HEADERS, "Idempotency-Key": "worker-webhook-1"},
    )
    assert hook.status_code == 200, f"Failed to create webhook: {hook.json()}"
    webhook_id = hook.json()["id"]

    created = client.post(
        f"/v1/webhooks/{webhook_id}/test", headers={**WRITE_HEADERS, "Idempotency-Key": "worker-webhook-test-1"}
    )
    delivery_id = created.json()["delivery_id"]

    with SessionLocal() as session:
        delivery = session.get(WebhookDeliveryModel, delivery_id)
        assert delivery is not None
        delivery.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
        session.add(delivery)
        session.commit()

    worker = WebhookDeliveryWorker(
        store_instance=store,
        organization_id="org_default",
        poll_interval_seconds=0.01,
        batch_size=10,
    )
    result = worker.run_once()

    assert result.processed == 1
    assert result.delivered == 1
    assert result.retry_scheduled == 0
    assert result.failed == 0


def test_worker_run_forever_honors_max_cycles(monkeypatch) -> None:
    calls: list[int] = []
    sleeps: list[float] = []

    class _StubStore:
        def process_webhook_deliveries(self, *, organization_id: str, now: datetime, limit: int) -> dict:
            calls.append(limit)
            return {
                "processed": 0,
                "delivered": 0,
                "retry_scheduled": 0,
                "failed": 0,
                "items": [],
            }

    worker = WebhookDeliveryWorker(
        store_instance=_StubStore(),  # type: ignore[arg-type]
        organization_id="org_default",
        poll_interval_seconds=0.25,
        batch_size=5,
        sleep_fn=lambda seconds: sleeps.append(seconds),
        now_fn=lambda: datetime(2026, 3, 10, tzinfo=UTC),
    )

    worker.run_forever(max_cycles=3)

    assert calls == [5, 5, 5]
    assert sleeps == [0.25, 0.25]
