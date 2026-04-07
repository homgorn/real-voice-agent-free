# Self-Hosting VoiceAgent

VoiceAgent can run locally for development and on standard container infrastructure for production.

## Local Development

```bash
pip install -e ".[dev]"
python -m pytest -q
uvicorn voiceagent_api.app:app --app-dir apps/api/src --reload
PYTHONPATH=apps/api/src python -m voiceagent_api.worker
python -m http.server 4173 -d apps/web
```

## Docker Compose

```bash
docker compose up --build -d
```

Typical local endpoints:
- API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`
- Control plane: `http://localhost:4173`

## Production Shape

A practical production path is:

- Cloudflare or another edge proxy
- Nginx / ingress in front of the API
- FastAPI app for control plane and API traffic
- Worker process for webhook delivery
- PostgreSQL as the primary database
- Optional Valkey for rate limiting and related platform concerns

## Minimum Production Checklist

- Set `VOICEAGENT_ENV=production`
- Use PostgreSQL instead of SQLite
- Configure `VOICEAGENT_ALLOWED_ORIGINS`
- Configure `VOICEAGENT_ALLOWED_HOSTS`
- Replace bootstrap API keys with secure values
- Put secrets in environment or secret storage
- Run API and worker as separate processes

## Related Docs

- [openai-runtime.md](openai-runtime.md)
- [../USAGE.md](../USAGE.md)
- [../SECURITY.md](../SECURITY.md)
