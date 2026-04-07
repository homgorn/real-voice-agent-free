# API Quickstart

VoiceAgent exposes an API-first backend for agents, calls, bookings, integrations, and operator workflows.

## Base Requirements

- Bearer token in `Authorization`
- `Idempotency-Key` on all POST and PATCH mutations
- JSON request and response bodies

## 1. Create an Agent

```bash
curl -X POST http://localhost:8000/v1/agents   -H "Authorization: Bearer dev-secret-key"   -H "Idempotency-Key: agent-001"   -H "Content-Type: application/json"   -d '{
    "name": "Front Desk",
    "template_id": "tpl_receptionist_booking_v1",
    "timezone": "Asia/Almaty",
    "default_language": "ru",
    "business_hours": {"mon_fri": ["09:00-18:00"]}
  }'
```

## 2. Publish the Agent

```bash
curl -X POST http://localhost:8000/v1/agents/{agent_id}/publish   -H "Authorization: Bearer dev-secret-key"   -H "Idempotency-Key: publish-001"   -H "Content-Type: application/json"   -d '{"target_environment": "production"}'
```

## 3. Inspect Scheduling Availability

```bash
curl "http://localhost:8000/v1/agents/{agent_id}/availability?days=5&limit=8"   -H "Authorization: Bearer dev-secret-key"
```

## 4. Create a Call and Respond

```bash
curl -X POST http://localhost:8000/v1/calls   -H "Authorization: Bearer dev-secret-key"   -H "Idempotency-Key: call-001"   -H "Content-Type: application/json"   -d '{
    "agent_id": "agt_xxx",
    "direction": "inbound",
    "from_number": "+77011234567",
    "to_number": "+77021234567"
  }'
```

```bash
curl -X POST http://localhost:8000/v1/calls/{call_id}/respond   -H "Authorization: Bearer dev-secret-key"   -H "Idempotency-Key: respond-001"   -H "Content-Type: application/json"   -d '{"input_text": "I want to book tomorrow after lunch", "voice_id": "alloy"}'
```

## 5. Create a Booking

```bash
curl -X POST http://localhost:8000/v1/bookings   -H "Authorization: Bearer dev-secret-key"   -H "Idempotency-Key: booking-001"   -H "Content-Type: application/json"   -d '{
    "agent_id": "agt_xxx",
    "contact_name": "Alina",
    "contact_phone": "+77011234567",
    "service": "consultation",
    "start_at": "2026-04-10T15:00:00+05:00"
  }'
```

## Next Reads

- [../USAGE.md](../USAGE.md)
- [control-plane.md](control-plane.md)
- [scheduling-and-bookings.md](scheduling-and-bookings.md)
