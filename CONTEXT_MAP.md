# CONTEXT_MAP.md — VoiceAgent System Map

## System Overview
```
┌─────────────────────────────────────────────────────────────┐
│                     VoiceAgent Platform                      │
├─────────────────────────────────────────────────────────────┤
│  Control Plane (API)           │  Execution Plane (Runtime)  │
│  ┌──────────────────────────┐  │  ┌──────────────────────┐   │
│  │  FastAPI App (app.py)    │  │  │  CallRuntimeOrchestr. │   │
│  │  ├─ 14 Domain Routers    │  │  │  ├─ STT Adapter       │   │
│  │  ├─ Security Middleware   │  │  │  ├─ LLM Adapter       │   │
│  │  ├─ Exception Handlers    │  │  │  └─ TTS Adapter       │   │
│  │  └─ Lifespan (start/stop)│  │  └──────────────────────┘   │
│  └──────────────────────────┘  │                              │
│  ┌──────────────────────────┐  │  ┌──────────────────────┐   │
│  │  AgentStore (store.py)   │  │  │  Webhook Worker       │   │
│  │  ├─ CRUD for all domains │  │  │  ├─ Poll queue        │   │
│  │  ├─ Idempotency logic    │  │  │  ├─ Retry w/backoff   │   │
│  │  ├─ Event emission       │  │  │  └─ Deliver webhooks  │   │
│  │  └─ Billing sync         │  │  └──────────────────────┘   │
│  └──────────────────────────┘  │                              │
├─────────────────────────────────────────────────────────────┤
│  Data Layer                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ PostgreSQL    │  │ SQLite (dev) │  │ Valkey (future)  │   │
│  │ 18 tables     │  │ Single file  │  │ Idempotency+     │   │
│  │ ORM: SQLAlchemy│  │              │  │ Rate limiting    │   │
│  └──────────────┘  └──────────────┘  └──────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  Provider Adapters                                           │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────────┐                   │
│  │ STT   │ │ TTS  │ │ LLM  │ │ Calendar │                   │
│  │ (stub)│ │(stub)│ │(stub)│ │ (stub)   │                   │
│  └──────┘ └──────┘ └──────┘ └──────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow: Inbound Call
```
Telephony Provider → POST /v1/calls → store.create_call()
  → Event: call.started → Webhook delivery (if subscribed)
  → POST /v1/calls/{id}/respond → runtime_orchestrator.respond()
    → STT.transcribe() → LLM.generate_turn() → TTS.synthesize()
    → store.add_call_turn() → Event: call.turn.completed
  → POST /v1/calls/{id}/complete → store.complete_call()
    → store.call_summaries upsert → Event: call.ended
    → Webhook delivery (if subscribed)
```

## Data Flow: Agent Publish
```
POST /v1/agents/{id}/publish → store.publish_agent()
  → Create AgentVersionModel (immutable snapshot)
  → Update AgentModel status to "published"
  → Event: agent.published → Webhook delivery
```

## API Map
| Router | Prefix | Methods | Auth Scopes | Idempotency |
|--------|--------|---------|-------------|-------------|
| health | /health, /ready | GET | None | No |
| organizations | /v1/organizations/current | GET, PATCH | orgs:read, orgs:write | No |
| api_keys | /v1/api-keys | GET, POST, DELETE | api_keys:read, api_keys:write | POST |
| billing | /v1/plans, /v1/subscriptions, /v1/licenses, /v1/billing/* | GET, POST | billing:read, billing:write | POST |
| agents | /v1/agents, /v1/templates | GET, POST, PATCH, publish, rollback | agents:* | POST, PATCH, publish, rollback |
| calls | /v1/calls | GET, POST, turns, respond, complete | calls:read, calls:write | All POST |
| bookings | /v1/bookings | GET, POST, PATCH | bookings:read, bookings:write | POST, PATCH |
| phone_numbers | /v1/phone-numbers | GET, POST, PATCH | phone_numbers:read, phone_numbers:write | POST, PATCH |
| integrations | /v1/integrations | GET, POST | integrations:read, integrations:write | POST (connect, test) |
| knowledge_bases | /v1/knowledge-bases | GET, POST | knowledge_bases:read, knowledge_bases:write | POST |
| partners | /v1/partners | GET, POST | partners:read, partners:write | POST |
| webhooks | /v1/webhooks | GET, POST, DELETE, test, retry, process | webhooks:read, webhooks:write | POST, retry, test |
| events | /v1/events | GET | events:read | No |
| usage | /v1/usage | GET | usage:read | No |

## Database Tables (18)
agents, agent_versions, organizations, api_keys, plans, subscriptions,
licenses, billing_webhook_events, templates, bookings, events,
webhook_subscriptions, webhook_deliveries, calls, call_turns,
call_summaries, phone_numbers, integrations, knowledge_bases,
knowledge_base_documents, partners, partner_accounts, idempotency_keys

## Key Types
- `AgentModel` - Agent configuration with versioning
- `CallModel` - Call lifecycle tracking
- `CallTurnModel` - Individual conversation turns with latency/cost
- `EventModel` - Event sourcing for all state changes
- `WebhookDeliveryModel` - Reliable webhook delivery with retries
- `IdempotencyKeyModel` - Idempotency protection for POST operations

## File Structure
```
apps/api/src/voiceagent_api/
├── app.py              # FastAPI engine (182 lines) — routers, middleware, exception handlers
├── config.py           # Pydantic Settings (all env vars with VOICEAGENT_ prefix)
├── db.py               # SQLAlchemy engine, session, create/close database
├── models.py           # SQLAlchemy ORM models (18 tables)
├── schemas.py          # Pydantic request/response schemas (60+ models)
├── store.py            # Service layer (all business logic, ~2200 lines)
├── auth.py             # API key authentication with SHA-256, scope enforcement
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