# VoiceAgent Epics v1

Источник:

- `prd/prd-v1.md`
- `docs/architecture-v1.md`
- `contracts/api-surface-v1.md`
- `contracts/event-schema-v1.md`

## Epic 1 — Repo Skeleton and Local Developer Experience

Outcome:

- базовая структура репозитория и окружений для OSS Core

Candidate stories:

- создать структуру `apps/`, `packages/`, `contracts/`, `tests/`, `docs/`
- добавить `.env.example`
- добавить docker-compose для локального старта
- добавить logging/tracing bootstrap

## Epic 2 — Identity, Tenancy, and API Keys

Outcome:

- multi-tenant foundation и secure API access

Candidate stories:

- model `organizations`, `users`, `api_keys`
- auth middleware
- scoped API keys
- tenant-aware access checks

## Epic 3 — Agent Config and Versioning

Outcome:

- draft/publish/rollback lifecycle для агента

Candidate stories:

- entities `agents`, `agent_versions`, `templates`
- create/update/publish endpoints
- config validation
- version registry

## Epic 4 — Call Runtime and Telephony Abstraction

Outcome:

- минимальный execution plane для live calls

Candidate stories:

- telephony adapter contract
- runtime session model
- inbound call lifecycle
- transfer/hangup support

## Epic 5 — Turn Orchestration and Provider Layer

Outcome:

- runtime orchestration STT -> LLM/tools -> TTS

Candidate stories:

- STT/TTS/LLM adapter contracts
- turn orchestrator
- fallback policy
- structured error handling

## Epic 6 — Booking Flow and Calendar Integration

Outcome:

- продаваемый `booking` сценарий

Candidate stories:

- slot lookup tool
- booking creation flow
- booking entity and API
- booking events

## Epic 7 — Transcript, Summary, Events, and Observability

Outcome:

- traceability каждого звонка

Candidate stories:

- call turns storage
- transcript generation
- event envelope and dispatcher
- latency/cost/error metrics

## Epic 8 — Control Plane UI

Outcome:

- минимальная hosted/self-managed панель управления

Candidate stories:

- agents list/detail
- publish flow
- calls list/detail
- transcript/timeline view

## Epic 9 — Billing, Licensing, Affiliate, Agency

Outcome:

- коммерческий контур для Cloud/Agency

Candidate stories:

- subscription sync
- license resolution
- affiliate/referral model
- partner subaccounts

## Epic 10 — Quality, Hardening, and Launch Readiness

Outcome:

- минимально надёжный запуск design partners

Candidate stories:

- contract tests
- integration smoke tests
- failure categorization
- rollout checklist
