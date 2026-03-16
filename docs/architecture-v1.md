# VoiceAgent Architecture v1

Дата: 9 марта 2026

## 1. Архитектурные принципы

- boring tech first
- control plane отдельно от execution plane
- provider abstraction вместо vendor lock-in
- observability по умолчанию
- API-first: UI не должен уметь больше, чем API
- OSS Core должен быть полезен сам по себе

## 2. High-Level Overview

Платформа делится на две зоны:

### Control Plane

Отвечает за:

- users and organizations
- plans and billing
- agent configuration
- templates
- integrations metadata
- analytics and QA
- partner/agency features

### Execution Plane

Отвечает за:

- live calls
- session state
- STT/TTS/LLM orchestration
- tool invocation
- realtime tracing
- transcript generation
- call outcomes and event emission

## 3. Service Map

### 3.1 API Service

Стек:

- FastAPI
- PostgreSQL
- Redis

Отвечает за:

- REST API `/v1`
- auth and API keys
- tenant boundaries
- agent/workflow CRUD
- integrations config
- usage read endpoints

### 3.2 Runtime Orchestrator

Отвечает за:

- lifecycle звонка
- orchestration turn-by-turn
- policy enforcement
- tool routing
- fallback logic

### 3.3 Realtime Media Gateway

Отвечает за:

- связь с telephony provider
- аудио-потоки
- realtime events и interruption handling

### 3.4 Worker Service

Отвечает за:

- async jobs
- post-call summary
- webhook delivery
- retry logic
- reporting

### 3.5 Analytics / Event Pipeline

Отвечает за:

- event ingestion
- aggregation metrics
- cost and latency analytics
- dashboards

### 3.6 Partner/Billing Service

Отвечает за:

- subscription state
- usage sync
- license state
- affiliate/referral data
- agency account hierarchy

## 4. Suggested Initial Stack

- backend API: FastAPI
- workers: Celery or Dramatiq
- primary DB: PostgreSQL
- cache and transient state: Redis
- object storage: S3-compatible storage
- frontend: React
- logging/error tracking: structured logs + Sentry
- product analytics: PostHog or ClickHouse-backed analytics
- deployment:
  - OSS: Docker Compose
  - Cloud: managed containers

## 5. Data Domains

Основные сущности:

- `organizations`
- `users`
- `api_keys`
- `agents`
- `agent_versions`
- `templates`
- `phone_numbers`
- `calls`
- `call_turns`
- `transcripts`
- `bookings`
- `contacts`
- `knowledge_bases`
- `integrations`
- `events`
- `usage_records`
- `plans`
- `subscriptions`
- `partners`
- `referrals`

## 6. Provider Adapter Layer

Нужны адаптеры для:

- telephony
- STT
- TTS
- LLM
- calendar
- CRM
- messaging
- billing

Все адаптеры должны:

- иметь единый контракт
- отдавать structured errors
- записывать latency и cost
- поддерживать provider metadata

## 7. Runtime Sequence: Inbound Call

1. Telephony provider отправляет событие о входящем звонке.
2. Media gateway создаёт runtime session.
3. Runtime orchestrator загружает published agent config.
4. STT adapter превращает аудио в текст.
5. LLM/tool layer принимает решение о следующем ходе.
6. Tool adapter вызывается при необходимости.
7. TTS adapter формирует ответ.
8. Все turn events, latency и cost пишутся в event stream.
9. После завершения воркер формирует summary и outcome.
10. Webhook dispatcher публикует внешние события.

## 8. Control Plane Sequence: Agent Publish

1. Пользователь меняет draft-конфиг агента.
2. API service валидирует конфиг.
3. Создаётся immutable `agent_version`.
4. Version registry помечает версию как published.
5. Execution plane читает новую published version по tenant/agent id.

## 9. Deployment Models

## 9.1 OSS Core

Включает:

- API service
- runtime orchestrator
- worker
- PostgreSQL
- Redis

Запуск:

- `docker-compose.yml`

## 9.2 Cloud / Pro

Включает всё из OSS плюс:

- hosted control plane UI
- analytics stack
- billing sync
- partner services
- managed integrations

## 10. Security and Isolation

- tenant-aware access checks
- API keys with scopes
- secrets outside repo
- audit events для админских действий
- redaction policy для transcript/PII
- signed webhooks

## 11. Observability

Базовые требования:

- `trace_id` у каждого звонка и фоновой операции
- per-turn latency
- per-provider latency
- per-call cost
- error category:
  - `telephony`
  - `stt`
  - `tts`
  - `llm`
  - `tool`
  - `integration`
  - `internal`

Это один из ключевых differentiator'ов продукта.

## 12. Decisions Deferred

- конкретный telephony runtime vendor для hosted version
- конкретный open-source telephony reference stack
- конкретный vector/retrieval backend
- exact agency rebilling mechanics
- private deployment packaging
