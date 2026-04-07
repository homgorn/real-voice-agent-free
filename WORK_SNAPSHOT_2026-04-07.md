# Work Snapshot — 2026-04-07 10:03:59 +06:00

## Snapshot Policy
- Отдельный Markdown snapshot я не сохраняю автоматически.
- Автоматически сохраняется только контекст диалога в сессии.
- По запросу я делаю явный snapshot-файл в репозитории.

## Completed Earlier Batches
- Усилен API key auth: `bcrypt` + обратная совместимость с legacy SHA-256 ключами и автоматическая миграция при первом использовании.
- Закрыта утечка webhook secret: secret возвращается только при создании webhook.
- Подключён OpenAI runtime для `STT/LLM/TTS` с env-конфигом, dependency и тестами.
- Runtime теперь передаёт в LLM недавнюю историю разговора.
- Добавлен backend dashboard summary: `GET /v1/dashboard/overview`.
- `apps/web` превращён из заглушки в операторский control plane: overview, onboarding, agents, calls, bookings, setup.
- README / docs / roadmap / context map уже частично синхронизированы под новый статус проекта.
- Лендинг не трогался.

## Current Batch In Progress
Цель текущего batch: перевести scheduling из декоративного режима в реальную бизнес-логику.

### Уже внесено в код текущего batch
- Добавлен setting `VOICEAGENT_BOOKING_SLOT_MINUTES`.
- Добавлен `BookingConflictError` для осмысленного `409 booking_conflict`.
- Добавлены схемы availability response.
- Добавлен новый route: `GET /v1/agents/{agent_id}/availability`.
- В `store.py` добавлена логика:
  - построение availability по `business_hours` агента;
  - исключение уже занятых слотов из availability;
  - блокировка double-booking при `create_booking`;
  - блокировка конфликтного reschedule/update при `update_booking`;
  - runtime tool execution для `calendar.lookup_slots` с возвратом реальных available slots.
- Переписывается control plane под новый flow:
  - `apps/web/api.js` — API client умеет запрашивать availability;
  - `apps/web/render.js` — рендер suggested slots и tool-call slot payload;
  - `apps/web/app.js` — operator flow для подстановки slot в booking form;
  - `apps/web/index.html` — booking availability pane и исправление битых строк.
- Обновляются тесты:
  - API regression на availability + double-booking conflict;
  - runtime expectations под executed tool calls.

## Important Current State
- Этот batch ещё **не прошёл финальную валидацию**.
- После текущих правок я ещё **не запускал повторно** `python -m ruff check .` и `python -m pytest -q`.
- Последний полностью зелёный статус был до этого batch: `ruff` и `pytest` были зелёными, `37` тестов проходили.

## Business Logic State Right Now
- Backend/platform skeleton уже сильный.
- Core product стал ближе к real scheduling flow.
- Самые крупные оставшиеся product gaps после этого batch всё ещё такие:
  - telephony ingress / media pipeline;
  - hosted-safe auth model для frontend;
  - реальные provider integrations beyond stubs;
  - deeper operator workflows и drill-down.

## Git Status At Snapshot Time
```text
## main...origin/main
 M .env.example
 M .gitignore
 M CONTEXT_MAP.md
 M README.md
 M ROADMAP.md
 M USAGE.md
 M alembic/env.py
 M alembic/versions/20260309_0001_create_agent_tables.py
 M alembic/versions/20260309_0002_add_bookings_events_webhooks.py
 M alembic/versions/20260309_0003_add_calls_tables.py
 M alembic/versions/20260310_0004_add_organizations_and_api_keys.py
 M alembic/versions/20260310_0005_add_org_scoping_columns.py
 M alembic/versions/20260310_0006_add_billing_tables.py
 M alembic/versions/20260310_0007_add_webhook_retry_state.py
 M alembic/versions/20260310_0008_add_runtime_turn_fields.py
 M apps/api/src/voiceagent_api/adapters/llm.py
 M apps/api/src/voiceagent_api/adapters/stt.py
 M apps/api/src/voiceagent_api/adapters/tts.py
 M apps/api/src/voiceagent_api/app.py
 M apps/api/src/voiceagent_api/auth.py
 M apps/api/src/voiceagent_api/config.py
 M apps/api/src/voiceagent_api/errors.py
 M apps/api/src/voiceagent_api/middleware.py
 M apps/api/src/voiceagent_api/models.py
 M apps/api/src/voiceagent_api/routers/_helpers.py
 M apps/api/src/voiceagent_api/routers/agents.py
 M apps/api/src/voiceagent_api/routers/api_keys.py
 M apps/api/src/voiceagent_api/routers/billing.py
 M apps/api/src/voiceagent_api/routers/bookings.py
 M apps/api/src/voiceagent_api/routers/calls.py
 M apps/api/src/voiceagent_api/routers/events.py
 M apps/api/src/voiceagent_api/routers/health.py
 M apps/api/src/voiceagent_api/routers/integrations.py
 M apps/api/src/voiceagent_api/routers/knowledge_bases.py
 M apps/api/src/voiceagent_api/routers/partners.py
 M apps/api/src/voiceagent_api/routers/phone_numbers.py
 M apps/api/src/voiceagent_api/routers/webhooks.py
 M apps/api/src/voiceagent_api/runtime.py
 M apps/api/src/voiceagent_api/schemas.py
 M apps/api/src/voiceagent_api/store.py
 M apps/api/src/voiceagent_api/worker.py
 M apps/web/README.md
 M pyproject.toml
 M tests/load_test.py
 M tests/test_api.py
 M tests/test_runtime.py
 M tests/test_worker.py
?? apps/api/src/voiceagent_api/adapters/openai_client.py
?? apps/api/src/voiceagent_api/routers/dashboard.py
?? apps/web/api.js
?? apps/web/app.js
?? apps/web/index.html
?? apps/web/render.js
?? apps/web/styles.css
?? chatlogs-07.04.2026.txt
?? real-voice-agent-free-main070426-60procentov.zip
```

## Next Safe Step After This Snapshot
- Довести текущий scheduling batch до конца.
- Прогнать `python -m ruff check .`.
- Прогнать `python -m pytest -q`.
- После этого обновить docs под final state batch.
