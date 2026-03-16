from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import uuid4


@dataclass(slots=True)
class CalendarBookingRequest:
    agent_id: str
    contact_name: str
    contact_phone: str
    service: str
    start_at: datetime


@dataclass(slots=True)
class CalendarBookingResult:
    external_booking_id: str
    status: str


@dataclass(slots=True)
class CalendarBookingUpdateRequest:
    agent_id: str
    external_booking_id: str | None
    contact_name: str
    contact_phone: str
    service: str
    start_at: datetime
    status: str | None = None


class CalendarAdapter(Protocol):
    def create_booking(self, request: CalendarBookingRequest) -> CalendarBookingResult: ...
    def update_booking(self, request: CalendarBookingUpdateRequest) -> CalendarBookingResult: ...


class StubCalendarAdapter:
    """Local adapter used until a real calendar provider is wired in."""

    def create_booking(self, request: CalendarBookingRequest) -> CalendarBookingResult:
        suffix = uuid4().hex[:10]
        return CalendarBookingResult(
            external_booking_id=f"cal_{request.agent_id}_{suffix}",
            status="confirmed",
        )

    def update_booking(self, request: CalendarBookingUpdateRequest) -> CalendarBookingResult:
        external_id = request.external_booking_id
        if not external_id:
            suffix = uuid4().hex[:10]
            external_id = f"cal_{request.agent_id}_{suffix}"
        return CalendarBookingResult(
            external_booking_id=external_id,
            status=request.status or "confirmed",
        )


def get_calendar_adapter() -> CalendarAdapter:
    return StubCalendarAdapter()
