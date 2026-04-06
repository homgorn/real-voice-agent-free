# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Async SQLAlchemy support with asyncpg driver (optional)

### Changed
- Migrated from pip to uv package manager
- Dockerfile now uses multi-stage build with uv

## [0.2.0] - 2026-04-06

### Added
- 14 domain routers extracted from monolithic app.py
- Security headers middleware (HSTS, CSP, X-Frame-Options, X-Content-Type-Options)
- CORS middleware (strict in production, wildcard in dev/test)
- Global exception handler for all unhandled exceptions
- Rate limiting middleware with Valkey sliding window
- OpenTelemetry SDK integration with /metrics endpoint
- Valkey integration for idempotency cache
- Kubernetes manifests (deployment, service, ingress, HPA, configmap, secrets)
- Nginx reverse proxy configuration with rate limiting
- OpenTelemetry Collector, Prometheus, Alertmanager configs
- GitHub Actions CI/CD pipeline (uv + Ruff + Pytest + Security + Docker)
- Pre-commit hooks (Ruff + compile)
- Makefile with uv-based commands
- SEO landing page with JSON-LD (WebApplication, FAQPage, HowTo, Speakable, Breadcrumb)
- Terms of Service and Privacy Policy sections
- robots.txt and sitemap.xml
- AGENTS.md, CONTEXT_MAP.md, ROADMAP.md, SECURITY.md, USAGE.md

### Changed
- app.py: 1482 → 182 lines
- All POST/PATCH mutation endpoints now require Idempotency-Key header
- Idempotency cache: Valkey first, SQL fallback
- Docker Compose includes Valkey service
- pyproject.toml updated with valkey, opentelemetry, prometheus dependencies

### Fixed
- JSON serialization bug in idempotency cache (SQLAlchemy JSON column)
- Monkeypatch import for license validation tests
- Missing idempotency on PATCH endpoints (bookings, phone_numbers, agents)
- Missing idempotency on webhook test/retry/process endpoints
- Missing idempotency on integration test endpoint
- Meta description length (now < 160 chars)
- Semantic HTML (header, main, nav, article, section)
- Touch target sizes (all >= 44px)
- Schema.org publisher field
- All URLs updated to GitHub Pages

## [0.1.0] - 2026-03-10

### Added
- FastAPI core with domain routers
- Multi-tenant organizations with scoped API keys
- Agent CRUD with versioning, publish, rollback
- Call lifecycle: create, turns, respond, complete, summary
- Booking management with calendar adapter interface
- Webhook system with HMAC signing and retry logic
- Background webhook delivery worker
- Event sourcing for all state changes
- Idempotency protection for critical POSTs
- Lemon Squeezy billing integration
- License validation
- Partner/agency referral system
- Knowledge base with documents
- Integration catalog (calendar, etc.)
- Usage tracking and cost estimation
- Provider adapter pattern (STT, TTS, LLM, Calendar)
- 28+ integration tests
- Docker Compose local dev stack
- Alembic migrations

[Unreleased]: https://github.com/homgorn/real-voice-agent-free/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/homgorn/real-voice-agent-free/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/homgorn/real-voice-agent-free/releases/tag/v0.1.0
