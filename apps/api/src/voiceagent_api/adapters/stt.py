from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Protocol

from voiceagent_api.adapters.openai_client import get_openai_client, openai_enabled
from voiceagent_api.config import settings
from voiceagent_api.errors import NotFoundError, UpstreamServiceError


@dataclass(slots=True)
class TranscriptionRequest:
    call_id: str
    trace_id: str
    input_text: str | None = None
    audio_ref: str | None = None


@dataclass(slots=True)
class TranscriptionResult:
    provider: str
    text: str
    confidence: float
    is_final: bool
    latency_ms: int


class STTAdapter(Protocol):
    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult: ...


class StubSTTAdapter:
    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        if request.input_text:
            return TranscriptionResult(
                provider="stub-stt",
                text=request.input_text,
                confidence=1.0,
                is_final=True,
                latency_ms=5,
            )
        return TranscriptionResult(
            provider="stub-stt",
            text=f"Transcript from {request.audio_ref}",
            confidence=0.92,
            is_final=True,
            latency_ms=120,
        )


class OpenAISTTAdapter:
    def transcribe(self, request: TranscriptionRequest) -> TranscriptionResult:
        if request.input_text:
            return TranscriptionResult(
                provider="text-input",
                text=request.input_text,
                confidence=1.0,
                is_final=True,
                latency_ms=1,
            )
        if not request.audio_ref:
            raise UpstreamServiceError("Audio transcription requires audio_ref")

        audio_path = self._resolve_audio_path(request.audio_ref)
        started_at = perf_counter()
        client = get_openai_client()
        try:
            with audio_path.open("rb") as audio_file:
                response = client.audio.transcriptions.create(
                    file=audio_file,
                    model=settings.openai_stt_model,
                    response_format="text",
                )
        except Exception as exc:
            raise UpstreamServiceError(f"OpenAI transcription failed: {exc}") from exc

        text = response if isinstance(response, str) else getattr(response, "text", "")
        text = text.strip()
        if not text:
            raise UpstreamServiceError("OpenAI transcription returned empty text")
        latency_ms = max(1, int((perf_counter() - started_at) * 1000))
        return TranscriptionResult(
            provider=f"openai:{settings.openai_stt_model}",
            text=text,
            confidence=0.0,
            is_final=True,
            latency_ms=latency_ms,
        )

    def _resolve_audio_path(self, audio_ref: str) -> Path:
        normalized = audio_ref.removeprefix("file://")
        path = Path(normalized).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path
        if not path.exists() or not path.is_file():
            raise NotFoundError(f"Audio file not found: {audio_ref}")
        return path


def get_stt_adapter() -> STTAdapter:
    if openai_enabled():
        return OpenAISTTAdapter()
    return StubSTTAdapter()
