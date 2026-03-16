# VoiceAgent: Product Strategy, OSS/Paid Split, API, Affiliate, Competitor Research

Date: March 9, 2026

## 1. Executive Summary

The current `spec.txt` has the right ambition, but the wrong first-release shape.

What is strong in the spec:

- clear ICP hypothesis: SMB service businesses, especially cafes/restaurants
- strong monetization instinct: subscriptions, setup fees, templates, API access
- useful distribution ideas: free trial, referrals, partner channel
- correct product direction: fast deployment, no-code/low-code setup, voice + analytics + integrations

What is weak in the spec:

- MVP is overloaded with enterprise infrastructure
- too many third-party components for a first release
- unclear moat if the product is just "another wrapper over voice AI APIs"
- no strict split between OSS value and paid value
- too much emphasis on infrastructure tools, not enough on product control, debugging, safety, and ROI proof

Core recommendation:

- build a narrow, opinionated SMB voice-agent platform
- ship two products from day one:
  - `OSS Core`: self-hosted, developer-friendly, minimal visual builder, API, basic integrations
  - `Cloud / Pro`: hosted control plane, advanced analytics, team features, white-label/agency tools, audit logs, templates, partner billing, premium support
- own the orchestration layer and domain workflows; do not make Vapi/Retell/Voximplant your moat

The biggest opportunity from competitor weakness is not "better AI quality" alone.
It is:

- better production observability
- better handoff to humans
- lower surprise cost at scale
- simpler SMB onboarding
- stronger localized templates and ROI instrumentation

## 2. What To Change In The Current Spec

### 2.1 Remove from MVP

These items are too heavy for first release:

- Jenkins
- Apache Airflow
- Keycloak
- ELK Stack
- Portainer
- full Kubernetes-first deployment
- separate Rasa intent layer for everything

Why:

- they increase ops burden faster than they increase product value
- they slow down iteration on the actual product
- they make OSS adoption harder
- they are unnecessary before product-market fit

### 2.2 Replace with a leaner stack

Recommended v1 stack:

- Backend: FastAPI
- Async jobs: Celery or Dramatiq
- Database: PostgreSQL
- Cache / queues / ephemeral state: Redis
- Realtime/event bus: Postgres + Redis first, NATS only if proven necessary
- Frontend: React + a component system, not just raw Tailwind sprawl
- Auth: app-native org/user/API key auth first
- Observability: OpenTelemetry + structured logs + Sentry + PostHog or ClickHouse-based analytics
- Storage: S3-compatible object storage for call recordings and artifacts
- Deploy: Docker Compose for OSS, managed containers for Cloud; add Kubernetes only when concurrency or multi-region justifies it

### 2.3 Change the AI architecture

The spec is too "2023 platform stack": Botpress + LangChain + Rasa + Whisper + Coqui + Kubernetes + ELK.

A stronger 2026 approach:

- use LLM-driven tool calling for dialog execution
- keep deterministic workflow/state machines for critical business actions
- make STT/TTS/LLM pluggable
- treat prompting, tools, KB retrieval, and policy checks as first-class config
- make every call debuggable turn-by-turn

The product should be:

- agentic where flexibility helps
- deterministic where money, booking, lead capture, compliance, and routing matter

## 3. Recommended Product Shape

## 3.1 Product Thesis

Do not sell "voice AI".
Sell:

- missed-call recovery
- booking automation
- lead qualification
- after-hours answering
- FAQ deflection with escalation
- appointment reminders and confirmation
- post-call summaries and CRM sync

This is easier to buy, easier to measure, and easier to template.

## 3.2 Primary ICP

Rank ICPs in this order:

1. clinics / dental / beauty / wellness
2. restaurants with reservations or delivery intake
3. home services
4. agencies serving those businesses

Reason:

- repetitive calls
- clear ROI
- easy template standardization
- high sensitivity to missed calls

## 3.3 Packaging: OSS vs Paid

### OSS Core

Goal: adoption, credibility, developer community, integration surface.

Include:

- self-hostable API server
- call/workflow engine
- basic prompt/tool/workflow editor
- provider adapters for STT/TTS/LLM
- SIP/telephony connector abstraction
- basic transcripts and logs
- API keys and webhook support
- 1-2 starter templates
- import/export of agent definitions

Do not include in OSS:

- hosted billing
- advanced analytics
- team RBAC / audit log
- white-label portal
- multi-tenant agency dashboard
- premium templates
- managed knowledge sync
- SLA/support
- advanced QA/evals
- revenue attribution dashboards

### Paid Cloud / Pro

Goal: monetization and operational leverage.

Include:

- hosted multi-tenant control plane
- advanced observability and call replay
- prompt/version diffing and rollback
- sandbox vs production environments
- team permissions and audit logs
- white-label agency mode
- branded widgets and customer portal
- usage billing
- advanced integrations
- managed template library
- QA scoring / evals / anomaly detection
- human handoff inbox
- premium onboarding

### Enterprise

Add only when pulled by demand:

- private deployment
- BYOC/BYOK
- custom data retention
- regional deployment
- SSO/SAML
- signed DPAs and SLAs

## 4. Your Moat

Do not compete on "we also support voice agents".

Compete on:

- vertical templates with business logic
- localization for Russian/CIS and multilingual SMBs
- better debugging than Vapi/Synthflow-class tools
- better handoff and operator tooling than builder-first platforms
- transparent unit economics
- open core credibility
- easy API + agency resale workflow

Your moat should be:

1. orchestration layer
2. business templates
3. observability and QA
4. partner distribution
5. OSS adoption funnel

## 5. Own API: What It Should Look Like

Your API should exist even if you have a no-code UI.

### 5.1 API principles

- everything in UI must also be available by API
- versioned from day one: `/v1`
- tenant-scoped
- idempotent for critical writes
- event-driven via webhooks
- import/export friendly

### 5.2 Core entities

- `organizations`
- `users`
- `api_keys`
- `agents`
- `workflows`
- `knowledge_bases`
- `tools`
- `phone_numbers`
- `calls`
- `transcripts`
- `bookings`
- `contacts`
- `integrations`
- `events`
- `usage_records`
- `plans`
- `licenses`
- `partners`
- `referrals`

### 5.3 Minimum endpoints

- `POST /v1/agents`
- `GET /v1/agents/:id`
- `POST /v1/agents/:id/publish`
- `POST /v1/calls`
- `GET /v1/calls/:id`
- `GET /v1/calls/:id/transcript`
- `POST /v1/webhooks/test`
- `POST /v1/integrations/:provider/connect`
- `POST /v1/knowledge-bases`
- `POST /v1/bookings`
- `GET /v1/usage`
- `GET /v1/audit-events`

### 5.4 Webhooks

Must-have webhook events:

- `call.started`
- `call.ended`
- `call.escalated`
- `call.failed`
- `booking.created`
- `booking.updated`
- `lead.captured`
- `invoice.payment_succeeded`
- `subscription.activated`
- `subscription.canceled`
- `license.validated`
- `partner.referral.created`

### 5.5 Auth

- dashboard auth for humans
- API keys for server-to-server
- short-lived signed tokens for embeddable clients
- scoped permissions for agency/customer separation

## 6. Billing and Licensing

## 6.1 Lemon Squeezy recommendation

Lemon Squeezy is a strong fit if your commercial product is sold globally as SaaS/software.

Why it fits:

- merchant-of-record model reduces tax/VAT burden
- subscription APIs exist
- webhook support exists
- customer portal exists
- license key APIs exist
- affiliate support exists
- test mode exists

Relevant docs checked on March 9, 2026:

- API reference: https://docs.lemonsqueezy.com/api
- subscriptions: https://docs.lemonsqueezy.com/help/products/subscriptions
- webhooks: https://docs.lemonsqueezy.com/help/webhooks
- customer portal: https://docs.lemonsqueezy.com/help/online-store/customer-portal
- license API: https://docs.lemonsqueezy.com/api/license-api
- affiliate endpoints: https://docs.lemonsqueezy.com/api/affiliates/list-all-affiliates

Important constraints:

- standard pricing is not cheap at scale: base platform fee is listed as `5% + 50c`, with extra fees in some cases
- merchant affiliate referrals add `+3%`
- affiliate payouts have their own fee structure
- payouts are batched, not instant

Relevant docs:

- pricing: https://www.lemonsqueezy.com/pricing
- fees: https://docs.lemonsqueezy.com/help/getting-started/fees
- merchant affiliate fees: https://docs.lemonsqueezy.com/help/affiliates-for-merchants/fees
- supported countries / payouts: https://docs.lemonsqueezy.com/help/getting-started/supported-countries

Recommendation:

- use Lemon Squeezy for `Cloud/Pro` and agency subscriptions
- use Lemon Squeezy license keys only for paid self-hosted editions
- do not force OSS users through Lemon Squeezy
- if your real buyer base becomes heavily Russia/CIS-only, keep a backup payment rail plan because Lemon Squeezy is best aligned with global SaaS, not local offline SMB collections

## 6.2 Pricing model recommendation

Do not price mainly by "number of skills".
Price by business value and usage.

Recommended pricing dimensions:

- base monthly platform fee
- included minutes / conversations
- included phone numbers / channels
- included seats
- included environments
- add-ons for extra minutes, extra numbers, premium integrations, white-label

Suggested first structure:

- `OSS`: free, self-hosted, no hosted support
- `Starter`: one location, one primary use case, basic analytics
- `Growth`: multi-location, CRM/calendar integrations, call replay, QA
- `Agency`: subaccounts, white-label, margin/resale controls
- `Enterprise`: private deployment / BYOC / custom SLA

## 7. Affiliate and Partner Program

You need two parallel channels:

- affiliate program
- reseller / agency partner program

These are not the same thing.

### 7.1 Affiliate

Best for:

- creators
- newsletters
- YouTubers
- consultants
- indie builders

Use Lemon Squeezy built-in affiliates first.

Why:

- you get affiliate signup, tracking, payouts, and merchant-side management faster
- docs confirm merchant affiliate setup, referral tracking script, and affiliate APIs

Relevant docs:

- getting started: https://docs.lemonsqueezy.com/help/affiliates-for-merchants/getting-started
- managing affiliates and referrals: https://docs.lemonsqueezy.com/help/affiliates-for-merchants/managing-affiliates-and-referrals
- getting referrals: https://docs.lemonsqueezy.com/help/affiliates-for-merchants/getting-referrals
- affiliate experience: https://docs.lemonsqueezy.com/help/affiliates-for-merchants/the-affiliate-experience

Recommendation:

- start with 20% recurring commission for 12 months
- higher tier for strategic creators
- do not offer lifetime revshare at the start

### 7.2 Agency / Reseller

Best for:

- web studios
- CRM integrators
- no-code agencies
- telecom implementers

Needs beyond affiliate:

- client subaccounts
- transfer ownership
- markup / rebilling
- branded portal
- managed onboarding
- deal registration
- partner dashboard

This should be a product feature, not only a finance feature.

## 8. Deep Competitor Research

## 8.1 Competitor map

### Voice-agent API / telephony-first

- Vapi
- Retell AI
- Voximplant
- Bland AI

### No-code / agency / ops platforms

- Synthflow
- Voiceflow
- Botpress

### OSS / self-host / telephony infrastructure

- jambonz

## 8.2 What competitors are promising

### Vapi

Official positioning checked March 9, 2026:

- "voice AI agents for developers"
- claims `300M+` calls and `2.5M+` assistants launched
- strong API-first posture
- tools, provider resources, observability integrations, free US phone numbers

Sources:

- https://vapi.ai/
- https://docs.vapi.ai/api-reference//
- https://docs.vapi.ai/tools/
- https://docs.vapi.ai/providers/observability/langfuse
- https://docs.vapi.ai/free-telephony

### Retell AI

Official positioning checked March 9, 2026:

- build, test, deploy, monitor AI phone agents
- supports simulation testing, SIP, phone calls, webhooks
- official Node and Python SDKs
- published pay-as-you-go pricing from `0.07+/minute`

Sources:

- https://docs.retellai.com/
- https://docs.retellai.com/get-started/sdk
- https://www.retellai.com/pricing

### Synthflow

Official positioning checked March 9, 2026:

- "Voice AI OS"
- strong no-code and agency/white-label angle
- claims in-house telephony and sub-100 ms latency
- PAYG docs list `0.15-0.24` per minute and 5 concurrency units

Sources:

- https://synthflow.ai/
- https://docs.synthflow.ai/pay-as-you-go
- https://synthflow.ai/ghl

### Voximplant

Official positioning checked March 9, 2026:

- voice AI orchestration platform
- deep SIP and telephony connectivity
- serverless orchestration
- explicit pricing for SIP, streaming, speech, connectors

Sources:

- https://voximplant.ai/
- https://voximplant.com/pricing
- https://voximplant.com/docs/guides/ai

### Voiceflow

Official positioning checked March 9, 2026:

- build, manage, and deliver chat and voice agents
- strong business/agency collaboration and observability posture
- supports phone, APIs, KB, transcripts, evaluations, call forwarding

Sources:

- https://www.voiceflow.com/pricing
- https://docs.voiceflow.com/
- https://docs.voiceflow.com/docs/call-forwarding-step

### Botpress

Official positioning checked March 9, 2026:

- visual studio + AI spend pricing
- human handoff is a paid feature
- no full studio/dashboard white-label

Sources:

- https://botpress.com/pricing
- https://botpress.com/en/features/human-handoff

### jambonz

Official positioning checked March 9, 2026:

- self-hosted open-source CPaaS
- BYO everything
- privacy-centric
- white-labelable

Sources:

- https://jambonz.github.io/
- https://docs.jambonz.org/self-hosting/overview
- https://www.jambonz.org/

## 8.3 Repeated negative feedback patterns

### Pattern A: high latency / awkward conversational timing

Observed around Vapi, Voximplant-class setups, and forum discussions about production voice stacks.

Examples:

- Vapi users reporting phone delays closer to 2-3 seconds in real calls despite better dashboard numbers
- Voximplant reviewers mentioning delays or robotic call feel

Sources:

- https://www.reddit.com/r/vapiai/comments/1jugvu0
- https://www.reddit.com/r/AI_Agents/comments/1jugufv
- https://www.g2.com/products/voximplant/reviews

Product implication:

- make latency visible per turn, not just abstract dashboard averages
- show "time to first word", interruption timing, webhook delay, model delay, telephony delay

### Pattern B: debugging is painful

Observed around Retell, Vapi, Synthflow.

Examples:

- Retell reviews mention unclear error messages, weak debugging visibility, advanced docs gaps, and even support complaints when API changes broke production
- Vapi forum/reddit comments describe the stack as hard to debug in real calls
- Synthflow reviews mention weak analytics and integration pain

Sources:

- https://www.g2.com/products/retell-ai/reviews
- https://www.g2.com/products/retell-ai/pricing
- https://www.reddit.com/r/AI_Agents/comments/1qp5615/build_your_ai_voice_agent_using_vapi/
- https://www.g2.com/products/synthflow/reviews

Product implication:

- build "why this call failed" as a first-class feature
- for every turn, log transcript, tool invocation, model instruction version, latency, confidence, and fallback outcome

### Pattern C: pricing gets ugly at volume

Observed around Retell, Synthflow, Vapi, Lemon Squeezy itself on the billing side.

Examples:

- Retell reviews repeatedly say pricing adds up with high volume
- Synthflow reviews cite high pricing and fast cost growth
- Vapi support docs describe platform fees plus pass-through provider costs

Sources:

- https://www.g2.com/products/retell-ai/reviews
- https://www.retellai.com/pricing
- https://www.g2.com/products/synthflow/reviews
- https://docs.synthflow.ai/pay-as-you-go
- https://support.vapi.ai/t/27132870/pricing

Product implication:

- expose unit economics per agent and per customer account
- build cost guardrails, rate caps, minute alerts, and model routing policies

### Pattern D: too technical for non-developers

Observed around Vapi, Botpress, Retell, and even Synthflow once flows get advanced.

Examples:

- Vapi review says dashboard is difficult and needs a basic vs advanced mode
- Retell reviews say non-technical users will struggle
- Botpress reviews mention steep learning curve and confusing settings
- Synthflow 1.5-star review says setup required an in-house developer

Sources:

- https://www.g2.com/products/vapi-ai/reviews
- https://www.g2.com/products/retell-ai/reviews
- https://www.g2.com/products/botpress/reviews
- https://www.g2.com/products/synthflow/reviews
- https://www.capterra.com/p/199292/Botpress/reviews/

Product implication:

- split product into operator mode and builder mode
- do not expose raw AI plumbing to SMBs
- guided onboarding must produce a working receptionist in under 15 minutes

### Pattern E: poor human handoff / conversation management

Observed in Botpress and Voiceflow review data.

Examples:

- Botpress reviewers complain about weak conversation management and needing custom frontend/inbox behavior
- Voiceflow reviewers mention missing or incomplete human-in-loop/conversation-transfer capabilities for serious use

Sources:

- https://www.g2.com/products/botpress/reviews
- https://www.g2.com/products/voiceflow/reviews
- https://docs.voiceflow.com/docs/call-forwarding-step
- https://botpress.com/en/features/human-handoff

Product implication:

- your product should ship with a real operator console, not just a builder
- human handoff must preserve transcript, slots, extracted fields, recommended next action, and customer profile

### Pattern F: customization ceilings

Observed in Synthflow, Voximplant no-code feedback, Voiceflow scale feedback, Botpress.

Examples:

- Synthflow reviews say complex logic hits boundaries
- Voximplant reviews say customization is limited without code
- Voiceflow reviews mention clutter and scalability pain in large projects

Sources:

- https://www.g2.com/products/synthflow/reviews
- https://www.g2.com/products/voximplant/reviews
- https://www.g2.com/products/voiceflow/reviews

Product implication:

- make workflows composable
- support reusable subflows
- allow no-code defaults and code escape hatches

## 8.4 Competitor weaknesses you can directly exploit

Build these as explicit product advantages:

1. `Explainability`
   - every failure mapped to telephony / STT / LLM / tool / policy / integration layer
2. `Operator handoff`
   - one-click live transfer with context pack
3. `Cost controls`
   - budget policies, provider routing, guardrails
4. `SMB onboarding`
   - template wizard by business type
5. `Localized vertical templates`
   - booking, FAQ, callback, reminder, lead capture
6. `Open core credibility`
   - self-hostable engine plus paid hosted control plane

## 9. Concrete Product Improvements Over The Current Spec

### 9.1 Replace "AI-generated dialog trees" with "goal-driven workflow packs"

Better framing:

- reception
- booking
- lead qualification
- reminder
- missed-call recovery
- call summary and CRM update

Why:

- users buy outcomes, not trees

### 9.2 Add production QA from day one

Must-have features:

- transcript replay
- audio replay
- step timeline
- tool invocation trace
- redaction
- prompt/version history
- regression test sets

### 9.3 Add a real "operator console"

Must-have:

- active calls
- escalated calls
- missed intents
- recommended actions
- callback queue
- agent health

### 9.4 Add "ROI mode"

SMB needs proof.

Track:

- missed calls recovered
- bookings created
- bookings confirmed
- leads captured
- average handle time saved
- deflection rate
- after-hours answer coverage

### 9.5 Add "agency mode"

Must-have:

- subaccounts
- usage per client
- branding
- deployment templates
- permission boundaries
- optional markup/rebilling

## 10. Recommended Architecture

## 10.1 Control plane vs execution plane

Separate these early.

### Control plane

- users
- orgs
- UI
- agent config
- KB config
- integrations config
- analytics
- billing

### Execution plane

- live calls
- realtime state
- tool execution
- recording/transcription pipeline
- retries and failover

Why:

- easier OSS vs paid split
- easier scale path
- easier hosted/private deployment later

## 10.2 Provider abstraction

You need adapters for:

- telephony
- STT
- TTS
- LLM
- calendar
- CRM
- messaging

This lets you:

- ship fast with commercial providers
- preserve the option of OSS/self-host alternatives
- reduce vendor risk

## 10.3 OSS telephony recommendation

For open-core telephony, `jambonz` is strategically interesting because it is explicitly open-source, self-hosted, privacy-centric, and white-labelable.

It is a better architectural reference for OSS telephony control than building your core business entirely on Vapi or Retell.

Sources:

- https://jambonz.github.io/
- https://docs.jambonz.org/self-hosting/overview

## 11. 90-Day Plan

## Phase 1: 0-30 days

- narrow ICP to one vertical
- define OSS/Paid boundary in writing
- define API schema and event model
- define provider adapter interfaces
- build basic hosted control plane skeleton
- ship first template: `AI receptionist + booking + human transfer`

## Phase 2: 31-60 days

- add transcripts, replay, and event timeline
- add calendar integration
- add webhook framework
- add operator console
- add Lemon Squeezy billing and licensing
- add affiliate setup

## Phase 3: 61-90 days

- add agency mode
- add eval/test suite
- add second template pack
- onboard first design partners
- instrument ROI dashboards

## 12. Final Recommendation

The current spec should be rewritten around this thesis:

`VoiceAgent is an open-core voice automation platform for SMB service businesses, with a self-hosted execution engine and a paid hosted control plane for analytics, operations, billing, and partner distribution.`

If you keep the current spec mostly as-is, you risk:

- building too much infrastructure before shipping value
- depending on too many tools at once
- launching a platform that is technically impressive but commercially generic

If you apply the changes above, you get:

- a cleaner repo strategy
- a defendable OSS/Paid split
- a practical API-first product
- a partner-friendly revenue model
- a stronger position against Vapi / Retell / Synthflow / Voiceflow / Botpress

## 13. Source Notes

This document combines:

- local review of `spec.txt`
- official vendor docs and pricing pages checked on March 9, 2026
- public review summaries from G2/Capterra
- public Reddit/forum discussions used as directional market signals, not as audited fact

Use caution with forum evidence:

- G2/Capterra data is stronger than Reddit
- Reddit comments are useful for pattern detection, especially around latency, support, and debugging, but should not be treated as conclusive proof on their own
