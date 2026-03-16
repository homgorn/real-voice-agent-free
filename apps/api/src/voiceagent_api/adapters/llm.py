from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(slots=True)
class TurnGenerateRequest:
    call_id: str
    agent_id: str
    turn_index: int
    user_text: str
    trace_id: str


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
        tool_calls: list[dict] = []

        if any(keyword in normalized for keyword in ("запис", "appointment", "book", "slot")):
            assistant_text = "Могу помочь с записью. Назовите удобные дату и время."
            tool_calls = [{"tool_name": "calendar.lookup_slots", "status": "planned"}]
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


def get_llm_adapter() -> LLMAdapter:
    return StubLLMAdapter()
