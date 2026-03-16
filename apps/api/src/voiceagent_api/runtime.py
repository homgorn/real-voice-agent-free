from __future__ import annotations

from dataclasses import dataclass

from voiceagent_api.adapters.llm import TurnGenerateRequest, get_llm_adapter
from voiceagent_api.adapters.stt import TranscriptionRequest, get_stt_adapter
from voiceagent_api.adapters.tts import SynthesisRequest, get_tts_adapter
from voiceagent_api.config import settings


@dataclass(slots=True)
class RuntimeTurnRequest:
    call_id: str
    agent_id: str
    turn_index: int
    trace_id: str
    input_text: str | None = None
    audio_ref: str | None = None
    voice_id: str | None = None


@dataclass(slots=True)
class RuntimeTurnResult:
    user_text: str
    assistant_text: str
    latency_ms: int
    provider_breakdown: dict
    tool_calls: list[dict]
    response_audio_ref: str
    finish_reason: str


class CallRuntimeOrchestrator:
    def __init__(self) -> None:
        self.stt_adapter = get_stt_adapter()
        self.llm_adapter = get_llm_adapter()
        self.tts_adapter = get_tts_adapter()

    def respond(self, request: RuntimeTurnRequest) -> RuntimeTurnResult:
        transcription = self.stt_adapter.transcribe(
            TranscriptionRequest(
                call_id=request.call_id,
                trace_id=request.trace_id,
                input_text=request.input_text,
                audio_ref=request.audio_ref,
            )
        )
        decision = self.llm_adapter.generate_turn(
            TurnGenerateRequest(
                call_id=request.call_id,
                agent_id=request.agent_id,
                turn_index=request.turn_index,
                user_text=transcription.text,
                trace_id=request.trace_id,
            )
        )
        synthesis = self.tts_adapter.synthesize(
            SynthesisRequest(
                call_id=request.call_id,
                trace_id=request.trace_id,
                text=decision.assistant_text,
                voice_id=request.voice_id or settings.runtime_default_voice_id,
            )
        )
        return RuntimeTurnResult(
            user_text=transcription.text,
            assistant_text=decision.assistant_text,
            latency_ms=transcription.latency_ms + decision.latency_ms + synthesis.latency_ms,
            provider_breakdown={
                "stt_ms": transcription.latency_ms,
                "llm_ms": decision.latency_ms,
                "tts_ms": synthesis.latency_ms,
                "stt_provider": transcription.provider,
                "llm_provider": decision.provider,
                "tts_provider": synthesis.provider,
                "stt_confidence": transcription.confidence,
                "tokens_in": decision.tokens_in,
                "tokens_out": decision.tokens_out,
                "tts_audio_ref": synthesis.audio_ref,
            },
            tool_calls=decision.tool_calls,
            response_audio_ref=synthesis.audio_ref,
            finish_reason=decision.finish_reason,
        )


runtime_orchestrator = CallRuntimeOrchestrator()
