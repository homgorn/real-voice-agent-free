# VoiceAgent — Open-Source AI Phone Agent for Call Automation, Appointment Scheduling, and AI Receptionists

[![CI](https://github.com/voiceagent/voiceagent/actions/workflows/ci.yml/badge.svg)](https://github.com/voiceagent/voiceagent/actions/workflows/ci.yml)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)

VoiceAgent is an open-source AI phone agent platform for SMB service businesses. It helps teams automate inbound calls, appointment scheduling, lead capture, FAQ handling, and operator follow-up through an API-first backend and a lightweight control plane.

## What VoiceAgent Is

VoiceAgent is designed for companies that need an AI receptionist or AI voice agent without hard vendor lock-in.

- Automates inbound call handling for clinics, salons, auto services, consultants, and local service businesses
- Supports appointment booking workflows with availability lookup and booking conflict protection
- Runs a voice runtime pipeline with `STT -> LLM -> TTS`
- Exposes the full product through REST APIs, webhook events, and an operator control plane
- Keeps provider boundaries explicit through adapter interfaces for STT, TTS, LLM, and calendar systems

## Core Use Cases

- **AI receptionist** for answering common questions and routing calls
- **Appointment scheduling software** for service businesses that book over the phone
- **Call automation platform** for inbound support and lead qualification
- **Voice AI backend** for teams building custom telephony or CRM workflows
- **Operator control plane** for reviewing calls, bookings, integrations, and launch blockers

## Why It Matters

- **Open-source voice agent stack** — backend logic is inspectable and extensible
- **API-first architecture** — the UI sits on top of the same APIs exposed to integrators
- **Scheduling logic** — availability lookup, slot suggestions, and double-booking prevention are built into the backend
- **Observability** — every call turn stores latency, provider metadata, tool execution, and summaries
- **Operational workflows** — the control plane handles publishing agents, simulating calls, reviewing transcripts, and managing bookings

## Product Snapshot

| Area | Current capability |
|------|--------------------|
| Agents | Draft, publish, rollback, template-based creation |
| Calls | Create, respond, inspect transcript, complete, summarize |
| Scheduling | Availability lookup, slot suggestions, booking conflict checks |
| Integrations | Calendar integration records and health checks |
| Security | Scoped API keys, idempotency, security headers, CORS, trusted hosts |
| Platform | FastAPI, SQLAlchemy, Alembic, worker, metrics, CI/CD |
| Frontend | Operator control plane for launch setup and daily operations |

## Architecture

```text
Cloudflare / Edge
  -> Nginx / ingress
  -> FastAPI API
       -> routers
       -> store.py business logic
       -> runtime orchestrator
       -> webhook worker
  -> PostgreSQL or SQLite
  -> Valkey / rate limit / cache layer
  -> Provider adapters (STT, LLM, TTS, Calendar)
```

## Control Plane and Runtime

VoiceAgent now includes both the execution layer and the operator layer.

- **Runtime** handles the call turn pipeline and provider adapters
- **Scheduling core** calculates available slots from agent business hours and existing bookings
- **Control plane** lets operators create agents, connect integrations, simulate calls, inspect call transcripts, and create bookings from suggested slots

## Quick Start

```bash
pip install -e ".[dev]"
python -m pytest -q
uvicorn voiceagent_api.app:app --app-dir apps/api/src --host 0.0.0.0 --port 8000 --reload
```

Worker:

```bash
PYTHONPATH=apps/api/src python -m voiceagent_api.worker
```

Control plane:

```bash
python -m http.server 4173 -d apps/web
```

- API docs: `http://localhost:8000/docs`
- Control plane: `http://localhost:4173`

## Main Documentation

- [docs/README.md](docs/README.md) — documentation index
- [USAGE.md](USAGE.md) — end-to-end usage guide and curl examples
- [docs/api-quickstart.md](docs/api-quickstart.md) — fast API onboarding
- [docs/self-hosting.md](docs/self-hosting.md) — local and production deployment notes
- [docs/openai-runtime.md](docs/openai-runtime.md) — OpenAI voice runtime setup
- [docs/control-plane.md](docs/control-plane.md) — operator UI and workflows
- [docs/scheduling-and-bookings.md](docs/scheduling-and-bookings.md) — availability and booking logic
- [SECURITY.md](SECURITY.md) — security posture and policies
- [ROADMAP.md](ROADMAP.md) — current roadmap and gaps
- [CONTEXT_MAP.md](CONTEXT_MAP.md) — architecture, API map, and code layout

## API Surface

| Resource | Key endpoints |
|----------|---------------|
| Agents | `/v1/agents`, `/v1/agents/{id}/publish`, `/v1/agents/{id}/availability` |
| Calls | `/v1/calls`, `/v1/calls/{id}/respond`, `/v1/calls/{id}/complete` |
| Bookings | `/v1/bookings` |
| Dashboard | `/v1/dashboard/overview` |
| Integrations | `/v1/integrations/{provider}/connect`, `/v1/integrations/{provider}/test` |
| Webhooks | `/v1/webhooks` |

> All POST and PATCH mutations require `Idempotency-Key`.

## Deployment Options

### Small self-hosted footprint
- FastAPI app on a single VM
- PostgreSQL or SQLite for development
- Optional Valkey for rate limiting and idempotency support
- Cloudflare in front for TLS, caching, and basic protection

### Larger production setup
- Managed PostgreSQL
- Kubernetes deployment or container hosting
- Nginx or ingress rate limiting
- OpenTelemetry + Prometheus + Grafana
- External telephony and calendar providers

## SEO / Search Intent Coverage

This repository is relevant for searches around:

- open-source AI phone agent
- AI receptionist for small business
- voice AI appointment scheduling
- inbound call automation platform
- FastAPI voice bot backend
- open-source call center automation
- AI voice agent with calendar booking
- operator control plane for voice AI

## What Is Still Missing

VoiceAgent is substantially more complete than an initial bootstrap, but it is not the final hosted product yet.

- Telephony ingress is not finished end-to-end
- Browser-safe hosted auth is not implemented yet
- CRM adapters and richer provider integrations are still pending
- Frontend is useful, but not yet a production SPA

## License

MIT — see [LICENSE](LICENSE) for details.
