# VoiceAgent Stories Sprint 01

Цель спринта:

- подготовить skeleton для `OSS Core`
- зафиксировать доменные контракты
- создать минимальный backend foundation под API и runtime

## Story 1 — Repo structure

Как разработчик,
я хочу стандартную структуру репозитория,
чтобы product docs, backend, frontend и contracts не смешивались.

Acceptance criteria:

- есть директории для backend app, frontend app, shared contracts, tests
- README объясняет назначение структуры

## Story 2 — Environment config

Как разработчик,
я хочу понятный env/config слой,
чтобы локальный запуск и дальнейший деплой не были хаотичными.

Acceptance criteria:

- есть `.env.example`
- есть конфиг приложения с обязательными переменными
- есть валидация критичных настроек

## Story 3 — FastAPI skeleton

Как разработчик,
я хочу минимальный FastAPI backend,
чтобы начать реализацию `/v1` API.

Acceptance criteria:

- есть health endpoint
- есть versioned router `/v1`
- есть базовый app factory

## Story 4 — Domain models for orgs and agents

Как платформа,
я хочу базовые доменные модели,
чтобы можно было хранить организации и агентов.

Acceptance criteria:

- описаны схемы `Organization`, `Agent`, `AgentVersion`
- есть миграционный план или model notes

## Story 5 — API key auth

Как интегратор,
я хочу использовать API key,
чтобы безопасно вызывать API без dashboard session.

Acceptance criteria:

- есть `Authorization: Bearer`
- есть scope-aware key validation
- невалидный ключ даёт нормализованную ошибку

## Story 6 — Agent CRUD

Как пользователь,
я хочу создавать и читать агентов,
чтобы управлять конфигурацией voice workflow.

Acceptance criteria:

- `POST /v1/agents`
- `GET /v1/agents`
- `GET /v1/agents/{agent_id}`

## Story 7 — Publish flow contract

Как пользователь,
я хочу публиковать версию агента,
чтобы runtime использовал только валидную immutable конфигурацию.

Acceptance criteria:

- есть endpoint publish
- создаётся отдельная version record
- published version отделена от draft

## Story 8 — Event envelope implementation plan

Как команда,
я хочу единый event envelope,
чтобы runtime, analytics и integrations использовали один формат.

Acceptance criteria:

- event envelope описан в коде или schema package
- есть validation rules

## Story 9 — Provider adapter interfaces

Как команда,
я хочу формальные adapter interfaces,
чтобы можно было независимо реализовывать telephony/STT/TTS/LLM.

Acceptance criteria:

- есть интерфейсы для основных adapter типов
- есть unified error/result shape

## Story 10 — Test and quality bootstrap

Как команда,
я хочу базовые тесты и quality gates,
чтобы дальше не накапливать хаос.

Acceptance criteria:

- есть test runner
- есть минимум smoke tests для app startup и health endpoint
- есть contract tests для API error shape
