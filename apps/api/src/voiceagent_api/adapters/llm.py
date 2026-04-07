from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Protocol

from voiceagent_api.adapters.openai_client import get_openai_client, openai_enabled
from voiceagent_api.config import settings
from voiceagent_api.errors import UpstreamServiceError


@dataclass(slots=True)
class TurnGenerateRequest:
    call_id: str
    agent_id: str
    turn_index: int
    user_text: str
    trace_id: str
    conversation_history: list[dict[str, str]]


@dataclass(slots=True)
class TurnGenerateResult:
    provider: str
    assistant_text: str
    tool_calls: list[dict]
    finish_reason: str
    tokens_in: int
    tokens_out: int
    latency_ms: int


class LLMAdapter(Protocol):
    def generate_turn(self, request: TurnGenerateRequest) -> TurnGenerateResult: ...


class StubLLMAdapter:
    def generate_turn(self, request: TurnGenerateRequest) -> TurnGenerateResult:
        normalized = request.user_text.lower()
        tool_calls = infer_tool_calls(normalized)

        if tool_calls:
            assistant_text = "Могу помочь с записью. Назовите удобные дату и время."
        elif any(keyword in normalized for keyword in ("цен", "price", "стоим")):
            assistant_text = "Подскажу по стоимости. Уточните, какая именно услуга вас интересует."
        else:
            assistant_text = "Понял. Уточните, пожалуйста, детали запроса, и я продолжу."

        return TurnGenerateResult(
            provider="stub-llm",
            assistant_text=assistant_text,
            tool_calls=tool_calls,
            finish_reason="completed",
            tokens_in=max(8, len(request.user_text.split()) * 4),
            tokens_out=max(12, len(assistant_text.split()) * 5),
            latency_ms=180,
        )


class OpenAILLMAdapter:
    def generate_turn(self, request: TurnGenerateRequest) -> TurnGenerateResult:
        normalized = request.user_text.lower()
        started_at = perf_counter()
        client = get_openai_client()
        instructions = build_llm_instructions()
        try:
            response = client.responses.create(
                model=settings.openai_llm_model,
                instructions=instructions,
                input=build_llm_input(request),
                temperature=settings.openai_llm_temperature,
            )
        except Exception as exc:
            raise UpstreamServiceError(f"OpenAI text generation failed: {exc}") from exc

        assistant_text = (getattr(response, "output_text", "") or "").strip()
        if not assistant_text:
            raise UpstreamServiceError("OpenAI response returned empty output")
        usage = getattr(response, "usage", None)
        latency_ms = max(1, int((perf_counter() - started_at) * 1000))
        return TurnGenerateResult(
            provider=f"openai:{settings.openai_llm_model}",
            assistant_text=assistant_text,
            tool_calls=infer_tool_calls(normalized),
            finish_reason="completed",
            tokens_in=int(getattr(usage, "input_tokens", 0) or 0),
            tokens_out=int(getattr(usage, "output_tokens", 0) or 0),
            latency_ms=latency_ms,
        )


def infer_tool_calls(normalized_text: str) -> list[dict]:
    if any(keyword in normalized_text for keyword in ("запис", "appointment", "book", "slot", "calendar")):
        return [{"tool_name": "calendar.lookup_slots", "status": "planned"}]
    return []


def build_llm_instructions() -> str:
    return (
        "You are VoiceAgent, a phone assistant for SMB service businesses. "
        "Reply conversationally, keep answers short, avoid markdown, and ask only the next needed question. "
        "Use the provided conversation history to maintain context and avoid repeating questions. "
        "If the caller wants to book, reschedule, or check availability, guide them toward a date and time. "
        "If the user asks about price, answer briefly and ask one clarifying follow-up if needed."
    )


def build_llm_input(request: TurnGenerateRequest) -> str:
    history_lines: list[str] = []
    for message in request.conversation_history[-12:]:
        role = message.get("role", "user").strip() or "user"
        text = message.get("text", "").strip()
        if text:
            history_lines.append(f"{role.title()}: {text}")

    if not history_lines:
        return request.user_text

    history_block = "\n".join(history_lines)
    return f"Conversation history:\n{history_block}\nCurrent caller message:\n{request.user_text}"


def get_llm_adapter() -> LLMAdapter:
    if openai_enabled():
        return OpenAILLMAdapter()
    return StubLLMAdapter()
