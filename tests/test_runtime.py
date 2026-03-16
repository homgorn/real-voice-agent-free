from __future__ import annotations

from fastapi.testclient import TestClient

from voiceagent_api.app import app
from voiceagent_api.store import store

WRITE_HEADERS = {"Authorization": "Bearer dev-secret-key"}


def setup_function() -> None:
    store.reset()


def _create_agent_and_call(client: TestClient) -> str:
    agent = client.post(
        "/v1/agents",
        json={
            "name": "Front Desk",
            "template_id": "tpl_receptionist_booking_v1",
            "timezone": "Asia/Almaty",
            "default_language": "ru",
            "business_hours": {"mon_fri": ["09:00-18:00"]},
        },
        headers=WRITE_HEADERS,
    )
    agent_id = agent.json()["id"]
    call = client.post(
        "/v1/calls",
        json={
            "agent_id": agent_id,
            "direction": "inbound",
            "from_number": "+77011234567",
            "to_number": "+77021234567",
        },
        headers=WRITE_HEADERS,
    )
    return call.json()["id"]


def test_runtime_respond_creates_turn_from_text_input() -> None:
    client = TestClient(app)
    call_id = _create_agent_and_call(client)

    response = client.post(
        f"/v1/calls/{call_id}/respond",
        json={"input_text": "Хочу записаться на завтра", "voice_id": "nova"},
        headers=WRITE_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user_text"] == "Хочу записаться на завтра"
    assert "запись" in body["assistant_text"].lower()
    assert body["response_audio_ref"].startswith(f"tts_{call_id}_nova_")
    assert body["finish_reason"] == "completed"
    assert body["provider_breakdown"]["stt_provider"] == "stub-stt"
    assert body["provider_breakdown"]["llm_provider"] == "stub-llm"
    assert body["provider_breakdown"]["tts_provider"] == "stub-tts"

    turns = client.get(f"/v1/calls/{call_id}/turns", headers=WRITE_HEADERS)
    assert turns.status_code == 200
    assert turns.json()["total"] == 1
    assert turns.json()["items"][0]["response_audio_ref"] == body["response_audio_ref"]


def test_runtime_respond_transcribes_audio_reference() -> None:
    client = TestClient(app)
    call_id = _create_agent_and_call(client)

    response = client.post(
        f"/v1/calls/{call_id}/respond",
        json={"audio_ref": "recordings/chunk-001.wav"},
        headers=WRITE_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user_text"] == "Transcript from recordings/chunk-001.wav"
    assert body["latency_ms"] == 390
    assert body["provider_breakdown"]["stt_ms"] == 120
    assert body["provider_breakdown"]["llm_ms"] == 180
    assert body["provider_breakdown"]["tts_ms"] == 90
