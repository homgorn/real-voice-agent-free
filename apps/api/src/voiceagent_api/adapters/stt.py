from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


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


def get_stt_adapter() -> STTAdapter:
    return StubSTTAdapter()
