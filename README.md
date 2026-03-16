# VoiceAgent — Open-Source Voice AI Platform for SMB Service Businesses

VoiceAgent is an open-core voice automation platform that helps service businesses handle inbound calls, bookings, and customer support with AI phone agents. It combines an API-first core with vertical templates, observability, and integration hooks for real-world operations.

## What VoiceAgent Solves

- Automates inbound phone calls and call routing for SMB teams.
- Handles appointment scheduling, confirmations, and follow-ups.
- Powers AI receptionist workflows with escalation to humans.
- Provides an auditable API for voice agent orchestration.

## Why VoiceAgent (Positioning)

- Vertical templates for specific service industries.
- Strong debugging and call observability.
- Human handoff built into the flow.
- Transparent usage economics for operators.
- API-first integrations with external systems.
- Partner distribution and white-label readiness.

## Core Features (OSS Core)

- Multi-tenant organizations with scoped API keys.
- Agents with versioning, rollback, and templates.
- Call lifecycle endpoints: turns, summaries, runtime responses.
- Booking updates and scheduling hooks.
- Knowledge bases and integrations catalog.
- Webhooks with HMAC signatures and retry-aware delivery.
- Usage tracking and partner referral plumbing.
- Idempotency protection for critical write operations.
- SQLAlchemy persistence with Alembic migrations.
- Background worker for delivery retries and polling.

## API Resources (Bootstrap)

- `organizations`, `api keys`, `plans`, `subscriptions`, `licenses`
- `agents`, `agent versions`, `templates`
- `phone numbers`, `calls`, `call turns`, `call runtime respond`
- `call summary`, `bookings`, `knowledge bases`, `integrations`
- `usage`, `partners`, `events`, `webhooks`, `webhook deliveries`

Важно: все критичные `POST` операции требуют заголовок `Idempotency-Key` и возвращают 428 при его отсутствии.

## Quick Start

```powershell
python -m pytest
python -m alembic upgrade head
uvicorn voiceagent_api.app:app --app-dir apps/api/src --reload
$env:PYTHONPATH="apps/api/src"
python -m voiceagent_api.worker --once
```

Локально bootstrap использует SQLite. Следующий production-oriented шаг — перевод на PostgreSQL-конфиг и реальные migrations/revision workflows.

Docker runtime:

```powershell
docker compose up --build
```

Фоновый worker:

```powershell
$env:PYTHONPATH="apps/api/src"
python -m voiceagent_api.worker --once
python -m voiceagent_api.worker
```

В `docker compose` поднимаются `api`, `worker`, `db`.

## Repository Docs

- Product and market strategy: `docs/product-strategy-and-competitor-research.md`
- BMAD assets and workflow plan: `docs/bmad-assets-and-workflow-plan.md`
- Product brief: `prd/product-brief-v1.md`
- PRD: `prd/prd-v1.md`
- Architecture: `docs/architecture-v1.md`
- API contract: `contracts/api-surface-v1.md`
- Event contract: `contracts/event-schema-v1.md`
- Provider contract: `contracts/provider-adapter-interface-v1.md`
- Backlog: `backlog/epics-v1.md`
- Original source spec: `spec.txt`

## Near-Term Priorities

1. Freeze OSS vs paid boundary.
2. Define `/v1` API resources and webhook model.
3. Build the first vertical template: receptionist + booking + transfer.
4. Add billing and affiliate plumbing for Cloud/Pro.
5. Onboard design partners and validate ROI.

## Cloud / Pro Direction

- Hosted control plane with analytics and QA.
- Billing, usage, and partner tooling.
- White-label/agency features.
- Enterprise observability and governance.

## Keywords

Voice AI, AI phone agent, call automation, appointment scheduling, customer support automation, open-source voice agent API, voice bot platform, SMB call handling.

## BMAD Context

This repo lives inside a larger `bmad` workspace. We should actively reuse the nearby BMAD research, PM, and architecture workflows instead of inventing our own planning process from scratch.

## Notes

The current repo is at strategy stage. The heavy enterprise stack from the original spec should not be implemented as MVP by default.
