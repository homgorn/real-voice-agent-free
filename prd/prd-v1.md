# VoiceAgent PRD v1

Дата: 9 марта 2026

Источники:

- `spec.txt`
- `docs/product-strategy-and-competitor-research.md`
- `prd/product-brief-v1.md`

## 1. Product Summary

`VoiceAgent` — open-core voice automation platform для SMB service businesses и agency partners.

Платформа должна позволять:

- быстро запустить AI receptionist / booking / FAQ / lead qualification сценарии
- подключать телефонные номера и интеграции
- видеть полную историю, качество и стоимость звонков
- работать в формате `OSS Core`, `Cloud / Pro`, `Agency`

## 2. Goals (MVP)

1. Запустить один продаваемый шаблон для SMB: `receptionist + booking + transfer`.
2. Зафиксировать в продукте чёткую границу между `OSS Core` и платными изданиями.
3. Дать API-first платформу, где все ключевые действия доступны по `/v1`.
4. Сделать продовую дебагабельность звонков заметно лучше, чем у типичных voice AI builder'ов.
5. Подготовить базу для affiliate и agency distribution.

## 3. Non-Goals (MVP)

1. Полноценный enterprise IAM/SSO.
2. Полный набор CRM и мессенджер интеграций.
3. Универсальный visual studio уровня больших бот-платформ.
4. Мобильное приложение.
5. Полная мультирегиональность и private deployment automation.

## 4. Target Users

### Persona A: SMB Owner / Manager

Цель:

- не терять звонки и записи

Needs:

- быстрый запуск
- понятная аналитика
- минимум технических настроек

### Persona B: Operator / Admin

Цель:

- принимать handoff и следить за качеством звонков

Needs:

- список активных и проблемных звонков
- заметки, summary, callback queue

### Persona C: Agency / Integrator

Цель:

- обслуживать много клиентов и перепродавать решение

Needs:

- subaccounts
- шаблоны
- white-label
- usage per client

### Persona D: Developer / Technical Integrator

Цель:

- интегрировать или self-host'ить execution engine

Needs:

- стабильный API
- webhooks
- provider abstraction
- документация и import/export конфигов

## 5. Edition Matrix

## 5.1 OSS Core

Включает:

- self-hosted backend runtime
- сущности `agents`, `workflows`, `calls`, `transcripts`
- API keys
- webhooks
- базовые provider adapters
- базовые call logs и transcripts
- import/export agent config

Не включает:

- hosted billing
- advanced analytics
- audit log
- team RBAC
- premium templates
- managed integrations
- agency subaccounts
- white-label portal

## 5.2 Cloud / Pro

Включает всё из OSS плюс:

- hosted control plane
- usage and cost analytics
- call replay
- prompt/version history
- environments: draft/staging/production
- advanced dashboards
- managed integrations
- QA scoring and anomaly detection
- billing and subscription management

## 5.3 Agency

Включает всё из Pro плюс:

- client subaccounts
- white-label
- partner dashboard
- client-level usage visibility
- margin / rebilling support
- asset/template sharing across accounts

## 6. Core User Flows (MVP)

### Flow 1: Create and publish agent

1. Пользователь создаёт организацию.
2. Создаёт агента из шаблона `Receptionist + Booking`.
3. Подключает номер и календарь.
4. Публикует агента.
5. Получает тестовый звонок и базовый health status.

### Flow 2: Handle live call

1. Входящий звонок приходит на номер.
2. Телефония направляет вызов в execution plane.
3. Агент определяет intent.
4. Агент отвечает, задаёт вопросы, при необходимости вызывает tools.
5. Если нужно, звонок переводится на человека.
6. После завершения сохраняются transcript, summary, outcome, cost, events.

### Flow 3: Booking creation

1. Агент собирает имя, номер, услугу, дату/время.
2. Проверяет доступный слот в календаре.
3. Создаёт booking.
4. Отправляет подтверждение через интеграцию или webhook.

### Flow 4: Partner management

1. Партнёр подключает клиента.
2. Создаёт клиентский subaccount.
3. Разворачивает шаблон.
4. Смотрит usage и health по всем клиентам.

## 7. Functional Requirements

## 7.1 Organizations, Users, Auth

- multi-tenant model по организациям
- пользователи с базовыми ролями `owner`, `admin`, `operator`
- API keys со scope
- отдельные partner/org boundaries для Agency

## 7.2 Agents and Workflows

- создание агента из шаблона
- редактирование системных инструкций и business policy
- настройка business hours
- настройка fallback / escalation logic
- публикация и rollback версий агента

## 7.3 Calls and Telephony

- входящие звонки
- исходящие callback/reminder calls как next step, но не обязательны в day 1
- звонок должен иметь `call_id`, trace, status, latency и cost fields
- запись причины сбоев на уровне telephony / STT / LLM / tool / integration

## 7.4 Transcripts, Summaries, Replay

- хранение transcript по turn-by-turn
- хранение structured summary
- outcome tagging: `faq_resolved`, `booking_created`, `escalated`, `failed`, `lead_captured`
- replay audio/transcript для платных изданий

## 7.5 Knowledge and FAQ

- загрузка FAQ/knowledge документов
- привязка knowledge base к агенту
- retrieval policy и citations как next step, но базовая retrieval-поддержка нужна

## 7.6 Integrations

MVP integrations:

- calendar
- webhooks

Post-MVP:

- CRM
- messaging
- payments

## 7.7 Human Handoff

- ручной перевод на оператора
- сохранение контекста звонка
- передача transcript summary и extracted fields
- очередь callbacks для пропущенных/эскалированных звонков

## 7.8 Analytics and QA

MVP:

- total calls
- answered vs escalated
- booking conversion
- failed calls
- average latency
- average cost per call

Paid:

- timeline per turn
- anomaly detection
- version comparison
- quality scoring

## 7.9 Billing, Licensing, Partnering

- планы и usage records
- webhook sync от billing provider
- affiliate tracking для paid cloud
- лицензирование paid self-hosted edition как отдельный mode

## 7.10 Public API and Webhooks

MVP API:

- CRUD по agents
- publish/revert
- calls read API
- transcripts read API
- bookings API
- integrations connect/test
- usage read API

MVP webhooks:

- `call.started`
- `call.ended`
- `call.escalated`
- `call.failed`
- `booking.created`
- `lead.captured`
- `subscription.activated`
- `subscription.canceled`

## 8. Non-Functional Requirements

- API versioning from day one: `/v1`
- tenant isolation
- structured logs and trace IDs
- idempotency for critical write operations
- secret storage outside source code
- provider timeouts, retries, and circuit breakers
- baseline observability for latency, errors, and cost

## 9. Tech/Product Constraints

- execution plane не должен быть жёстко привязан к одному voice vendor
- control plane и execution plane должны быть разделены логически уже в v1
- OSS setup должен запускаться через Docker Compose
- платные функции не должны ломать self-hosted core

## 10. Success Metrics

1. Первый рабочий агент публикуется <= 15 минут после старта trial.
2. Не менее 80% тестовых звонков по демо-сценарию завершаются без критической ошибки.
3. Базовый booking flow проходит end-to-end.
4. У каждого звонка есть traceable timeline и outcome.
5. Есть платёжный контур и partner-ready модель для Cloud/Agency.

## 11. MVP Exit Criteria

1. Работает template `Receptionist + Booking + Transfer`.
2. Есть `OSS Core` runtime и API.
3. Есть `Cloud / Pro` control plane requirements и billing contract.
4. Есть contracts для API/events/provider adapters.
5. Есть backlog на реализацию Sprint 1.
