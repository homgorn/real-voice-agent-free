# BMAD Assets To Use For VoiceAgent

Date: March 9, 2026

## Why BMAD matters here

`VoiceAgent` sits inside a larger BMAD workspace, and that workspace already contains useful reusable assets:

- analyst workflows for market, domain, and technical research
- PM workflows for product brief and PRD creation
- architect workflows for architecture decision records
- agent personas that enforce role separation
- platform-level principles for modularity, observability, and provider abstraction

This means we should not run the project as a loose set of notes.
We should run it through a repeatable BMAD-style pipeline.

## Relevant local BMAD assets

### Research workflows

Located under `D:\bmad-project\_bmad\bmm\workflows\1-analysis\research\`

Most relevant:

- `workflow-market-research.md`
- `workflow-domain-research.md`
- `workflow-technical-research.md`

Use for `VoiceAgent`:

- competitor research
- negative review pattern collection
- telephony/provider tradeoff analysis
- ICP and buyer decision analysis

### Product brief workflow

Located under `D:\bmad-project\_bmad\bmm\workflows\1-analysis\create-product-brief\`

Most relevant:

- `workflow.md`
- `product-brief.template.md`

Use for `VoiceAgent`:

- convert the current idea and `spec.txt` into a shorter, executive-grade product brief
- force clarity on vision, users, scope, and metrics

### PRD workflows

Referenced via:

- `D:\bmad-project\_bmad\bmm\agents\pm.md`
- `D:\bmad-project\.agents\skills\bmad-bmm-create-prd\SKILL.md`

Use for `VoiceAgent`:

- produce the real PRD after brief and research are stable
- keep requirements tied to user outcomes, not random feature expansion

### Architecture workflows

Referenced via:

- `D:\bmad-project\_bmad\bmm\workflows\3-solutioning\create-architecture\workflow.md`
- `D:\bmad-project\_bmad\bmm\agents\architect.md`
- `D:\bmad-project\.agents\skills\bmad-bmm-create-architecture\SKILL.md`

Use for `VoiceAgent`:

- document control plane vs execution plane
- provider adapter boundaries
- event model
- deployment model for OSS vs Cloud

### Analyst / PM / Architect roles

Most relevant local personas:

- `D:\bmad-project\_bmad\bmm\agents\analyst.md`
- `D:\bmad-project\_bmad\bmm\agents\pm.md`
- `D:\bmad-project\_bmad\bmm\agents\architect.md`

Recommended use:

- `Analyst`: market, competitor, ICP, partner channel, pricing pressure
- `PM`: edition design, packaging, onboarding, conversion funnel, metrics
- `Architect`: API, services, providers, tenancy, execution/runtime model

### Platform principles already aligned with VoiceAgent

Relevant docs:

- `D:\bmad-project\docs\platform\ru\ai-platform-vision.md`
- `D:\bmad-project\docs\platform\ru\architecture.md`

Useful principles already present there:

- modular core with plugins/adapters
- observability by default
- security and secret handling as first-class concerns
- agentic orchestration with human-in-the-loop
- model/provider abstraction layer

These align well with `VoiceAgent` and should be adopted rather than reinvented.

## What this changes for VoiceAgent

We should structure project planning in BMAD order:

1. research
2. product brief
3. PRD
4. architecture
5. epics and stories
6. implementation

That is better than jumping from a raw spec directly into code.

## Recommended artifacts to create next

### 1. Product brief

Target path:

- `prd/product-brief-v1.md`

Purpose:

- one crisp statement of problem, ICP, value proposition, scope, metrics, and exclusions

### 2. PRD

Target path:

- `prd/prd-v1.md`

Purpose:

- define edition matrix, user journeys, functional requirements, constraints, non-goals

### 3. Architecture

Target path:

- `docs/architecture-v1.md`

Purpose:

- define API surface, service boundaries, provider adapters, data model, runtime model

### 4. Contracts

Target paths:

- `contracts/api-surface-v1.md`
- `contracts/event-schema-v1.md`
- `contracts/provider-adapter-interface-v1.md`

Purpose:

- freeze interfaces before implementation sprawls

### 5. Backlog

Target paths:

- `backlog/epics-v1.md`
- `backlog/stories-sprint-01.md`

Purpose:

- move from strategy to build order

## How to use BMAD without slowing down

Do not import the entire BMAD system into the repo.
Do this instead:

- reuse the workflow logic
- borrow the document sequence
- keep the output documents local to `voiceagent`
- avoid unnecessary ceremony unless it directly sharpens implementation decisions

## Practical next sequence for this repo

Recommended order:

1. freeze `OSS / Pro / Agency` edition boundary
2. create product brief
3. create PRD
4. create architecture
5. define contracts
6. create sprint backlog

## Conclusion

The BMAD workspace around this repo is useful and should be treated as a local playbook.

For `VoiceAgent`, the most valuable pieces are not exotic prompt tricks.
They are:

- research workflows
- PM/architect role separation
- document sequencing
- architecture and observability principles

That gives this repo a cleaner path from idea to implementation.
