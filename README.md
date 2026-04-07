# VoiceAgent — Open-Source AI Phone Agent Platform for SMB Service Businesses

[![CI](https://github.com/voiceagent/voiceagent/actions/workflows/ci.yml/badge.svg)](https://github.com/voiceagent/voiceagent/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)

VoiceAgent is an open-source voice AI platform that automates inbound calls, appointment scheduling, and customer support for service businesses. Built with FastAPI, PostgreSQL, and a provider adapter pattern for zero vendor lock-in.

## What VoiceAgent Solves

- **Automates inbound calls** — AI receptionists handle FAQs, routing, and lead capture 24/7
- **Appointment scheduling** — Calendar integration with conflict resolution and confirmations
- **Customer support automation** — Knowledge base-powered responses with human escalation
- **Full call observability** — Per-turn latency, per-provider cost, trace IDs for every call
- **API-first integrations** — REST API for everything; webhooks for real-time events
- **Operator control plane** — Dashboard overview, onboarding flows, test calls, bookings, and setup actions

## Why VoiceAgent (Positioning)

- **Vertical templates** for dental clinics, salons, auto repair, law firms, consultants
- **Strong debugging** — Every call is traced with latency and cost breakdowns
- **Human handoff** built into every flow — escalate when AI can't help
- **Transparent economics** — Know exactly what each call costs in tokens and duration
- **API-first** — UI never does more than the API can do
- **Partner distribution** — White-label and agency-ready with sub-account management

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    VoiceAgent Platform                       │
├───────────────────────┬─────────────────────────────────────┤
│  Control Plane (API)  │  Execution Plane (Runtime)           │
│  ├─ 14 Domain Routers │  ├─ CallRuntimeOrchestrator          │
│  ├─ Security Middleware│  ├─ STT → LLM → TTS Pipeline       │
│  ├─ Exception Handlers │  └─ Provider Adapters (pluggable)    │
│  └─ Lifespan mgmt     │                                      │
├───────────────────────┴─────────────────────────────────────┤
│  PostgreSQL (prod) / SQLite (dev) │  Valkey (future: cache)  │
│  18 tables · Alembic migrations   │  Webhook worker (async)  │
└─────────────────────────────────────────────────────────────┘
```

## Core Features

| Feature | Description |
|---------|-------------|
| Multi-tenant orgs | Scoped API keys, data isolation per organization |
| Agent versioning | Draft → Publish → Rollback with immutable snapshots |
| Call lifecycle | Create → Turns → Respond → Complete → Summary |
| Booking management | Calendar adapter interface (Google, Calendly, custom) |
| Webhook delivery | HMAC-signed, retry with exponential backoff |
| Event sourcing | All state changes emit events for audit and integrations |
| Provider adapters | STT, TTS, LLM, Calendar — Protocol-based, zero lock-in |
| Usage tracking | Per-call cost estimation (tokens + duration) |
| Dashboard overview | Control plane summary with action items, upcoming bookings, and operator workflows |
| Partner system | Referral tracking, sub-account management |
| Idempotency | All critical POSTs protected (428 if missing key) |

## Quick Start

```bash
# 1. Install
pip install -e ".[dev]"

# 2. Test
pytest tests/ -v

# 3. Run
uvicorn voiceagent_api.app:app --app-dir apps/api/src --host 0.0.0.0 --port 8000 --reload

# 4. Worker (separate terminal)
PYTHONPATH=apps/api/src python -m voiceagent_api.worker
```

### Docker

```bash
docker compose up --build -d
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

## API Resources

| Resource | Endpoints | Auth Scopes |
|----------|-----------|-------------|
| Organizations | GET, PATCH `/v1/organizations/current` | `orgs:read`, `orgs:write` |
| API Keys | GET, POST, DELETE `/v1/api-keys` | `api_keys:*` |
| Agents | CRUD + publish + rollback `/v1/agents` | `agents:*` |
| Calls | CRUD + turns + respond + complete | `calls:*` |
| Bookings | CRUD `/v1/bookings` | `bookings:*` |
| Webhooks | CRUD + test + retry + process | `webhooks:*` |
| Events | GET `/v1/events` | `events:read` |
| Usage | GET `/v1/usage`, `/v1/usage/costs` | `usage:read` |

> **Important:** All critical POST operations require `Idempotency-Key` header and return 428 if missing.

## Provider Adapters

VoiceAgent uses a Protocol-based adapter pattern for all external providers:

- **STT** (Speech-to-Text): Stub → OpenAI Whisper / Deepgram
- **TTS** (Text-to-Speech): Stub → OpenAI / ElevenLabs
- **LLM** (Language Model): Stub → OpenAI / Anthropic
- **Calendar**: Stub → Google Calendar / Calendly
- **Telephony**: Planned → Twilio / Vapi
- **CRM**: Planned → HubSpot / Salesforce

Add real providers by implementing the Protocol interface — no core changes needed.

Current runtime supports OpenAI-backed STT, LLM, and TTS when `VOICEAGENT_OPENAI_API_KEY` is configured; otherwise it falls back to stub providers for local development and tests.

## Deployment

### Budget $50/mo
```
API: Hetzner CPX21 (2 vCPU, 4GB) — $9.50
DB: Neon Free (100 CU-hrs) — $0
Cache: Upstash Valkey Free — $0
CDN: Cloudflare Free — $0
Total: ~$10/mo
```

### Budget $200/mo
```
API: Hetzner CCX22 (4 vCPU, 16GB) — $30
DB: DigitalOcean Managed PG — $15
Cache: DigitalOcean Managed Valkey — $15
CDN: Cloudflare Pro — $20
Monitoring: Grafana Cloud + Sentry — $26
Total: ~$106/mo
```

### Production Stack
```
Cloudflare (CDN + WAF) → Nginx (rate limiting) → FastAPI (K8s pods)
                                                    ↓
                                          PostgreSQL (managed)
                                          Valkey (cache + rate limit)
                                          OpenTelemetry → Prometheus → Grafana
```

## Documentation

| Document | Purpose |
|----------|---------|
| [AGENTS.md](AGENTS.md) | AI-IDE context for Claude Code, Cursor, Windsurf |
| [CONTEXT_MAP.md](CONTEXT_MAP.md) | System architecture map, data flows, API map |
| [ROADMAP.md](ROADMAP.md) | Development plan, tech debt tracker |
| [SECURITY.md](SECURITY.md) | Security policy, OWASP Top 10:2025 compliance |
| [USAGE.md](USAGE.md) | Full usage guide with curl examples |
| [docs/architecture-v1.md](docs/architecture-v1.md) | Architecture decisions |
| [contracts/api-surface-v1.md](contracts/api-surface-v1.md) | API contract |
| [contracts/provider-adapter-interface-v1.md](contracts/provider-adapter-interface-v1.md) | Provider adapter contract |

## Keywords

Voice AI, AI phone agent, call automation, appointment scheduling, customer support automation, open-source voice agent API, voice bot platform, SMB call handling, AI receptionist, voice API, call observability, multi-tenant voice platform

## License

MIT — see [LICENSE](LICENSE) for details.


