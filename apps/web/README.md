# Web App

Control plane UI for VoiceAgent operators.

## Current scope
- Connects to `GET /v1/dashboard/overview`
- Creates agents from templates and publishes drafts
- Runs test call simulations through `create -> respond -> complete`
- Creates and reviews bookings
- Manages phone numbers and calendar integrations
- Inspects transcripts and summaries for recent calls

## Local run
```bash
python -m http.server 4173 -d apps/web
```

Open [http://localhost:4173](http://localhost:4173), then enter:
- API base URL, for example `http://localhost:8000`
- Bearer API key, for example `dev-secret-key`

## Why this exists
This control plane is meant to express product logic, not duplicate raw CRUD. The browser consumes backend summaries, runs operator workflows, and keeps the business rules concentrated in the API wherever possible.
