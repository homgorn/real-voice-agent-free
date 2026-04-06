# ROADMAP.md — VoiceAgent Development Plan

## ✅ Completed (v0.1 — March 2026)
- [x] FastAPI core with 14 domain routers
- [x] Multi-tenant organizations with scoped API keys
- [x] Agent CRUD with versioning, publish, rollback
- [x] Call lifecycle: create, turns, respond, complete, summary
- [x] Booking management with calendar adapter interface
- [x] Webhook system with HMAC signing and retry logic
- [x] Background webhook delivery worker
- [x] Event sourcing for all state changes
- [x] Idempotency protection for critical POSTs
- [x] Lemon Squeezy billing integration
- [x] License validation
- [x] Partner/agency referral system
- [x] Knowledge base with documents
- [x] Integration catalog (calendar, etc.)
- [x] Usage tracking and cost estimation
- [x] Provider adapter pattern (STT, TTS, LLM, Calendar)
- [x] 28+ integration tests
- [x] Docker Compose local dev stack
- [x] Alembic migrations

## ✅ Completed (v0.2 — April 2026)
- [x] Router extraction (app.py: 1482 → 182 lines)
- [x] Security headers middleware (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, Permissions-Policy)
- [x] CORS middleware (configurable per environment)
- [x] Global exception handler (catch-all for Exception)
- [x] Lifespan pattern for graceful startup/shutdown
- [x] Idempotency on ALL POST/PATCH mutation endpoints (was only critical POSTs)
- [x] JSON serialization fix for idempotency cache (SQLAlchemy JSON column)
- [x] Multi-stage Dockerfile
- [x] Kubernetes manifests (deployment, service, ingress, HPA, configmap, secrets)
- [x] Nginx reverse proxy with rate limiting
- [x] OpenTelemetry Collector config
- [x] Prometheus + Alertmanager config
- [x] GitHub Actions CI/CD (lint, test, security, docker)
- [x] Pre-commit hooks (Ruff + compile)
- [x] SEO landing page with JSON-LD (WebApplication, FAQPage, HowTo, SpeakableSpecification)
- [x] robots.txt + sitemap.xml
- [x] AGENTS.md, CONTEXT_MAP.md, ROADMAP.md, SECURITY.md, USAGE.md
- [x] Updated README.md with SEO keywords
- [x] 33/33 tests passing
- [x] Makefile for dev commands

## 🔄 In Progress
- [ ] Async SQLAlchemy migration (asyncpg)
- [ ] Valkey integration for idempotency + rate limiting
- [ ] OpenTelemetry SDK instrumentation
- [ ] Prometheus /metrics endpoint
- [ ] SQL-level pagination (replace in-memory)
- [ ] Store.py refactoring into domain services
- [ ] Replace _serialize_* with Pydantic model_validate

## 📋 Planned (v0.3)
- [ ] Real STT provider (OpenAI Whisper / Deepgram)
- [ ] Real TTS provider (OpenAI / ElevenLabs)
- [ ] Real LLM provider (OpenAI / Anthropic)
- [ ] Real Calendar provider (Google Calendar)
- [ ] Telephony adapter (Twilio / Vapi)
- [ ] CRM adapter (HubSpot)
- [ ] Real-time WebSocket for live call monitoring
- [ ] Call recording storage (S3-compatible)
- [ ] Post-call summary generation (LLM-based)
- [ ] Dashboard UI (React)

## 📋 Planned (v0.4 — Cloud/Pro)
- [ ] Hosted control plane
- [ ] Analytics dashboard (PostHog / ClickHouse)
- [ ] Usage-based billing
- [ ] Managed integrations catalog
- [ ] White-label/agency features
- [ ] Enterprise SSO (SAML/OIDC)
- [ ] Audit log for admin actions
- [ ] PII redaction policy for transcripts

## 💡 Ideas
- [ ] Voice cloning for custom agent voices
- [ ] Multi-language support (real-time translation)
- [ ] Sentiment analysis during calls
- [ ] Automated QA scoring for call quality
- [ ] A/B testing for agent configurations
- [ ] Call intent classification
- [ ] Predictive escalation (detect frustration)

## Tech Debt Tracker
| Item | Priority | Effort | Status |
|------|----------|--------|--------|
| store.py → domain services | High | Large | Planned |
| In-memory pagination → SQL | High | Medium | Planned |
| Sync runtime → async | Medium | Medium | Planned |
| Usage cost calculation → SQL aggregation | Medium | Small | Planned |
| _serialize_* → Pydantic model_validate | Medium | Medium | Planned |
| Async SQLAlchemy (asyncpg) | Medium | Medium | Planned |
| Valkey integration | Medium | Medium | Planned |
| OpenTelemetry SDK instrumentation | Medium | Medium | Planned |
| In-memory pagination → SQL | High | Medium | Planned |
| SHA-256 → bcrypt for existing keys | Medium | Small | Done (new keys) |
| Sync runtime → async | Medium | Medium | Planned |
| Usage cost calculation → SQL aggregation | Medium | Small | Planned |