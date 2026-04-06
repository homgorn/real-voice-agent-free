# AGENTS.md — AI Agent Context File

## Project Overview
VoiceAgent is an open-source voice AI platform for SMB service businesses. It automates inbound calls, appointment scheduling, and customer support with AI phone agents.

## Architecture
- **Engine**: FastAPI app (`app.py`) with 14 domain routers under `routers/`
- **Services**: `store.py` is the monolithic service layer (2200+ lines, being refactored)
- **Adapters**: Provider pattern with `Protocol` interfaces for STT, TTS, LLM, Calendar
- **Database**: SQLAlchemy ORM with SQLite (dev) / PostgreSQL (prod)
- **Background**: Webhook delivery worker (`worker.py`) with polling and retry logic

## Key Patterns
- **Multi-tenant**: All resources scoped by `organization_id`
- **API Key Auth**: Bearer token with scope-based access control (`require_scope("resource:action")`)
- **Idempotency**: ALL POST/PATCH mutations require `Idempotency-Key` header (returns 428 if missing). Exceptions: GET, DELETE, /health, /ready
- **Event-driven**: All state changes emit events to `events` table, which trigger webhook deliveries
- **Provider adapters**: Protocol-based interfaces for STT, TTS, LLM, Calendar — stub implementations ready for real providers
- **Security headers**: HSTS, CSP, X-Frame-Options, X-Content-Type-Options enforced via middleware
- **CORS**: Strict in production (configurable via `VOICEAGENT_ALLOWED_ORIGINS`), wildcard in dev/test
- **Graceful lifecycle**: Lifespan pattern for startup/shutdown; skipped in test mode

## File Structure
```
apps/api/src/voiceagent_api/
├── app.py              # FastAPI engine with routers, middleware, exception handlers
├── config.py           # Pydantic Settings (all env vars with VOICEAGENT_ prefix)
├── db.py               # SQLAlchemy engine, session, create/close database
├── models.py           # SQLAlchemy ORM models (18 tables)
├── schemas.py          # Pydantic request/response schemas (60+ models)
├── store.py            # Service layer (all business logic, ~2200 lines)
├── auth.py             # API key authentication with bcrypt, scope enforcement
├── errors.py           # Custom exception hierarchy (VoiceAgentError base)
├── worker.py           # Background webhook delivery worker
├── runtime.py          # Call runtime orchestrator (STT → LLM → TTS pipeline)
├── webhooks.py         # Webhook dispatcher with HMAC signing
├── lemonsqueezy.py     # Billing provider adapter
├── routers/            # 14 domain routers extracted from app.py
│   ├── _helpers.py     # Shared utilities (trace_id, idempotency, pagination)
│   ├── health.py, organizations.py, api_keys.py, billing.py
│   ├── agents.py, calls.py, bookings.py, phone_numbers.py
│   ├── integrations.py, knowledge_bases.py, partners.py
│   ├── webhooks.py, events.py, usage.py
└── adapters/           # Provider adapters (Protocol + stub implementations)
    ├── stt.py, tts.py, llm.py, calendar.py
```

## Development Rules
1. All new files must be < 500 lines
2. All changes must pass `ruff check` and `pytest`
3. New routes go in `routers/`, not `app.py`
4. New business logic goes in `store.py` methods (until service layer refactor)
5. All env vars use `VOICEAGENT_` prefix
6. Never commit `.env` or real secrets
7. API responses must use Pydantic schemas — never return raw dicts
8. All POST mutations require idempotency key

## AI-IDE Integration
- **Claude Code:** Read AGENTS.md first, then CONTEXT_MAP.md
- **Cursor:** Use .cursorrules with these architectural rules
- **Windsurf:** Add .windsurfrules with project context