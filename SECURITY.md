# SECURITY.md — VoiceAgent Security Policy

## Supported Versions
| Version | Supported |
|---------|-----------|
| 0.2.x   | ✅        |
| < 0.2   | ❌        |

## Reporting a Vulnerability
Report security vulnerabilities to security@voiceagent.example.com.
We will respond within 48 hours and work with you to resolve the issue.

## OWASP Top 10:2025 Compliance

### A01: Broken Access Control
- ✅ API key authentication with scope-based authorization
- ✅ All resources scoped to organization_id
- ✅ CORS strict mode in production

### A02: Cryptographic Failures
- ✅ bcrypt for API key hashing (12 rounds)
- ✅ HMAC-SHA256 for webhook signatures
- ✅ HTTPS enforced in production

### A03: Software Supply Chain Failures
- ✅ pip-audit in CI pipeline
- ✅ Pinned dependencies in pyproject.toml
- ✅ GitHub Dependabot alerts enabled

### A04: Insecure Design
- ✅ Idempotency protection for all critical POSTs
- ✅ Input validation via Pydantic schemas
- ✅ Rate limiting via Nginx (production)

### A05: Security Misconfiguration
- ✅ Security headers (HSTS, CSP, X-Frame-Options, etc.)
- ✅ Debug endpoints disabled in production
- ✅ No secrets in repository

### A06: Vulnerable Components
- ✅ Regular dependency audits
- ✅ Pre-commit hooks for code quality

### A07: Authentication Failures
- ✅ Bearer token authentication
- ✅ Scope-based authorization
- ✅ last_used_at tracking for key rotation

### A08: Data Integrity
- ✅ Parameterized queries via SQLAlchemy ORM
- ✅ No raw SQL or f-strings in queries

### A09: Logging Failures
- ✅ Structured logging with trace_id
- ✅ No secrets in logs
- ✅ Global exception handler prevents stack trace leaks

### A10: Exceptional Conditions
- ✅ Global exception handler for all unhandled exceptions
- ✅ Custom error types with safe messages
- ✅ No internal details in API responses

## Security Checklist
- [ ] Never commit `.env` file
- [ ] Rotate API keys every 30 days
- [ ] Use separate read-only keys for public frontends
- [ ] Enable rate limiting in production
- [ ] Configure CORS for your domain
- [ ] Use HTTPS (Let's Encrypt / Cloudflare)
- [ ] Enable WAF (Cloudflare / AWS WAF)
- [ ] Set up alerting for anomalies (Prometheus + Alertmanager)
- [ ] Regular dependency updates (`pip install --upgrade`)
- [ ] Quarterly penetration testing
- [ ] Enable Dependabot alerts

## Production Hardening
1. Set `VOICEAGENT_ENV=production`
2. Configure `VOICEAGENT_ALLOWED_ORIGINS` to your domain
3. Configure `VOICEAGENT_ALLOWED_HOSTS` to your API domain
4. Use PostgreSQL (not SQLite)
5. Use bcrypt for API key hashing (install `bcrypt` package)
6. Enable Nginx rate limiting
7. Set up TLS certificates
8. Run behind Cloudflare or similar WAF