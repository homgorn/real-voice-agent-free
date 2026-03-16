from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import uuid4

from voiceagent_api.config import settings


@dataclass(slots=True)
class SynthesisRequest:
    call_id: str
    trace_id: str
    text: str
    voice_id: str | None = None


@dataclass(slots=True)
class SynthesisResult:
    provider: str
    audio_ref: str
    duration_ms: int
    latency_ms: int


class TTSAdapter(Protocol):
    def synthesize(self, request: SynthesisRequest) -> SynthesisResult: ...


class StubTTSAdapter:
    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        voice_id = request.voice_id or settings.runtime_default_voice_id
        suffix = uuid4().hex[:8]
        return SynthesisResult(
            provider="stub-tts",
            audio_ref=f"tts_{request.call_id}_{voice_id}_{suffix}",
            duration_ms=max(500, len(request.text) * 45),
            latency_ms=90,
        )


def get_tts_adapter() -> TTSAdapter:
    return StubTTSAdapter()
