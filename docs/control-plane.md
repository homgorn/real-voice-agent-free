# Control Plane

The web control plane lives in `apps/web` and is meant for operators, founders, or support teams running VoiceAgent.

## Current Workflows

- connect to API with a bearer key
- review dashboard summary and launch blockers
- create and publish agents
- run simulated calls
- inspect transcripts and summaries
- create bookings
- review suggested availability slots
- manage phone numbers
- connect and test calendar integrations

## Why It Exists

The control plane expresses business logic already implemented in the backend. It is not intended to become a disconnected CRUD layer.

## Local Run

```bash
python -m http.server 4173 -d apps/web
```

Then open `http://localhost:4173`.

## Current State

Useful for operations and demos, but not yet a fully hardened production SPA.

## Related Docs

- [../apps/web/README.md](../apps/web/README.md)
- [api-quickstart.md](api-quickstart.md)
- [scheduling-and-bookings.md](scheduling-and-bookings.md)
