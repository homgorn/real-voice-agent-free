# VoiceAgent API Surface v1

Дата: 9 марта 2026

Base path:

- `/v1`

Auth:

- dashboard session auth
- `Authorization: Bearer <api_key>` for server-to-server

Common rules:

- JSON only
- tenant-scoped resources
- idempotency key header required for critical POST operations
- pagination on list endpoints
- `trace_id` returned on error responses where possible

## 1. Core Resources

### Organizations

- `GET /v1/organizations/current`
- `PATCH /v1/organizations/current`

### API Keys

- `GET /v1/api-keys`
- `POST /v1/api-keys`
- `DELETE /v1/api-keys/{key_id}`

### Billing

- `GET /v1/plans`
- `GET /v1/subscriptions`
- `GET /v1/licenses`
- `POST /v1/licenses/validate`
- `POST /v1/billing/lemonsqueezy/webhook`

### Agents

- `GET /v1/agents`
- `POST /v1/agents`
- `GET /v1/agents/{agent_id}`
- `PATCH /v1/agents/{agent_id}`
- `POST /v1/agents/{agent_id}/publish`
- `POST /v1/agents/{agent_id}/rollback`

### Agent Versions

- `GET /v1/agents/{agent_id}/versions`
- `GET /v1/agents/{agent_id}/versions/{version_id}`

### Templates

- `GET /v1/templates`
- `POST /v1/templates/{template_id}/instantiate`

### Phone Numbers

- `GET /v1/phone-numbers`
- `POST /v1/phone-numbers`
- `PATCH /v1/phone-numbers/{number_id}`

### Calls

- `GET /v1/calls`
- `POST /v1/calls`
- `GET /v1/calls/{call_id}`
- `GET /v1/calls/{call_id}/turns`
- `POST /v1/calls/{call_id}/turns`
- `POST /v1/calls/{call_id}/respond`
- `GET /v1/calls/{call_id}/transcript`
- `GET /v1/calls/{call_id}/summary`
- `POST /v1/calls/{call_id}/complete`

### Bookings

- `GET /v1/bookings`
- `POST /v1/bookings`
- `GET /v1/bookings/{booking_id}`
- `PATCH /v1/bookings/{booking_id}`

### Knowledge Bases

- `GET /v1/knowledge-bases`
- `POST /v1/knowledge-bases`
- `POST /v1/knowledge-bases/{kb_id}/documents`

### Integrations

- `GET /v1/integrations`
- `POST /v1/integrations/{provider}/connect`
- `POST /v1/integrations/{provider}/test`

### Usage

- `GET /v1/usage`
- `GET /v1/usage/costs`

### Webhooks

- `GET /v1/webhooks`
- `POST /v1/webhooks`
- `GET /v1/webhooks/{webhook_id}/deliveries`
- `POST /v1/webhooks/deliveries/process`
- `POST /v1/webhooks/{webhook_id}/deliveries/{delivery_id}/retry`
- `POST /v1/webhooks/{webhook_id}/test`
- `DELETE /v1/webhooks/{webhook_id}`

### Events

- `GET /v1/events`

### Partner / Agency

- `GET /v1/partners/current`
- `GET /v1/partners/current/accounts`
- `POST /v1/partners/current/accounts`

## 2. Example: Create Agent

```json
POST /v1/agents
{
  "name": "Main Receptionist",
  "template_id": "tpl_receptionist_booking_v1",
  "timezone": "Asia/Almaty",
  "default_language": "ru",
  "business_hours": {
    "mon_fri": ["09:00-18:00"]
  }
}
```

Response:

```json
{
  "id": "agt_123",
  "status": "draft",
  "published_version_id": null
}
```

## 3. Example: Publish Agent

```json
POST /v1/agents/agt_123/publish
{
  "target_environment": "production"
}
```

Response:

```json
{
  "agent_id": "agt_123",
  "version_id": "ver_007",
  "status": "published"
}
```

## 4. Error Shape

```json
{
  "error": {
    "code": "integration_timeout",
    "message": "Calendar provider timed out",
    "category": "integration",
    "trace_id": "trc_123"
  }
}
```

## 5. Out of Scope for v1

- public embedded client SDK
- bulk import APIs
- advanced search/filter grammar
- full admin APIs for enterprise governance
