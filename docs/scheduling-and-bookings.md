# Scheduling and Bookings

VoiceAgent now includes backend scheduling logic that is directly useful for appointment-driven businesses.

## What It Does

- calculates agent availability from `business_hours`
- returns suggested slots through `GET /v1/agents/{agent_id}/availability`
- excludes already booked slots from the returned availability
- blocks double-booking during booking creation
- blocks conflicting booking updates and reschedules
- exposes slot suggestions in the control plane and in runtime tool execution

## Main Endpoint

```bash
curl "http://localhost:8000/v1/agents/{agent_id}/availability?days=5&limit=8"   -H "Authorization: Bearer dev-secret-key"
```

## Booking Conflict Behavior

When a requested slot overlaps an already confirmed or rescheduled booking, the API returns `409 booking_conflict`.

This matters because scheduling logic should live in the backend, not only in the UI.

## Runtime Integration

If the LLM infers `calendar.lookup_slots`, VoiceAgent executes the lookup and records available slots in the call turn payload.

## Related Docs

- [api-quickstart.md](api-quickstart.md)
- [control-plane.md](control-plane.md)
- [../USAGE.md](../USAGE.md)
