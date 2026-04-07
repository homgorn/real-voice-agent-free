from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Protocol
from uuid import uuid4

from voiceagent_api.adapters.openai_client import get_openai_client, openai_enabled
from voiceagent_api.config import settings
from voiceagent_api.errors import UpstreamServiceError


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


class OpenAITTSAdapter:
    def synthesize(self, request: SynthesisRequest) -> SynthesisResult:
        voice_id = request.voice_id or settings.runtime_default_voice_id
        audio_dir = Path(settings.runtime_audio_dir)
        audio_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"tts_{request.call_id}_{voice_id}_{uuid4().hex[:8]}.{settings.openai_tts_response_format}"
        output_path = audio_dir / file_name
        started_at = perf_counter()
        client = get_openai_client()
        try:
            with client.audio.speech.with_streaming_response.create(
                model=settings.openai_tts_model,
                voice=voice_id,
                input=request.text,
                instructions=settings.openai_tts_instructions,
                response_format=settings.openai_tts_response_format,
            ) as response:
                response.stream_to_file(output_path)
        except Exception as exc:
            raise UpstreamServiceError(f"OpenAI speech synthesis failed: {exc}") from exc

        latency_ms = max(1, int((perf_counter() - started_at) * 1000))
        return SynthesisResult(
            provider=f"openai:{settings.openai_tts_model}",
            audio_ref=str(output_path),
            duration_ms=max(500, len(request.text) * 45),
            latency_ms=latency_ms,
        )


def get_tts_adapter() -> TTSAdapter:
    if openai_enabled():
        return OpenAITTSAdapter()
    return StubTTSAdapter()
