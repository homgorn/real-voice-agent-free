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

## Bootstrap v6 Checklist (ALWAYS check before declaring done)

### Phase 1: Core (DONE)
- [x] FastAPI engine with routers (14 domain routers)
- [x] Pydantic Settings (all env vars with VOICEAGENT_ prefix)
- [x] SQLAlchemy ORM + Alembic migrations
- [x] Provider adapters (STT, TTS, LLM, Calendar — Protocol + stubs)
- [x] Multi-tenant org scoping
- [x] API key auth with scope enforcement
- [x] Idempotency on all POST/PATCH
- [x] Event sourcing + webhook delivery
- [x] Worker (background delivery)
- [x] 33/33 tests passing
- [x] Docker Compose (API + DB + Valkey + Worker)
- [x] uv package manager (pyproject.toml, uv.lock)

### Phase 2: Security (DONE)
- [x] Security headers middleware (HSTS, CSP, X-Frame-Options, etc.)
- [x] CORS (strict in prod, wildcard in dev)
- [x] TrustedHostMiddleware
- [x] Global exception handler
- [x] Lifespan pattern (graceful startup/shutdown)
- [x] Rate limiting (Valkey sliding window)
- [x] SEO landing page + JSON-LD schemas
- [x] robots.txt + sitemap.xml

### Phase 3: Infrastructure (DONE)
- [x] Multi-stage Dockerfile (uv)
- [x] Kubernetes manifests (deployment, service, ingress, HPA, configmap, secrets)
- [x] Nginx reverse proxy + rate limiting
- [x] GitHub Actions CI/CD (uv + Ruff + Pytest + Security + Docker)
- [x] Pre-commit hooks (Ruff + compile)
- [x] Makefile (uv-based)
- [x] AGENTS.md, CONTEXT_MAP.md, ROADMAP.md, SECURITY.md, USAGE.md

### Phase 4: Remaining from Bootstrap (DONE)
- [x] OpenTelemetry SDK + `/metrics` endpoint (otel-collector already configured)
- [x] Locust load tests (tests/load_test.py)
- [x] CHANGELOG.md (Keep a Changelog format)
- [x] CODE_OF_CONDUCT.md (Contributor Covenant v2.1)
- [x] CHAT_HISTORY.md
- [x] .editorconfig
- [ ] Async SQLAlchemy (asyncpg driver) — deferred: requires full store.py rewrite