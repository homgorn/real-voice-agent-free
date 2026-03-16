# VoiceAgent Event Schema v1

Дата: 9 марта 2026

## Цель

Сделать единый event contract между execution plane, control plane, integrations и partner/billing контуром.

## 1. Event Envelope

```json
{
  "event_id": "uuid",
  "event_type": "call.started",
  "event_version": "v1",
  "occurred_at": "2026-03-09T12:00:00Z",
  "trace_id": "uuid",
  "tenant_id": "org_123",
  "source": "runtime",
  "payload": {}
}
```

Обязательные поля:

- `event_id`
- `event_type`
- `event_version`
- `occurred_at`
- `trace_id`
- `tenant_id`
- `source`
- `payload`

## 2. Event Types (MVP)

1. `call.started`
2. `call.turn.completed`
3. `call.escalated`
4. `call.ended`
5. `call.failed`
6. `booking.created`
7. `booking.updated`
8. `lead.captured`
9. `agent.published`
10. `integration.failed`
11. `subscription.activated`
12. `subscription.canceled`
13. `license.validated`
14. `partner.referral.created`
15. `webhook.test`

## 3. call.started

```json
{
  "call_id": "call_123",
  "agent_id": "agt_123",
  "phone_number_id": "num_123",
  "channel": "voice",
  "direction": "inbound",
  "from": "+7701xxxxxxx",
  "to": "+7702xxxxxxx"
}
```

Validation:

- `direction` in `inbound|outbound`
- `call_id` required

## 4. call.turn.completed

```json
{
  "call_id": "call_123",
  "turn_index": 3,
  "user_text": "Запишите меня на завтра",
  "assistant_text": "Подскажите удобное время",
  "latency_ms": 912,
  "provider_breakdown": {
    "stt_ms": 180,
    "llm_ms": 420,
    "tts_ms": 210
  },
  "tool_calls": [
    {
      "tool_name": "calendar.lookup_slots",
      "status": "ok"
    }
  ]
}
```

Validation:

- `turn_index` >= 0
- `latency_ms` >= 0

## 5. call.escalated

```json
{
  "call_id": "call_123",
  "reason": "human_requested",
  "target": "operator_queue",
  "summary": "Клиент хочет поговорить с администратором"
}
```

## 6. call.ended

```json
{
  "call_id": "call_123",
  "duration_ms": 183000,
  "outcome": "booking_created",
  "cost": {
    "currency": "USD",
    "amount": "0.42"
  },
  "recording_available": true
}
```

Validation:

- `outcome` in `faq_resolved|booking_created|escalated|lead_captured|abandoned|failed`

## 7. call.failed

```json
{
  "call_id": "call_123",
  "category": "stt",
  "code": "provider_timeout",
  "message": "STT provider timed out after 3 attempts"
}
```

Validation:

- `category` in `telephony|stt|tts|llm|tool|integration|internal`

## 8. booking.created

```json
{
  "booking_id": "bk_123",
  "call_id": "call_123",
  "contact": {
    "name": "Алина",
    "phone": "+7701xxxxxxx"
  },
  "service": "consultation",
  "start_at": "2026-03-10T15:00:00+05:00"
}
```

## 9. lead.captured

```json
{
  "lead_id": "lead_123",
  "call_id": "call_123",
  "contact": {
    "name": "Нурсултан",
    "phone": "+7707xxxxxxx"
  },
  "interest": "dental cleaning"
}
```

## 10. agent.published

```json
{
  "agent_id": "agt_123",
  "version_id": "ver_007",
  "environment": "production",
  "published_by": "usr_123"
}
```

## 11. Billing / Partner Events

### subscription.activated

```json
{
  "subscription_id": "sub_123",
  "plan_code": "pro_growth",
  "billing_provider": "lemonsqueezy"
}
```

### partner.referral.created

```json
{
  "partner_id": "prt_123",
  "referral_id": "ref_123",
  "referred_account_id": "org_987"
}
```

### webhook.test

```json
{
  "webhook_id": "wh_123",
  "target_url": "https://example.com/webhooks/voiceagent"
}
```
