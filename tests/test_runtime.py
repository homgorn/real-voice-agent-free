from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
from voiceagent_api.adapters.openai_client import reset_openai_client
from voiceagent_api.app import app
from voiceagent_api.config import settings
from voiceagent_api.store import store

WRITE_HEADERS = {"Authorization": "Bearer dev-secret-key"}


def setup_function() -> None:
    store.reset()
    reset_openai_client()
    settings.openai_api_key = ""
    settings.runtime_audio_dir = "runtime_audio"


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
        headers={**WRITE_HEADERS, "Idempotency-Key": "rt-agent-1"},
    )
    assert agent.status_code == 200, f"Failed to create agent: {agent.json()}"
    agent_id = agent.json()["id"]
    call = client.post(
        "/v1/calls",
        json={
            "agent_id": agent_id,
            "direction": "inbound",
            "from_number": "+77011234567",
            "to_number": "+77021234567",
        },
        headers={**WRITE_HEADERS, "Idempotency-Key": "rt-call-1"},
    )
    assert call.status_code == 200, f"Failed to create call: {call.json()}"
    return call.json()["id"]


def test_runtime_respond_creates_turn_from_text_input() -> None:
    client = TestClient(app)
    call_id = _create_agent_and_call(client)

    response = client.post(
        f"/v1/calls/{call_id}/respond",
        json={"input_text": "Хочу записаться на завтра", "voice_id": "nova"},
        headers={**WRITE_HEADERS, "Idempotency-Key": "rt-respond-1"},
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
    assert body["tool_calls"][0]["status"] == "completed"
    assert body["tool_calls"][0]["available_slots"]
    assert "Ближайшие окна" in body["assistant_text"]

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
        headers={**WRITE_HEADERS, "Idempotency-Key": "rt-respond-2"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["user_text"] == "Transcript from recordings/chunk-001.wav"
    assert body["latency_ms"] == 390
    assert body["provider_breakdown"]["stt_ms"] == 120
    assert body["provider_breakdown"]["llm_ms"] == 180
    assert body["provider_breakdown"]["tts_ms"] == 90


def test_runtime_respond_uses_openai_providers_when_configured(monkeypatch) -> None:
    class FakeTranscriptions:
        def create(self, *, file, model, response_format):
            assert model == settings.openai_stt_model
            assert response_format == "text"
            assert file.read() == b"RIFFfakewav"
            file.seek(0)
            return "Нужно записаться к стоматологу"

    class FakeSpeechResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def stream_to_file(self, path):
            Path(path).write_bytes(b"ID3fake")

    class FakeSpeechStreaming:
        def create(self, *, model, voice, input, instructions, response_format):
            assert model == settings.openai_tts_model
            assert voice == "cedar"
            assert response_format == settings.openai_tts_response_format
            assert "Speak clearly" in instructions
            assert "запись" in input.lower()
            return FakeSpeechResponse()

    class FakeResponses:
        def create(self, *, model, instructions, input, temperature):
            assert model == settings.openai_llm_model
            assert temperature == settings.openai_llm_temperature
            assert "VoiceAgent" in instructions
            assert "стоматологу" in input.lower()
            return SimpleNamespace(
                output_text="Могу помочь с записью. Назовите удобные дату и время.",
                usage=SimpleNamespace(input_tokens=21, output_tokens=13),
            )

    class FakeSpeech:
        def __init__(self):
            self.with_streaming_response = FakeSpeechStreaming()

    class FakeAudio:
        def __init__(self):
            self.transcriptions = FakeTranscriptions()
            self.speech = FakeSpeech()

    class FakeClient:
        def __init__(self):
            self.audio = FakeAudio()
            self.responses = FakeResponses()

    fake_client = FakeClient()
    workspace_tmp_root = Path(".pytest-work")
    workspace_tmp_root.mkdir(exist_ok=True)
    audio_path = workspace_tmp_root / "sample-openai.wav"
    output_dir = workspace_tmp_root / "runtime-audio-openai"
    output_dir.mkdir(exist_ok=True)
    audio_path.write_bytes(b"RIFFfakewav")

    try:
        monkeypatch.setattr(settings, "openai_api_key", "test-openai-key")
        monkeypatch.setattr(settings, "runtime_audio_dir", str(output_dir))
        monkeypatch.setattr("voiceagent_api.adapters.stt.get_openai_client", lambda: fake_client)
        monkeypatch.setattr("voiceagent_api.adapters.llm.get_openai_client", lambda: fake_client)
        monkeypatch.setattr("voiceagent_api.adapters.tts.get_openai_client", lambda: fake_client)

        client = TestClient(app)
        call_id = _create_agent_and_call(client)
        response = client.post(
            f"/v1/calls/{call_id}/respond",
            json={"audio_ref": str(audio_path), "voice_id": "cedar"},
            headers={**WRITE_HEADERS, "Idempotency-Key": "rt-respond-openai-1"},
        )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["user_text"] == "Нужно записаться к стоматологу"
        assert body["provider_breakdown"]["stt_provider"] == f"openai:{settings.openai_stt_model}"
        assert body["provider_breakdown"]["llm_provider"] == f"openai:{settings.openai_llm_model}"
        assert body["provider_breakdown"]["tts_provider"] == f"openai:{settings.openai_tts_model}"
        assert body["provider_breakdown"]["tokens_in"] == 21
        assert body["provider_breakdown"]["tokens_out"] == 13
        assert body["tool_calls"][0]["tool_name"] == "calendar.lookup_slots"
        assert body["tool_calls"][0]["status"] == "completed"
        assert body["tool_calls"][0]["available_slots"]
        assert "Ближайшие окна" in body["assistant_text"]
        assert Path(body["response_audio_ref"]).exists()
        assert Path(body["response_audio_ref"]).parent == output_dir
        assert Path(body["response_audio_ref"]).suffix == ".mp3"
    finally:
        if audio_path.exists():
            audio_path.unlink()
        shutil.rmtree(output_dir, ignore_errors=True)

def test_runtime_respond_passes_recent_history_to_openai(monkeypatch) -> None:
    captured: dict[str, str] = {}

    class FakeSpeechResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def stream_to_file(self, path):
            Path(path).write_bytes(b"ID3history")

    class FakeSpeechStreaming:
        def create(self, *, model, voice, input, instructions, response_format):
            assert model == settings.openai_tts_model
            assert voice == "alloy"
            assert response_format == settings.openai_tts_response_format
            assert "день" in input.lower()
            return FakeSpeechResponse()

    class FakeResponses:
        def create(self, *, model, instructions, input, temperature):
            captured["input"] = input
            assert model == settings.openai_llm_model
            assert temperature == settings.openai_llm_temperature
            assert "maintain context" in instructions
            return SimpleNamespace(
                output_text="Понял. После обеда есть окна. Какой день вам подходит?",
                usage=SimpleNamespace(input_tokens=34, output_tokens=11),
            )

    class FakeSpeech:
        def __init__(self):
            self.with_streaming_response = FakeSpeechStreaming()

    class FakeAudio:
        def __init__(self):
            self.speech = FakeSpeech()

    class FakeClient:
        def __init__(self):
            self.audio = FakeAudio()
            self.responses = FakeResponses()

    output_dir = Path(".pytest-work") / "runtime-audio-history"
    output_dir.mkdir(parents=True, exist_ok=True)
    fake_client = FakeClient()

    try:
        client = TestClient(app)
        call_id = _create_agent_and_call(client)
        first_response = client.post(
            f"/v1/calls/{call_id}/respond",
            json={"input_text": "Хочу записаться на завтра"},
            headers={**WRITE_HEADERS, "Idempotency-Key": "rt-history-1"},
        )
        assert first_response.status_code == 200, first_response.text

        monkeypatch.setattr(settings, "openai_api_key", "test-openai-key")
        monkeypatch.setattr(settings, "runtime_audio_dir", str(output_dir))
        monkeypatch.setattr("voiceagent_api.adapters.llm.get_openai_client", lambda: fake_client)
        monkeypatch.setattr("voiceagent_api.adapters.tts.get_openai_client", lambda: fake_client)

        second_response = client.post(
            f"/v1/calls/{call_id}/respond",
            json={"input_text": "После обеда"},
            headers={**WRITE_HEADERS, "Idempotency-Key": "rt-history-2"},
        )

        assert second_response.status_code == 200, second_response.text
        body = second_response.json()
        assert body["provider_breakdown"]["stt_provider"] == "text-input"
        assert body["provider_breakdown"]["llm_provider"] == f"openai:{settings.openai_llm_model}"
        assert body["provider_breakdown"]["tts_provider"] == f"openai:{settings.openai_tts_model}"
        assert body["provider_breakdown"]["history_messages"] == 2
        assert "Хочу записаться на завтра" in captured["input"]
        assert "Назовите удобные дату и время" in captured["input"]
        assert "После обеда" in captured["input"]
    finally:
        shutil.rmtree(output_dir, ignore_errors=True)

