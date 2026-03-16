# VoiceAgent Provider Adapter Interface v1

Дата: 9 марта 2026

## Цель

Зафиксировать единый контракт между ядром платформы и внешними провайдерами, чтобы:

- избежать vendor lock-in
- поддерживать OSS и hosted editions
- собирать одинаковые telemetry/cost/error данные по всем интеграциям

## 1. Общие требования ко всем адаптерам

Каждый адаптер обязан:

- иметь provider id и version metadata
- отдавать structured success/error responses
- возвращать `latency_ms` и cost metadata где применимо
- поддерживать timeout и retry policy
- логировать `trace_id`

## 2. Telephony Adapter

Ответственность:

- receive inbound call events
- initiate outbound calls
- transfer calls
- hang up calls
- emit media/session state

Минимальный интерфейс:

```text
start_session(call_context) -> TelephonySession
transfer_call(session_id, target) -> TransferResult
end_call(session_id) -> EndCallResult
get_capabilities() -> TelephonyCapabilities
```

Критичные поля результата:

- `provider_call_id`
- `session_id`
- `latency_ms`
- `status`
- `error_category`

## 3. STT Adapter

Ответственность:

- преобразование аудио в текст
- partial/final transcript support where available

Минимальный интерфейс:

```text
transcribe_chunk(audio_chunk, session_context) -> PartialTranscript
finalize_transcript(session_context) -> FinalTranscript
get_capabilities() -> STTCapabilities
```

Критичные поля:

- `text`
- `confidence`
- `is_final`
- `latency_ms`

## 4. TTS Adapter

Ответственность:

- генерация аудиоответа

Минимальный интерфейс:

```text
synthesize(text, voice_config, session_context) -> AudioResult
get_capabilities() -> TTSCapabilities
```

Критичные поля:

- `audio_ref`
- `duration_ms`
- `latency_ms`

## 5. LLM Adapter

Ответственность:

- reasoning / response generation
- tool-call decisioning
- structured output support

Минимальный интерфейс:

```text
generate_turn(turn_input, agent_policy, tool_catalog) -> TurnDecision
summarize_call(call_context) -> CallSummary
get_capabilities() -> LLMCapabilities
```

`TurnDecision` должен включать:

- `assistant_text`
- `tool_calls`
- `finish_reason`
- `tokens_in`
- `tokens_out`
- `latency_ms`

## 6. Calendar Adapter

Ответственность:

- lookup slots
- create booking
- update/cancel booking

Минимальный интерфейс:

```text
lookup_slots(query) -> SlotListResult
create_booking(request) -> BookingResult
update_booking(request) -> BookingResult
```

## 7. CRM Adapter

Ответственность:

- create/update contact
- create/update lead
- attach call summary

Минимальный интерфейс:

```text
upsert_contact(contact_payload) -> ContactResult
upsert_lead(lead_payload) -> LeadResult
attach_call_summary(summary_payload) -> SyncResult
```

## 8. Messaging Adapter

Ответственность:

- отправка подтверждений и напоминаний

Минимальный интерфейс:

```text
send_message(message_payload) -> DeliveryResult
```

## 9. Billing Adapter

Ответственность:

- синхронизация subscription state
- portal/licensing hooks
- webhook validation

Минимальный интерфейс:

```text
validate_webhook(signature, payload) -> ValidationResult
sync_subscription(event_payload) -> SubscriptionSyncResult
resolve_license(license_key) -> LicenseResult
```

## 10. Unified Error Shape

Каждый адаптер должен возвращать ошибки в виде:

```json
{
  "status": "error",
  "error": {
    "category": "integration",
    "code": "provider_timeout",
    "message": "Provider timed out",
    "retryable": true
  },
  "latency_ms": 3000,
  "trace_id": "trc_123"
}
```

Категории:

- `auth`
- `quota`
- `timeout`
- `validation`
- `provider`
- `internal`

## 11. Implementation Rule

Ни один adapter не должен протаскивать vendor-specific payload глубоко в core domain.

В core остаются только:

- normalized requests
- normalized responses
- normalized telemetry
