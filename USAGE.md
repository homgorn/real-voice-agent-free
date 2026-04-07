# USAGE.md — VoiceAgent Usage Guide

## Quick Start

### Local Development (SQLite)
```bash
# Install dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Start the API server
uvicorn voiceagent_api.app:app --app-dir apps/api/src --host 0.0.0.0 --port 8000 --reload

# Run the webhook worker (in another terminal)
PYTHONPATH=apps/api/src python -m voiceagent_api.worker
```

### Docker Compose (PostgreSQL)
```bash
docker compose up --build -d
# API: http://localhost:8000
# Docs: http://localhost:8000/docs
```

## Authentication

All API requests except `/health` and `/ready` require a Bearer token:

```bash
curl -H "Authorization: Bearer dev-secret-key" http://localhost:8000/v1/agents
```

### Available Bootstrap Keys

| Key | Scopes |
|-----|--------|
| `dev-secret-key` | Full access (all scopes) |
| `read-only-key` | Read-only access |

### Creating API Keys

```bash
curl -X POST http://localhost:8000/v1/api-keys \
  -H "Authorization: Bearer dev-secret-key" \
  -H "Idempotency-Key: create-key-001" \
  -H "Content-Type: application/json" \
  -d '{"name": "my-service", "scopes": ["agents:read", "calls:read"]}'
```

## API Examples

### Create an Agent

```bash
curl -X POST http://localhost:8000/v1/agents \
  -H "Authorization: Bearer dev-secret-key" \
  -H "Idempotency-Key: agent-001" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Front Desk",
    "template_id": "tpl_receptionist_booking_v1",
    "timezone": "Asia/Almaty",
    "default_language": "ru",
    "business_hours": {"mon_fri": ["09:00-18:00"]}
  }'
```

### Publish an Agent

```bash
curl -X POST http://localhost:8000/v1/agents/{agent_id}/publish \
  -H "Authorization: Bearer dev-secret-key" \
  -H "Idempotency-Key: publish-001" \
  -H "Content-Type: application/json" \
  -d '{"target_environment": "production"}'
```

### Create a Booking

```bash
curl -X POST http://localhost:8000/v1/bookings \
  -H "Authorization: Bearer dev-secret-key" \
  -H "Idempotency-Key: booking-001" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agt_xxx",
    "contact_name": "Алина",
    "contact_phone": "+77011234567",
    "service": "consultation",
    "start_at": "2026-04-10T15:00:00+05:00"
  }'
```

### Call Runtime Respond

```bash
curl -X POST http://localhost:8000/v1/calls/{call_id}/respond \
  -H "Authorization: Bearer dev-secret-key" \
  -H "Idempotency-Key: respond-001" \
  -H "Content-Type: application/json" \
  -d '{"input_text": "Хочу записаться на завтра", "voice_id": "nova"}'
```

### OpenAI Runtime

```bash
VOICEAGENT_OPENAI_API_KEY=sk-... \
VOICEAGENT_OPENAI_STT_MODEL=gpt-4o-transcribe \
VOICEAGENT_OPENAI_LLM_MODEL=gpt-4.1-mini \
VOICEAGENT_OPENAI_TTS_MODEL=gpt-4o-mini-tts \
uvicorn voiceagent_api.app:app --app-dir apps/api/src --reload
```

Current runtime behavior:
- `input_text` bypasses STT and goes directly into the turn pipeline.
- `audio_ref` is resolved as a local file path for OpenAI transcription.
- Synthesized audio is written to `VOICEAGENT_RUNTIME_AUDIO_DIR`.
- If `VOICEAGENT_OPENAI_API_KEY` is empty, VoiceAgent falls back to stub adapters.

### Complete a Call

```bash
curl -X POST http://localhost:8000/v1/calls/{call_id}/complete \
  -H "Authorization: Bearer dev-secret-key" \
  -H "Idempotency-Key: complete-001" \
  -H "Content-Type: application/json" \
  -d '{
    "outcome": "booking_created",
    "duration_ms": 183000,
    "recording_available": true,
    "summary_text": "Client booked a consultation"
  }'
```

## Webhooks

### Create a Webhook

```bash
curl -X POST http://localhost:8000/v1/webhooks \
  -H "Authorization: Bearer dev-secret-key" \
  -H "Idempotency-Key: webhook-001" \
  -H "Content-Type: application/json" \
  -d '{
    "target_url": "https://example.com/webhooks/voiceagent",
    "event_types": ["booking.created", "agent.published", "call.ended"]
  }'
```

Store the returned webhook secret securely. List and delete endpoints do not return it again.

### Verify Webhook Signature

```python
import hashlib, hmac

def verify(payload: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
```

## Configuration

All settings use the `VOICEAGENT_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `VOICEAGENT_ENV` | `development` | Environment name |
| `VOICEAGENT_LOG_LEVEL` | `INFO` | Logging level |
| `VOICEAGENT_DATABASE_URL` | `sqlite+pysqlite:///./voiceagent.db` | Database connection |
| `VOICEAGENT_API_KEYS` | See `.env.example` | Bootstrap API keys |
| `VOICEAGENT_ALLOWED_ORIGINS` | `*` | CORS allowed origins |
| `VOICEAGENT_ALLOWED_HOSTS` | `*` | Allowed host headers |
| `VOICEAGENT_DB_POOL_SIZE` | `5` | DB connection pool size |
| `VOICEAGENT_RUNTIME_AUDIO_DIR` | `runtime_audio` | Local directory for synthesized audio |
| `VOICEAGENT_OPENAI_API_KEY` | Empty | Enables OpenAI runtime adapters when set |
| `VOICEAGENT_OPENAI_STT_MODEL` | `gpt-4o-transcribe` | Speech-to-text model |
| `VOICEAGENT_OPENAI_LLM_MODEL` | `gpt-4.1-mini` | Turn-generation model |
| `VOICEAGENT_OPENAI_TTS_MODEL` | `gpt-4o-mini-tts` | Speech synthesis model |
| `VOICEAGENT_OPENAI_TTS_RESPONSE_FORMAT` | `mp3` | Output format for generated audio |

## Debugging

### Enable Debug Logging

```bash
VOICEAGENT_LOG_LEVEL=DEBUG uvicorn voiceagent_api.app:app --app-dir apps/api/src --reload
```

### Check Database

```bash
sqlite3 voiceagent.db ".tables"
sqlite3 voiceagent.db "SELECT * FROM agents;"
```

### Worker Logs

```bash
PYTHONPATH=apps/api/src python -m voiceagent_api.worker --once
```

## Production Deployment

### Environment Variables

```bash
VOICEAGENT_ENV=production
VOICEAGENT_DATABASE_URL=postgresql+psycopg://user:pass@host:5432/voiceagent
VOICEAGENT_ALLOWED_ORIGINS=https://yourdomain.com
VOICEAGENT_ALLOWED_HOSTS=api.yourdomain.com
VOICEAGENT_API_KEYS=your-secure-key,all-scopes
```

### Docker

```bash
docker compose up -d
```

### Kubernetes

```bash
kubectl apply -f k8s/
```
