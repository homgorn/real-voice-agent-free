from __future__ import annotations

from datetime import UTC, datetime, timedelta
from fastapi.testclient import TestClient
import hashlib
import hmac
import importlib
import json

from voiceagent_api.app import app
from voiceagent_api.auth import hash_api_key
from voiceagent_api.config import settings
from voiceagent_api.db import SessionLocal
from voiceagent_api.models import ApiKeyModel, OrganizationModel, WebhookDeliveryModel
from voiceagent_api.store import store
from voiceagent_api.webhooks import DeliveryResult, WebhookDispatcher


WRITE_HEADERS = {"Authorization": "Bearer dev-secret-key"}
READ_HEADERS = {"Authorization": "Bearer read-only-key"}
SECOND_ORG_HEADERS = {"Authorization": "Bearer second-org-key"}


def with_idempotency(headers: dict[str, str], key: str) -> dict[str, str]:
    return {**headers, "Idempotency-Key": key}


def setup_function() -> None:
    store.reset()


def test_health() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready() -> None:
    client = TestClient(app)
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json()["status"] == "ready"


def test_current_organization_and_api_keys() -> None:
    client = TestClient(app)

    org = client.get("/v1/organizations/current", headers=WRITE_HEADERS)
    assert org.status_code == 200
    assert org.json()["id"] == "org_default"

    api_keys = client.get("/v1/api-keys", headers=WRITE_HEADERS)
    assert api_keys.status_code == 200
    assert api_keys.json()["total"] >= 2


def test_plans_list() -> None:
    client = TestClient(app)
    response = client.get("/v1/plans", headers=WRITE_HEADERS)
    assert response.status_code == 200
    assert response.json()["total"] >= 3


def test_agents_list_requires_auth() -> None:
    client = TestClient(app)
    response = client.get("/v1/agents")
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "authentication_error"
    assert body["error"]["category"] == "auth"
    assert body["error"]["trace_id"]


def test_read_only_key_cannot_create_agent() -> None:
    client = TestClient(app)
    payload = {
        "name": "Front Desk",
        "template_id": "tpl_receptionist_booking_v1",
        "timezone": "Asia/Almaty",
        "default_language": "ru",
        "business_hours": {"mon_fri": ["09:00-18:00"]},
    }
    response = client.post("/v1/agents", json=payload, headers=READ_HEADERS)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "authorization_error"


def test_resources_are_scoped_by_organization() -> None:
    with SessionLocal() as session:
        session.add(
            OrganizationModel(
                id="org_second",
                name="Second Organization",
                slug="second-organization",
                created_at=store.get_current_organization("org_default")["created_at"],
                updated_at=store.get_current_organization("org_default")["updated_at"],
            )
        )
        session.add(
            ApiKeyModel(
                id="key_second",
                organization_id="org_second",
                name="second",
                key_hash=hash_api_key("second-org-key"),
                scopes=["orgs:read", "api_keys:read", "agents:read"],
                is_active=True,
                created_at=store.get_current_organization("org_default")["created_at"],
                last_used_at=None,
            )
        )
        session.commit()

    client = TestClient(app)
    payload = {
        "name": "Front Desk",
        "template_id": "tpl_receptionist_booking_v1",
        "timezone": "Asia/Almaty",
        "default_language": "ru",
        "business_hours": {"mon_fri": ["09:00-18:00"]},
    }
    created = client.post("/v1/agents", json=payload, headers=with_idempotency(WRITE_HEADERS, "idem-agent-1"))
    agent_id = created.json()["id"]

    second_org_list = client.get("/v1/agents", headers=SECOND_ORG_HEADERS)
    assert second_org_list.status_code == 200
    assert second_org_list.json()["total"] == 0

    second_org_fetch = client.get(f"/v1/agents/{agent_id}", headers=SECOND_ORG_HEADERS)
    assert second_org_fetch.status_code == 404


def test_create_and_get_agent() -> None:
    client = TestClient(app)
    payload = {
        "name": "Front Desk",
        "template_id": "tpl_receptionist_booking_v1",
        "timezone": "Asia/Almaty",
        "default_language": "ru",
        "business_hours": {"mon_fri": ["09:00-18:00"]},
    }

    created = client.post("/v1/agents", json=payload, headers=with_idempotency(WRITE_HEADERS, "idem-agent-2"))
    assert created.status_code == 200
    body = created.json()
    assert body["status"] == "draft"
    agent_id = body["id"]

    listed = client.get("/v1/agents", headers=WRITE_HEADERS)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    fetched = client.get(f"/v1/agents/{agent_id}", headers=WRITE_HEADERS)
    assert fetched.status_code == 200
    assert fetched.json()["id"] == agent_id
    assert fetched.json()["name"] == "Front Desk"


def test_publish_agent() -> None:
    client = TestClient(app)
    payload = {
        "name": "Front Desk",
        "template_id": "tpl_receptionist_booking_v1",
        "timezone": "Asia/Almaty",
        "default_language": "ru",
        "business_hours": {"mon_fri": ["09:00-18:00"]},
    }

    created = client.post("/v1/agents", json=payload, headers=with_idempotency(WRITE_HEADERS, "idem-agent-2a"))
    agent_id = created.json()["id"]

    published = client.post(
        f"/v1/agents/{agent_id}/publish",
        json={"target_environment": "production"},
        headers=with_idempotency(WRITE_HEADERS, "idem-publish-1"),
    )
    assert published.status_code == 200
    assert published.json()["status"] == "published"
    assert published.json()["version_id"].startswith("ver_")

    fetched = client.get(f"/v1/agents/{agent_id}", headers=WRITE_HEADERS)
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "published"
    assert fetched.json()["published_version_id"] == published.json()["version_id"]


def test_list_agent_versions() -> None:
    client = TestClient(app)
    payload = {
        "name": "Front Desk",
        "template_id": "tpl_receptionist_booking_v1",
        "timezone": "Asia/Almaty",
        "default_language": "ru",
        "business_hours": {"mon_fri": ["09:00-18:00"]},
    }

    created = client.post("/v1/agents", json=payload, headers=with_idempotency(WRITE_HEADERS, "idem-agent-3"))
    agent_id = created.json()["id"]
    publish = client.post(
        f"/v1/agents/{agent_id}/publish",
        json={"target_environment": "production"},
        headers=with_idempotency(WRITE_HEADERS, "idem-publish-2"),
    )
    version_id = publish.json()["version_id"]

    versions = client.get(f"/v1/agents/{agent_id}/versions", headers=WRITE_HEADERS)
    assert versions.status_code == 200
    body = versions.json()
    assert body["total"] == 1
    assert body["items"][0]["version_id"] == version_id
    assert body["items"][0]["agent_id"] == agent_id


def test_publish_agent_emits_event() -> None:
    client = TestClient(app)
    payload = {
        "name": "Front Desk",
        "template_id": "tpl_receptionist_booking_v1",
        "timezone": "Asia/Almaty",
        "default_language": "ru",
        "business_hours": {"mon_fri": ["09:00-18:00"]},
    }

    created = client.post("/v1/agents", json=payload, headers=with_idempotency(WRITE_HEADERS, "idem-agent-4"))
    agent_id = created.json()["id"]
    client.post(
        f"/v1/agents/{agent_id}/publish",
        json={"target_environment": "production"},
        headers=with_idempotency(WRITE_HEADERS, "idem-publish-3"),
    )

    events = client.get("/v1/events", headers=WRITE_HEADERS)
    assert events.status_code == 200
    body = events.json()
    assert body["total"] >= 1
    assert any(item["event_type"] == "agent.published" for item in body["items"])


def test_create_booking_emits_booking_event() -> None:
    client = TestClient(app)
    agent_payload = {
        "name": "Front Desk",
        "template_id": "tpl_receptionist_booking_v1",
        "timezone": "Asia/Almaty",
        "default_language": "ru",
        "business_hours": {"mon_fri": ["09:00-18:00"]},
    }
    created_agent = client.post(
        "/v1/agents",
        json=agent_payload,
        headers=with_idempotency(WRITE_HEADERS, "idem-agent-5"),
    )
    agent_id = created_agent.json()["id"]

    booking_payload = {
        "agent_id": agent_id,
        "contact_name": "Алина",
        "contact_phone": "+77011234567",
        "service": "consultation",
        "start_at": "2026-03-10T15:00:00+05:00",
    }
    created_booking = client.post(
        "/v1/bookings",
        json=booking_payload,
        headers=with_idempotency(WRITE_HEADERS, "idem-booking-1"),
    )
    assert created_booking.status_code == 200
    booking_body = created_booking.json()
    assert booking_body["status"] == "confirmed"
    assert booking_body["external_booking_id"].startswith("cal_")

    bookings = client.get("/v1/bookings", headers=WRITE_HEADERS)
    assert bookings.status_code == 200
    assert bookings.json()["total"] == 1

    events = client.get("/v1/events", headers=WRITE_HEADERS)
    assert events.status_code == 200
    assert any(item["event_type"] == "booking.created" for item in events.json()["items"])


def test_call_lifecycle_emits_events() -> None:
    client = TestClient(app)
    agent_payload = {
        "name": "Front Desk",
        "template_id": "tpl_receptionist_booking_v1",
        "timezone": "Asia/Almaty",
        "default_language": "ru",
        "business_hours": {"mon_fri": ["09:00-18:00"]},
    }
    created_agent = client.post(
        "/v1/agents",
        json=agent_payload,
        headers=with_idempotency(WRITE_HEADERS, "idem-agent-6"),
    )
    agent_id = created_agent.json()["id"]

    created_call = client.post(
        "/v1/calls",
        json={
            "agent_id": agent_id,
            "direction": "inbound",
            "from_number": "+77011234567",
            "to_number": "+77021234567",
        },
        headers=with_idempotency(WRITE_HEADERS, "idem-call-1"),
    )
    assert created_call.status_code == 200
    call_id = created_call.json()["id"]
    assert created_call.json()["status"] == "active"

    turn = client.post(
        f"/v1/calls/{call_id}/turns",
        json={
            "user_text": "Хочу записаться на завтра",
            "assistant_text": "Подскажите удобное время",
            "latency_ms": 850,
            "provider_breakdown": {"stt_ms": 100, "llm_ms": 500, "tts_ms": 250},
            "tool_calls": [{"tool_name": "calendar.lookup_slots", "status": "ok"}],
        },
        headers=with_idempotency(WRITE_HEADERS, "idem-turn-1"),
    )
    assert turn.status_code == 200
    assert turn.json()["turn_index"] == 0

    completed = client.post(
        f"/v1/calls/{call_id}/complete",
        json={
            "outcome": "booking_created",
            "duration_ms": 183000,
            "recording_available": True,
            "summary_text": "Клиент записан на консультацию",
            "structured_summary": {"service": "consultation"},
        },
        headers=with_idempotency(WRITE_HEADERS, "idem-complete-1"),
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"

    turns = client.get(f"/v1/calls/{call_id}/turns", headers=WRITE_HEADERS)
    assert turns.status_code == 200
    assert turns.json()["total"] == 1

    summary = client.get(f"/v1/calls/{call_id}/summary", headers=WRITE_HEADERS)
    assert summary.status_code == 200
    assert summary.json()["summary_text"] == "Клиент записан на консультацию"

    events = client.get("/v1/events", headers=WRITE_HEADERS)
    assert events.status_code == 200
    event_types = {item["event_type"] for item in events.json()["items"]}
    assert "call.started" in event_types
    assert "call.turn.completed" in event_types
    assert "call.ended" in event_types


def test_webhook_dispatcher_signs_and_delivers(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class _FakeResponse:
        status_code = 202
        text = "accepted"

    class _FakeClient:
        def __init__(self, *args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, content=None, headers=None):
            captured["url"] = url
            captured["content"] = content
            captured["headers"] = headers
            return _FakeResponse()

    monkeypatch.setattr("voiceagent_api.webhooks.httpx.Client", _FakeClient)

    dispatcher = WebhookDispatcher(timeout_seconds=3)
    result = dispatcher.deliver(
        target_url="https://example.com/hook",
        secret="whsec_test",
        event={
            "event_id": "evt_1",
            "event_type": "booking.created",
            "event_version": "v1",
            "occurred_at": "2026-03-09T12:00:00Z",
            "trace_id": "trc_1",
            "tenant_id": "default",
            "source": "runtime",
            "payload": {"booking_id": "bk_1"},
        },
    )
    assert result.status == "delivered"
    assert result.response_code == 202
    assert captured["url"] == "https://example.com/hook"
    assert captured["headers"]["X-VoiceAgent-Event"] == "booking.created"
    assert captured["headers"]["X-VoiceAgent-Signature"]


def test_webhook_creation_and_test_delivery(monkeypatch) -> None:
    monkeypatch.setattr(
        "voiceagent_api.store.dispatcher.deliver",
        lambda **kwargs: DeliveryResult(status="delivered", response_code=202, response_body="accepted"),
    )
    client = TestClient(app)
    create_hook = client.post(
        "/v1/webhooks",
        json={
            "target_url": "https://example.com/webhooks/voiceagent",
            "event_types": ["booking.created", "agent.published"],
        },
        headers=with_idempotency(WRITE_HEADERS, "idem-webhook-1"),
    )
    assert create_hook.status_code == 200
    hook_body = create_hook.json()
    assert hook_body["id"].startswith("wh_")
    assert hook_body["secret"].startswith("whsec_")

    list_hooks = client.get("/v1/webhooks", headers=WRITE_HEADERS)
    assert list_hooks.status_code == 200
    assert list_hooks.json()["total"] == 1

    test_delivery = client.post(f"/v1/webhooks/{hook_body['id']}/test", headers=WRITE_HEADERS)
    assert test_delivery.status_code == 200
    delivery_body = test_delivery.json()
    assert delivery_body["webhook_id"] == hook_body["id"]
    assert delivery_body["status"] == "delivered"

    deliveries = client.get(f"/v1/webhooks/{hook_body['id']}/deliveries", headers=WRITE_HEADERS)
    assert deliveries.status_code == 200
    deliveries_body = deliveries.json()
    assert deliveries_body["total"] == 1
    assert deliveries_body["items"][0]["status"] == "delivered"
    assert deliveries_body["items"][0]["event_type"] == "webhook.test"

    events = client.get("/v1/events", headers=WRITE_HEADERS)
    assert events.status_code == 200
    assert any(item["event_type"] == "webhook.test" for item in events.json()["items"])


def test_manual_retry_redelivers_failed_webhook(monkeypatch) -> None:
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
        headers=with_idempotency(WRITE_HEADERS, "idem-webhook-2"),
    )
    webhook_id = hook.json()["id"]

    created = client.post(f"/v1/webhooks/{webhook_id}/test", headers=WRITE_HEADERS)
    assert created.status_code == 200
    assert created.json()["status"] == "retry_scheduled"
    delivery_id = created.json()["delivery_id"]

    retried = client.post(
        f"/v1/webhooks/{webhook_id}/deliveries/{delivery_id}/retry",
        headers=WRITE_HEADERS,
    )
    assert retried.status_code == 200
    assert retried.json()["id"] == delivery_id
    assert retried.json()["status"] == "delivered"
    assert retried.json()["attempt_count"] == 2
    assert retried.json()["last_error"] is None


def test_process_webhook_queue_retries_due_deliveries(monkeypatch) -> None:
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
        headers=with_idempotency(WRITE_HEADERS, "idem-webhook-3"),
    )
    webhook_id = hook.json()["id"]

    created = client.post(f"/v1/webhooks/{webhook_id}/test", headers=WRITE_HEADERS)
    assert created.status_code == 200
    delivery_id = created.json()["delivery_id"]

    with SessionLocal() as session:
        delivery = session.get(WebhookDeliveryModel, delivery_id)
        assert delivery is not None
        delivery.next_attempt_at = datetime.now(UTC) - timedelta(seconds=1)
        session.add(delivery)
        session.commit()

    processed = client.post("/v1/webhooks/deliveries/process?limit=10", headers=WRITE_HEADERS)
    assert processed.status_code == 200
    body = processed.json()
    assert body["processed"] == 1
    assert body["delivered"] == 1
    assert body["retry_scheduled"] == 0
    assert body["failed"] == 0
    assert body["items"][0]["id"] == delivery_id
    assert body["items"][0]["status"] == "delivered"
    assert body["items"][0]["attempt_count"] == 2


def test_lemonsqueezy_webhook_updates_subscription(monkeypatch) -> None:
    monkeypatch.setattr(
        "voiceagent_api.store.dispatcher.deliver",
        lambda **kwargs: DeliveryResult(status="delivered", response_code=202, response_body="accepted"),
    )
    payload = {
        "meta": {
            "event_name": "subscription_created",
            "custom_data": {"organization_id": "org_default", "plan_code": "growth"},
        },
        "data": {
            "type": "subscriptions",
            "id": "sub_123",
            "attributes": {
                "status": "active",
                "status_formatted": "Active",
                "user_email": "owner@example.com",
                "user_name": "Owner",
                "product_id": 1001,
                "variant_id": 2002,
                "order_id": 3003,
                "store_id": 4004,
                "test_mode": True,
                "renews_at": "2026-04-10T10:00:00Z",
                "ends_at": None,
                "variant_name": "growth",
            },
        },
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(
        settings.lemon_squeezy_webhook_secret.encode("utf-8"),
        raw,
        hashlib.sha256,
    ).hexdigest()

    client = TestClient(app)
    response = client.post(
        "/v1/billing/lemonsqueezy/webhook",
        content=raw,
        headers={"X-Signature": signature, "Content-Type": "application/json"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "processed"

    subscriptions = client.get("/v1/subscriptions", headers=WRITE_HEADERS)
    assert subscriptions.status_code == 200
    body = subscriptions.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == "sub_123"
    assert body["items"][0]["plan_code"] == "growth"

    events = client.get("/v1/events", headers=WRITE_HEADERS)
    assert events.status_code == 200
    assert any(item["event_type"] == "subscription.activated" for item in events.json()["items"])


def test_license_validate_syncs_license(monkeypatch) -> None:
    app_module = importlib.import_module("voiceagent_api.app")
    monkeypatch.setattr(
        app_module,
        "validate_license_key",
        lambda **kwargs: {
            "valid": True,
            "error": None,
            "license_key": {
                "id": "lic_123",
                "status": "active",
                "key": "abcd-efgh-ijkl-mnop",
                "customer_email": "owner@example.com",
                "customer_name": "Owner",
                "activation_limit": 3,
                "activation_usage": 1,
                "expires_at": "2026-12-31T00:00:00Z",
                "product_id": 1001,
                "variant_id": 2002,
            },
            "instance": {"id": "inst_123"},
            "meta": {"store_id": 4004},
        },
    )
    client = TestClient(app)
    response = client.post(
        "/v1/licenses/validate",
        json={"license_key": "abcd-efgh-ijkl-mnop", "instance_name": "voiceagent-prod"},
        headers=with_idempotency(WRITE_HEADERS, "idem-license-1"),
    )
    assert response.status_code == 200
    assert response.json()["valid"] is True

    licenses = client.get("/v1/licenses", headers=WRITE_HEADERS)
    assert licenses.status_code == 200
    body = licenses.json()
    assert body["total"] == 1
    assert body["items"][0]["id"] == "lic_123"
    assert body["items"][0]["status"] == "active"


def test_templates_list_and_instantiate() -> None:
    client = TestClient(app)
    templates = client.get("/v1/templates", headers=WRITE_HEADERS)
    assert templates.status_code == 200
    body = templates.json()
    assert body["total"] >= 1
    template_id = body["items"][0]["id"]

    created = client.post(
        f"/v1/templates/{template_id}/instantiate",
        json={
            "name": "Reception Desk",
            "timezone": "Asia/Almaty",
            "default_language": "ru",
            "business_hours": {"mon_fri": ["10:00-19:00"]},
        },
        headers=with_idempotency(WRITE_HEADERS, "idem-template-1"),
    )
    assert created.status_code == 200
    created_body = created.json()
    assert created_body["template_id"] == template_id
    assert created_body["status"] == "draft"


def test_phone_numbers_crud() -> None:
    client = TestClient(app)
    created = client.post(
        "/v1/phone-numbers",
        json={
            "provider": "stub",
            "number": "+15551234567",
            "label": "Front Desk",
            "status": "active",
            "capabilities": {"voice": True},
        },
        headers=with_idempotency(WRITE_HEADERS, "idem-number-1"),
    )
    assert created.status_code == 200
    number_id = created.json()["id"]

    listed = client.get("/v1/phone-numbers", headers=WRITE_HEADERS)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    updated = client.patch(
        f"/v1/phone-numbers/{number_id}",
        json={"label": "Front Desk Line", "status": "inactive"},
        headers=WRITE_HEADERS,
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "inactive"
    assert updated.json()["label"] == "Front Desk Line"


def test_integrations_connect_and_test() -> None:
    client = TestClient(app)
    connected = client.post(
        "/v1/integrations/calendar/connect",
        json={"config": {"calendar_id": "cal_123"}},
        headers=with_idempotency(WRITE_HEADERS, "idem-integration-1"),
    )
    assert connected.status_code == 200
    assert connected.json()["provider"] == "calendar"
    assert connected.json()["status"] == "connected"

    listed = client.get("/v1/integrations", headers=WRITE_HEADERS)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    tested = client.post("/v1/integrations/calendar/test", headers=WRITE_HEADERS)
    assert tested.status_code == 200
    assert tested.json()["status"] == "healthy"


def test_knowledge_base_create_and_document() -> None:
    client = TestClient(app)
    created = client.post(
        "/v1/knowledge-bases",
        json={"name": "FAQ", "description": "Basic FAQ content"},
        headers=with_idempotency(WRITE_HEADERS, "idem-kb-1"),
    )
    assert created.status_code == 200
    kb_id = created.json()["id"]

    document = client.post(
        f"/v1/knowledge-bases/{kb_id}/documents",
        json={"title": "Hours", "content": "We are open daily 9-6."},
        headers=with_idempotency(WRITE_HEADERS, "idem-kbdoc-1"),
    )
    assert document.status_code == 200
    assert document.json()["knowledge_base_id"] == kb_id

    listed = client.get("/v1/knowledge-bases", headers=WRITE_HEADERS)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1


def test_usage_endpoints() -> None:
    client = TestClient(app)
    agent_payload = {
        "name": "Support Desk",
        "template_id": "tpl_receptionist_booking_v1",
        "timezone": "Asia/Almaty",
        "default_language": "ru",
        "business_hours": {"mon_fri": ["09:00-18:00"]},
    }
    created_agent = client.post(
        "/v1/agents",
        json=agent_payload,
        headers=with_idempotency(WRITE_HEADERS, "idem-agent-7"),
    )
    agent_id = created_agent.json()["id"]

    created_call = client.post(
        "/v1/calls",
        json={
            "agent_id": agent_id,
            "direction": "inbound",
            "from_number": "+77011230000",
            "to_number": "+77021230000",
        },
        headers=with_idempotency(WRITE_HEADERS, "idem-call-2"),
    )
    call_id = created_call.json()["id"]

    client.post(
        f"/v1/calls/{call_id}/complete",
        json={
            "outcome": "faq_resolved",
            "duration_ms": 60000,
            "recording_available": False,
            "summary_text": "Answered pricing questions",
            "structured_summary": {"topic": "pricing"},
        },
        headers=with_idempotency(WRITE_HEADERS, "idem-complete-2"),
    )

    summary = client.get("/v1/usage", headers=WRITE_HEADERS)
    assert summary.status_code == 200
    assert summary.json()["total_calls"] == 1

    costs = client.get("/v1/usage/costs", headers=WRITE_HEADERS)
    assert costs.status_code == 200
    assert costs.json()["currency"] == "USD"


def test_partner_endpoints() -> None:
    client = TestClient(app)
    current = client.get("/v1/partners/current", headers=WRITE_HEADERS)
    assert current.status_code == 200
    partner_id = current.json()["id"]

    accounts = client.get("/v1/partners/current/accounts", headers=WRITE_HEADERS)
    assert accounts.status_code == 200
    assert accounts.json()["total"] == 0

    created = client.post(
        "/v1/partners/current/accounts",
        json={"name": "Client Organization"},
        headers=with_idempotency(WRITE_HEADERS, "idem-partner-1"),
    )
    assert created.status_code == 200
    body = created.json()
    assert body["partner_id"] == partner_id
    assert body["organization_name"] == "Client Organization"

    accounts_after = client.get("/v1/partners/current/accounts", headers=WRITE_HEADERS)
    assert accounts_after.status_code == 200
    assert accounts_after.json()["total"] == 1


def test_idempotency_replays_create_agent() -> None:
    client = TestClient(app)
    payload = {
        "name": "Front Desk",
        "template_id": "tpl_receptionist_booking_v1",
        "timezone": "Asia/Almaty",
        "default_language": "ru",
        "business_hours": {"mon_fri": ["09:00-18:00"]},
    }
    headers = {**WRITE_HEADERS, "Idempotency-Key": "idem-agent-1"}
    first = client.post("/v1/agents", json=payload, headers=headers)
    assert first.status_code == 200
    second = client.post("/v1/agents", json=payload, headers=headers)
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]

    listed = client.get("/v1/agents", headers=WRITE_HEADERS)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1


def test_idempotency_conflict_returns_409() -> None:
    client = TestClient(app)
    payload = {
        "name": "Front Desk",
        "template_id": "tpl_receptionist_booking_v1",
        "timezone": "Asia/Almaty",
        "default_language": "ru",
        "business_hours": {"mon_fri": ["09:00-18:00"]},
    }
    headers = {**WRITE_HEADERS, "Idempotency-Key": "idem-agent-2"}
    first = client.post("/v1/agents", json=payload, headers=headers)
    assert first.status_code == 200

    conflicting = client.post(
        "/v1/agents",
        json={**payload, "name": "Different"},
        headers=headers,
    )
    assert conflicting.status_code == 409
    assert conflicting.json()["error"]["code"] == "idempotency_conflict"


def test_idempotency_required_on_create_agent() -> None:
    client = TestClient(app)
    payload = {
        "name": "Front Desk",
        "template_id": "tpl_receptionist_booking_v1",
        "timezone": "Asia/Almaty",
        "default_language": "ru",
        "business_hours": {"mon_fri": ["09:00-18:00"]},
    }
    response = client.post("/v1/agents", json=payload, headers=WRITE_HEADERS)
    assert response.status_code == 428
    assert response.json()["error"]["code"] == "idempotency_required"


def test_agents_pagination() -> None:
    client = TestClient(app)
    payload = {
        "name": "Front Desk",
        "template_id": "tpl_receptionist_booking_v1",
        "timezone": "Asia/Almaty",
        "default_language": "ru",
        "business_hours": {"mon_fri": ["09:00-18:00"]},
    }
    for i in range(3):
        client.post(
            "/v1/agents",
            json={**payload, "name": f"Front Desk {i}"},
            headers=with_idempotency(WRITE_HEADERS, f"idem-agent-page-{i}"),
        )

    page1 = client.get("/v1/agents?limit=2&offset=0", headers=WRITE_HEADERS)
    assert page1.status_code == 200
    assert page1.json()["total"] == 3
    assert len(page1.json()["items"]) == 2

    page2 = client.get("/v1/agents?limit=2&offset=2", headers=WRITE_HEADERS)
    assert page2.status_code == 200
    assert page2.json()["total"] == 3
    assert len(page2.json()["items"]) == 1
