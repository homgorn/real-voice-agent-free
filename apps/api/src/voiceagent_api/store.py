from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4

from sqlalchemy import func, or_, select

from voiceagent_api.adapters.calendar import CalendarBookingRequest, CalendarBookingUpdateRequest, get_calendar_adapter
from voiceagent_api.auth import hash_api_key
from voiceagent_api.config import settings
from voiceagent_api.db import create_database, drop_database, ping_database, SessionLocal
from voiceagent_api.errors import IdempotencyConflictError, NotFoundError
from voiceagent_api.lemonsqueezy import extract_event_metadata
from voiceagent_api.models import (
    AgentModel,
    AgentVersionModel,
    ApiKeyModel,
    BillingWebhookEventModel,
    BookingModel,
    CallModel,
    CallSummaryModel,
    CallTurnModel,
    EventModel,
    IntegrationModel,
    IdempotencyKeyModel,
    KnowledgeBaseDocumentModel,
    KnowledgeBaseModel,
    LicenseModel,
    OrganizationModel,
    PartnerAccountModel,
    PartnerModel,
    PlanModel,
    PhoneNumberModel,
    SubscriptionModel,
    TemplateModel,
    WebhookDeliveryModel,
    WebhookSubscriptionModel,
)
from voiceagent_api.runtime import RuntimeTurnRequest, runtime_orchestrator
from voiceagent_api.schemas import (
    AgentCreateRequest,
    AgentUpdateRequest,
    ApiKeyCreateRequest,
    BookingCreateRequest,
    BookingUpdateRequest,
    CallCompleteRequest,
    CallCreateRequest,
    CallRespondRequest,
    CallTurnCreateRequest,
    IntegrationConnectRequest,
    KnowledgeBaseCreateRequest,
    KnowledgeBaseDocumentCreateRequest,
    OrganizationUpdateRequest,
    PartnerAccountCreateRequest,
    PhoneNumberCreateRequest,
    PhoneNumberUpdateRequest,
    TemplateInstantiateRequest,
    WebhookCreateRequest,
)
from voiceagent_api.webhooks import dispatcher


def _parse_optional_datetime(value):
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    return None


def _serialize_agent(model: AgentModel) -> dict:
    return {
        "id": model.id,
        "name": model.name,
        "template_id": model.template_id,
        "timezone": model.timezone,
        "default_language": model.default_language,
        "business_hours": model.business_hours or {},
        "status": model.status,
        "published_version_id": model.published_version_id,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _serialize_version(model: AgentVersionModel) -> dict:
    return {
        "version_id": model.version_id,
        "agent_id": model.agent_id,
        "target_environment": model.target_environment,
        "created_at": model.created_at,
        "snapshot": model.snapshot,
    }


def _serialize_template(model: TemplateModel) -> dict:
    return {
        "id": model.id,
        "name": model.name,
        "description": model.description,
        "default_language": model.default_language,
        "timezone": model.timezone,
        "business_hours": model.business_hours or {},
        "definition": model.definition or {},
        "is_active": model.is_active,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _serialize_booking(model: BookingModel) -> dict:
    return {
        "id": model.id,
        "agent_id": model.agent_id,
        "contact_name": model.contact_name,
        "contact_phone": model.contact_phone,
        "service": model.service,
        "start_at": model.start_at,
        "status": model.status,
        "external_booking_id": model.external_booking_id,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _serialize_event(model: EventModel) -> dict:
    return {
        "event_id": model.event_id,
        "event_type": model.event_type,
        "event_version": model.event_version,
        "occurred_at": model.occurred_at,
        "trace_id": model.trace_id,
        "tenant_id": model.tenant_id,
        "source": model.source,
        "payload": model.payload,
    }


def _serialize_webhook(model: WebhookSubscriptionModel) -> dict:
    return {
        "id": model.id,
        "target_url": model.target_url,
        "event_types": model.event_types,
        "secret": model.secret,
        "is_active": model.is_active,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _serialize_delivery(model: WebhookDeliveryModel) -> dict:
    return {
        "id": model.id,
        "webhook_id": model.webhook_id,
        "event_id": model.event_id,
        "event_type": model.event_type,
        "status": model.status,
        "attempt_count": model.attempt_count,
        "response_code": model.response_code,
        "response_body": model.response_body,
        "last_attempt_at": model.last_attempt_at,
        "next_attempt_at": model.next_attempt_at,
        "last_error": model.last_error,
        "delivered_at": model.delivered_at,
        "created_at": model.created_at,
    }


def _serialize_call(model: CallModel) -> dict:
    return {
        "id": model.id,
        "agent_id": model.agent_id,
        "phone_number_id": model.phone_number_id,
        "channel": model.channel,
        "direction": model.direction,
        "from_number": model.from_number,
        "to_number": model.to_number,
        "status": model.status,
        "outcome": model.outcome,
        "duration_ms": model.duration_ms,
        "recording_available": model.recording_available,
        "started_at": model.started_at,
        "ended_at": model.ended_at,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _serialize_call_turn(model: CallTurnModel) -> dict:
    return {
        "id": model.id,
        "call_id": model.call_id,
        "turn_index": model.turn_index,
        "user_text": model.user_text,
        "assistant_text": model.assistant_text,
        "latency_ms": model.latency_ms,
        "provider_breakdown": model.provider_breakdown or {},
        "tool_calls": model.tool_calls or [],
        "response_audio_ref": model.response_audio_ref,
        "finish_reason": model.finish_reason,
        "created_at": model.created_at,
    }


def _serialize_call_summary(model: CallSummaryModel) -> dict:
    return {
        "call_id": model.call_id,
        "summary_text": model.summary_text,
        "structured_summary": model.structured_summary or {},
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _serialize_phone_number(model: PhoneNumberModel) -> dict:
    return {
        "id": model.id,
        "organization_id": model.organization_id,
        "provider": model.provider,
        "number": model.number,
        "label": model.label,
        "status": model.status,
        "capabilities": model.capabilities or {},
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _serialize_integration(model: IntegrationModel) -> dict:
    return {
        "id": model.id,
        "organization_id": model.organization_id,
        "provider": model.provider,
        "status": model.status,
        "config": model.config or {},
        "last_tested_at": model.last_tested_at,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _serialize_knowledge_base(model: KnowledgeBaseModel) -> dict:
    return {
        "id": model.id,
        "organization_id": model.organization_id,
        "name": model.name,
        "description": model.description,
        "is_active": model.is_active,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _serialize_knowledge_document(model: KnowledgeBaseDocumentModel) -> dict:
    return {
        "id": model.id,
        "knowledge_base_id": model.knowledge_base_id,
        "title": model.title,
        "content": model.content,
        "source_url": model.source_url,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _serialize_partner(model: PartnerModel) -> dict:
    return {
        "id": model.id,
        "organization_id": model.organization_id,
        "name": model.name,
        "is_active": model.is_active,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _serialize_partner_account(model: PartnerAccountModel, organization: OrganizationModel) -> dict:
    return {
        "id": model.id,
        "partner_id": model.partner_id,
        "organization_id": model.organization_id,
        "organization_name": organization.name,
        "organization_slug": organization.slug,
        "created_at": model.created_at,
    }

def _serialize_organization(model: OrganizationModel) -> dict:
    return {
        "id": model.id,
        "name": model.name,
        "slug": model.slug,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _serialize_api_key(model: ApiKeyModel) -> dict:
    return {
        "id": model.id,
        "organization_id": model.organization_id,
        "name": model.name,
        "scopes": model.scopes or [],
        "is_active": model.is_active,
        "created_at": model.created_at,
        "last_used_at": model.last_used_at,
    }


def _serialize_plan(model: PlanModel) -> dict:
    return {
        "code": model.code,
        "name": model.name,
        "price_monthly_usd": model.price_monthly_usd,
        "is_active": model.is_active,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _serialize_subscription(model: SubscriptionModel) -> dict:
    return {
        "id": model.id,
        "organization_id": model.organization_id,
        "plan_code": model.plan_code,
        "status": model.status,
        "status_formatted": model.status_formatted,
        "customer_email": model.customer_email,
        "customer_name": model.customer_name,
        "product_id": model.product_id,
        "variant_id": model.variant_id,
        "order_id": model.order_id,
        "store_id": model.store_id,
        "test_mode": model.test_mode,
        "renews_at": model.renews_at,
        "ends_at": model.ends_at,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


def _serialize_license(model: LicenseModel) -> dict:
    return {
        "id": model.id,
        "organization_id": model.organization_id,
        "subscription_id": model.subscription_id,
        "order_id": model.order_id,
        "order_item_id": model.order_item_id,
        "product_id": model.product_id,
        "variant_id": model.variant_id,
        "customer_email": model.customer_email,
        "customer_name": model.customer_name,
        "key_short": model.key_short,
        "status": model.status,
        "activation_limit": model.activation_limit,
        "activation_usage": model.activation_usage,
        "expires_at": model.expires_at,
        "created_at": model.created_at,
        "updated_at": model.updated_at,
    }


class AgentStore:
    def __init__(self) -> None:
        create_database()
        self.seed_bootstrap_security()
        self.seed_bootstrap_plans()
        self.seed_bootstrap_templates()
        self.seed_bootstrap_partner()

    def reset(self) -> None:
        drop_database()
        create_database()
        self.seed_bootstrap_security()
        self.seed_bootstrap_plans()
        self.seed_bootstrap_templates()
        self.seed_bootstrap_partner()

    def ping(self) -> None:
        ping_database()

    def seed_bootstrap_security(self) -> None:
        now = datetime.now().astimezone()
        with SessionLocal() as session:
            organization = session.get(OrganizationModel, settings.default_organization_id)
            if organization is None:
                organization = OrganizationModel(
                    id=settings.default_organization_id,
                    name=settings.default_organization_name,
                    slug=settings.default_organization_name.lower().replace(" ", "-"),
                    created_at=now,
                    updated_at=now,
                )
                session.add(organization)

            for spec in settings.bootstrap_api_keys:
                key_hash = hash_api_key(str(spec["key"]))
                existing = session.scalar(select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash))
                if existing is not None:
                    continue
                session.add(
                    ApiKeyModel(
                        id=f"key_{uuid4().hex[:8]}",
                        organization_id=settings.default_organization_id,
                        name=str(spec["name"]),
                        key_hash=key_hash,
                        scopes=list(spec["scopes"]),
                        is_active=True,
                        created_at=now,
                        last_used_at=None,
                    )
                )
            session.commit()

    def seed_bootstrap_plans(self) -> None:
        now = datetime.now().astimezone()
        defaults = [
            ("starter", "Starter", 29),
            ("growth", "Growth", 99),
            ("agency", "Agency", 299),
        ]
        with SessionLocal() as session:
            for code, name, price in defaults:
                existing = session.get(PlanModel, code)
                if existing is not None:
                    continue
                session.add(
                    PlanModel(
                        code=code,
                        name=name,
                        price_monthly_usd=price,
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                    )
                )
            session.commit()

    def seed_bootstrap_templates(self) -> None:
        now = datetime.now().astimezone()
        defaults = [
            {
                "id": "tpl_receptionist_booking_v1",
                "name": "Receptionist + Booking",
                "description": "Default receptionist flow with booking handoff.",
                "default_language": "ru",
                "timezone": "Asia/Almaty",
                "business_hours": {"mon_fri": ["09:00-18:00"]},
                "definition": {"version": "v1", "category": "reception"},
            },
            {
                "id": "tpl_faq_basic_v1",
                "name": "FAQ Answering",
                "description": "Basic FAQ responder with escalation fallback.",
                "default_language": "en",
                "timezone": "UTC",
                "business_hours": {},
                "definition": {"version": "v1", "category": "faq"},
            },
        ]
        with SessionLocal() as session:
            for spec in defaults:
                existing = session.get(TemplateModel, spec["id"])
                if existing is not None:
                    continue
                session.add(
                    TemplateModel(
                        id=spec["id"],
                        name=spec["name"],
                        description=spec["description"],
                        default_language=spec["default_language"],
                        timezone=spec["timezone"],
                        business_hours=spec["business_hours"],
                        definition=spec["definition"],
                        is_active=True,
                        created_at=now,
                        updated_at=now,
                    )
                )
            session.commit()

    def seed_bootstrap_partner(self) -> None:
        now = datetime.now().astimezone()
        with SessionLocal() as session:
            organization = session.get(OrganizationModel, settings.default_organization_id)
            if organization is None:
                return
            existing = session.scalar(
                select(PartnerModel).where(PartnerModel.organization_id == organization.id)
            )
            if existing is not None:
                return
            session.add(
                PartnerModel(
                    id=f"prt_{organization.id}",
                    organization_id=organization.id,
                    name=f"{organization.name} Partner",
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            )
            session.commit()

    def get_current_organization(self, organization_id: str) -> dict:
        with SessionLocal() as session:
            organization = session.get(OrganizationModel, organization_id)
            if organization is None:
                raise NotFoundError("Organization not found")
            return _serialize_organization(organization)

    def update_organization(
        self,
        payload: OrganizationUpdateRequest,
        *,
        organization_id: str,
        now: datetime,
    ) -> dict:
        with SessionLocal() as session:
            organization = session.get(OrganizationModel, organization_id)
            if organization is None:
                raise NotFoundError("Organization not found")
            if payload.name is not None:
                organization.name = payload.name
            if payload.slug is not None:
                organization.slug = payload.slug
            organization.updated_at = now
            session.add(organization)
            session.commit()
            session.refresh(organization)
            return _serialize_organization(organization)

    def get_partner(self, organization_id: str) -> dict:
        with SessionLocal() as session:
            partner = self._get_partner_or_404(session, organization_id=organization_id)
            return _serialize_partner(partner)

    def list_partner_accounts(self, organization_id: str) -> list[dict]:
        with SessionLocal() as session:
            partner = self._get_partner_or_404(session, organization_id=organization_id)
            rows = session.execute(
                select(PartnerAccountModel, OrganizationModel)
                .join(OrganizationModel, PartnerAccountModel.organization_id == OrganizationModel.id)
                .where(PartnerAccountModel.partner_id == partner.id)
                .order_by(PartnerAccountModel.created_at.desc())
            ).all()
            return [_serialize_partner_account(account, org) for account, org in rows]

    def create_partner_account(
        self,
        payload: PartnerAccountCreateRequest,
        *,
        organization_id: str,
        trace_id: str,
        now: datetime,
    ) -> dict:
        with SessionLocal() as session:
            partner = self._get_partner_or_404(session, organization_id=organization_id)
            base_slug = (payload.slug or payload.name).strip().lower().replace(" ", "-")
            base_slug = "".join(char for char in base_slug if char.isalnum() or char == "-")
            if not base_slug:
                base_slug = f"org-{uuid4().hex[:6]}"
            slug = self._generate_unique_slug(session, base_slug)

            organization = OrganizationModel(
                id=f"org_{uuid4().hex[:8]}",
                name=payload.name,
                slug=slug,
                created_at=now,
                updated_at=now,
            )
            account = PartnerAccountModel(
                id=f"pac_{uuid4().hex[:8]}",
                partner_id=partner.id,
                organization_id=organization.id,
                created_at=now,
            )
            session.add(organization)
            session.add(account)
            self._emit_event(
                session,
                organization_id=partner.organization_id,
                event_type="partner.referral.created",
                trace_id=trace_id,
                occurred_at=now,
                source="control_plane",
                payload={
                    "partner_id": partner.id,
                    "referral_id": account.id,
                    "referred_account_id": organization.id,
                },
            )
            session.commit()
            session.refresh(organization)
            session.refresh(account)
            return _serialize_partner_account(account, organization)

    def list_api_keys(self, organization_id: str) -> list[dict]:
        with SessionLocal() as session:
            keys = session.scalars(
                select(ApiKeyModel)
                .where(ApiKeyModel.organization_id == organization_id)
                .order_by(ApiKeyModel.created_at.asc())
            ).all()
            return [_serialize_api_key(key) for key in keys]

    def create_api_key(
        self,
        payload: ApiKeyCreateRequest,
        *,
        organization_id: str,
        now: datetime,
    ) -> dict:
        with SessionLocal() as session:
            while True:
                raw_key = f"va_{uuid4().hex}"
                key_hash = hash_api_key(raw_key)
                existing = session.scalar(select(ApiKeyModel).where(ApiKeyModel.key_hash == key_hash))
                if existing is None:
                    break

            record = ApiKeyModel(
                id=f"key_{uuid4().hex[:8]}",
                organization_id=organization_id,
                name=payload.name,
                key_hash=key_hash,
                scopes=list(payload.scopes),
                is_active=True,
                created_at=now,
                last_used_at=None,
            )
            session.add(record)
            session.commit()
            session.refresh(record)
            return {**_serialize_api_key(record), "api_key": raw_key}

    def delete_api_key(
        self,
        key_id: str,
        *,
        organization_id: str,
    ) -> dict:
        with SessionLocal() as session:
            key_model = session.scalar(
                select(ApiKeyModel).where(
                    ApiKeyModel.id == key_id,
                    ApiKeyModel.organization_id == organization_id,
                )
            )
            if key_model is None:
                raise NotFoundError("API key not found")
            key_model.is_active = False
            session.add(key_model)
            session.commit()
            return {"id": key_id, "status": "revoked"}

    def list_plans(self) -> list[dict]:
        with SessionLocal() as session:
            plans = session.scalars(select(PlanModel).where(PlanModel.is_active.is_(True)).order_by(PlanModel.code)).all()
            return [_serialize_plan(plan) for plan in plans]

    def list_subscriptions(self, organization_id: str) -> list[dict]:
        with SessionLocal() as session:
            items = session.scalars(
                select(SubscriptionModel)
                .where(SubscriptionModel.organization_id == organization_id)
                .order_by(SubscriptionModel.updated_at.desc())
            ).all()
            return [_serialize_subscription(item) for item in items]

    def list_licenses(self, organization_id: str) -> list[dict]:
        with SessionLocal() as session:
            items = session.scalars(
                select(LicenseModel)
                .where(LicenseModel.organization_id == organization_id)
                .order_by(LicenseModel.updated_at.desc())
            ).all()
            return [_serialize_license(item) for item in items]

    def _get_agent_or_404(self, session, *, agent_id: str, organization_id: str) -> AgentModel:
        agent = session.scalar(
            select(AgentModel).where(
                AgentModel.id == agent_id,
                AgentModel.organization_id == organization_id,
            )
        )
        if agent is None:
            raise NotFoundError("Agent not found")
        return agent

    def _get_booking_or_404(self, session, *, booking_id: str, organization_id: str) -> BookingModel:
        booking = session.scalar(
            select(BookingModel).where(
                BookingModel.id == booking_id,
                BookingModel.organization_id == organization_id,
            )
        )
        if booking is None:
            raise NotFoundError("Booking not found")
        return booking

    def _get_call_or_404(self, session, *, call_id: str, organization_id: str) -> CallModel:
        call = session.scalar(
            select(CallModel).where(
                CallModel.id == call_id,
                CallModel.organization_id == organization_id,
            )
        )
        if call is None:
            raise NotFoundError("Call not found")
        return call

    def _get_webhook_or_404(self, session, *, webhook_id: str, organization_id: str) -> WebhookSubscriptionModel:
        hook = session.scalar(
            select(WebhookSubscriptionModel).where(
                WebhookSubscriptionModel.id == webhook_id,
                WebhookSubscriptionModel.organization_id == organization_id,
            )
        )
        if hook is None:
            raise NotFoundError("Webhook not found")
        return hook

    def _get_webhook_delivery_or_404(
        self,
        session,
        *,
        webhook_id: str,
        delivery_id: str,
    ) -> WebhookDeliveryModel:
        delivery = session.scalar(
            select(WebhookDeliveryModel).where(
                WebhookDeliveryModel.id == delivery_id,
                WebhookDeliveryModel.webhook_id == webhook_id,
            )
        )
        if delivery is None:
            raise NotFoundError("Webhook delivery not found")
        return delivery

    def _get_partner_or_404(self, session, *, organization_id: str) -> PartnerModel:
        partner = session.scalar(
            select(PartnerModel).where(
                PartnerModel.organization_id == organization_id,
                PartnerModel.is_active.is_(True),
            )
        )
        if partner is None:
            raise NotFoundError("Partner not found")
        return partner

    def _generate_unique_slug(self, session, base_slug: str) -> str:
        slug = base_slug
        counter = 1
        while True:
            exists = session.scalar(select(OrganizationModel).where(OrganizationModel.slug == slug))
            if exists is None:
                return slug
            counter += 1
            slug = f"{base_slug}-{counter}"

    def _idempotency_id(self, *, organization_id: str, method: str, path: str, key: str) -> str:
        return f"{organization_id}:{method.upper()}:{path}:{key}"

    def _is_idempotency_expired(self, record: IdempotencyKeyModel, now: datetime) -> bool:
        ttl_seconds = settings.idempotency_ttl_seconds
        if ttl_seconds <= 0:
            return False
        created_at = record.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=now.tzinfo)
        return created_at < now - timedelta(seconds=ttl_seconds)

    def get_idempotent_response(
        self,
        *,
        organization_id: str,
        key: str,
        method: str,
        path: str,
        request_hash: str,
    ) -> dict | None:
        record_id = self._idempotency_id(
            organization_id=organization_id,
            method=method,
            path=path,
            key=key,
        )
        with SessionLocal() as session:
            record = session.get(IdempotencyKeyModel, record_id)
            if record is None:
                return None
            now = datetime.now().astimezone()
            if self._is_idempotency_expired(record, now):
                session.delete(record)
                session.commit()
                return None
            if record.request_hash != request_hash:
                raise IdempotencyConflictError()
            return {
                "response_body": record.response_body or {},
                "response_code": record.response_code,
            }

    def store_idempotent_response(
        self,
        *,
        organization_id: str,
        key: str,
        method: str,
        path: str,
        request_hash: str,
        response_body: dict,
        response_code: int,
        created_at: datetime,
    ) -> None:
        record_id = self._idempotency_id(
            organization_id=organization_id,
            method=method,
            path=path,
            key=key,
        )
        with SessionLocal() as session:
            existing = session.get(IdempotencyKeyModel, record_id)
            if existing is not None:
                if self._is_idempotency_expired(existing, created_at):
                    session.delete(existing)
                    session.commit()
                    existing = None
                elif existing.request_hash != request_hash:
                    raise IdempotencyConflictError()
                else:
                    return
            session.add(
                IdempotencyKeyModel(
                    id=record_id,
                    organization_id=organization_id,
                    key=key,
                    method=method.upper(),
                    path=path,
                    request_hash=request_hash,
                    response_code=response_code,
                    response_body=response_body,
                    created_at=created_at,
                )
            )
            session.commit()

    def _next_webhook_attempt_at(self, *, attempt_count: int, now: datetime) -> datetime | None:
        if attempt_count >= settings.webhook_max_attempts:
            return None
        multiplier = 2 ** max(0, attempt_count - 1)
        delay_seconds = max(1, settings.webhook_retry_backoff_seconds) * multiplier
        return now + timedelta(seconds=delay_seconds)

    def _attempt_webhook_delivery(
        self,
        session,
        *,
        delivery: WebhookDeliveryModel,
        hook: WebhookSubscriptionModel,
        event: dict,
        attempted_at: datetime,
    ) -> WebhookDeliveryModel:
        result = dispatcher.deliver(
            target_url=hook.target_url,
            secret=hook.secret,
            event=event,
        )

        delivery.attempt_count += 1
        delivery.response_code = result.response_code
        delivery.response_body = result.response_body
        delivery.last_attempt_at = attempted_at

        if result.status == "delivered":
            delivery.status = "delivered"
            delivery.delivered_at = attempted_at
            delivery.next_attempt_at = None
            delivery.last_error = None
        else:
            delivery.delivered_at = None
            delivery.last_error = result.response_body
            delivery.next_attempt_at = self._next_webhook_attempt_at(
                attempt_count=delivery.attempt_count,
                now=attempted_at,
            )
            delivery.status = "retry_scheduled" if delivery.next_attempt_at is not None else "failed"

        session.add(delivery)
        session.flush()
        return delivery

    def list_agents(self, organization_id: str) -> list[dict]:
        with SessionLocal() as session:
            agents = session.scalars(
                select(AgentModel)
                .where(AgentModel.organization_id == organization_id)
                .order_by(AgentModel.created_at.asc())
            ).all()
            return [_serialize_agent(agent) for agent in agents]

    def create_agent(self, payload: AgentCreateRequest, *, organization_id: str, now: datetime) -> dict:
        agent = AgentModel(
            id=f"agt_{uuid4().hex[:8]}",
            organization_id=organization_id,
            name=payload.name,
            template_id=payload.template_id,
            timezone=payload.timezone,
            default_language=payload.default_language,
            business_hours=payload.business_hours,
            status="draft",
            published_version_id=None,
            created_at=now,
            updated_at=now,
        )
        with SessionLocal() as session:
            session.add(agent)
            session.commit()
            session.refresh(agent)
            return _serialize_agent(agent)

    def get_agent(self, agent_id: str, organization_id: str) -> dict:
        with SessionLocal() as session:
            agent = self._get_agent_or_404(session, agent_id=agent_id, organization_id=organization_id)
            return _serialize_agent(agent)

    def update_agent(
        self,
        agent_id: str,
        payload: AgentUpdateRequest,
        *,
        organization_id: str,
        now: datetime,
    ) -> dict:
        with SessionLocal() as session:
            agent = self._get_agent_or_404(session, agent_id=agent_id, organization_id=organization_id)
            if payload.name is not None:
                agent.name = payload.name
            if payload.template_id is not None:
                agent.template_id = payload.template_id
            if payload.timezone is not None:
                agent.timezone = payload.timezone
            if payload.default_language is not None:
                agent.default_language = payload.default_language
            if payload.business_hours is not None:
                agent.business_hours = payload.business_hours
            agent.updated_at = now
            session.add(agent)
            session.commit()
            session.refresh(agent)
            return _serialize_agent(agent)

    def list_versions(self, agent_id: str, organization_id: str) -> list[dict]:
        with SessionLocal() as session:
            agent = self._get_agent_or_404(session, agent_id=agent_id, organization_id=organization_id)
            versions = session.scalars(
                select(AgentVersionModel)
                .where(AgentVersionModel.agent_id == agent_id)
                .order_by(AgentVersionModel.created_at.desc())
            ).all()
            return [_serialize_version(version) for version in versions]

    def list_templates(self) -> list[dict]:
        with SessionLocal() as session:
            templates = session.scalars(
                select(TemplateModel).where(TemplateModel.is_active.is_(True)).order_by(TemplateModel.name.asc())
            ).all()
            return [_serialize_template(template) for template in templates]

    def instantiate_template(
        self,
        template_id: str,
        payload: TemplateInstantiateRequest,
        *,
        organization_id: str,
        now: datetime,
    ) -> dict:
        with SessionLocal() as session:
            template = session.get(TemplateModel, template_id)
            if template is None or not template.is_active:
                raise NotFoundError("Template not found")

            agent = AgentModel(
                id=f"agt_{uuid4().hex[:8]}",
                organization_id=organization_id,
                name=payload.name,
                template_id=template.id,
                timezone=payload.timezone or template.timezone,
                default_language=payload.default_language or template.default_language,
                business_hours=payload.business_hours if payload.business_hours is not None else template.business_hours,
                status="draft",
                published_version_id=None,
                created_at=now,
                updated_at=now,
            )
            session.add(agent)
            session.commit()
            session.refresh(agent)
            return _serialize_agent(agent)

    def get_version(self, agent_id: str, version_id: str, organization_id: str) -> dict:
        with SessionLocal() as session:
            self._get_agent_or_404(session, agent_id=agent_id, organization_id=organization_id)
            version = session.scalar(
                select(AgentVersionModel).where(
                    AgentVersionModel.version_id == version_id,
                    AgentVersionModel.agent_id == agent_id,
                )
            )
            if version is None:
                raise NotFoundError("Agent version not found")
            return _serialize_version(version)

    def rollback_agent(
        self,
        agent_id: str,
        *,
        organization_id: str,
        target_version_id: str | None,
        trace_id: str,
        now: datetime,
    ) -> dict:
        with SessionLocal() as session:
            agent = self._get_agent_or_404(session, agent_id=agent_id, organization_id=organization_id)
            if target_version_id:
                version = session.scalar(
                    select(AgentVersionModel).where(
                        AgentVersionModel.version_id == target_version_id,
                        AgentVersionModel.agent_id == agent_id,
                    )
                )
            else:
                version = session.scalars(
                    select(AgentVersionModel)
                    .where(AgentVersionModel.agent_id == agent_id)
                    .order_by(AgentVersionModel.created_at.desc())
                ).first()
            if version is None:
                raise NotFoundError("Agent version not found")

            snapshot = version.snapshot or {}
            agent.name = snapshot.get("name", agent.name)
            agent.template_id = snapshot.get("template_id", agent.template_id)
            agent.timezone = snapshot.get("timezone", agent.timezone)
            agent.default_language = snapshot.get("default_language", agent.default_language)
            agent.business_hours = snapshot.get("business_hours", agent.business_hours)
            agent.status = "published"
            agent.published_version_id = version.version_id
            agent.updated_at = now
            session.add(agent)
            self._emit_event(
                session,
                organization_id=organization_id,
                event_type="agent.published",
                trace_id=trace_id,
                occurred_at=now,
                source="control_plane",
                payload={
                    "agent_id": agent.id,
                    "version_id": version.version_id,
                    "environment": version.target_environment,
                    "published_by": "rollback",
                },
            )
            session.commit()
            return {
                "agent_id": agent.id,
                "version_id": version.version_id,
                "status": "published",
                "target_environment": version.target_environment,
            }

    def list_bookings(self, organization_id: str) -> list[dict]:
        with SessionLocal() as session:
            bookings = session.scalars(
                select(BookingModel)
                .where(BookingModel.organization_id == organization_id)
                .order_by(BookingModel.created_at.desc())
            ).all()
            return [_serialize_booking(booking) for booking in bookings]

    def get_booking(self, booking_id: str, organization_id: str) -> dict:
        with SessionLocal() as session:
            booking = self._get_booking_or_404(session, booking_id=booking_id, organization_id=organization_id)
            return _serialize_booking(booking)

    def update_booking(
        self,
        booking_id: str,
        payload: BookingUpdateRequest,
        *,
        organization_id: str,
        trace_id: str,
        now: datetime,
    ) -> dict:
        calendar_adapter = get_calendar_adapter()
        with SessionLocal() as session:
            booking = self._get_booking_or_404(session, booking_id=booking_id, organization_id=organization_id)
            contact_name = payload.contact_name or booking.contact_name
            contact_phone = payload.contact_phone or booking.contact_phone
            service = payload.service or booking.service
            start_at = payload.start_at or booking.start_at
            status = payload.status or booking.status
            calendar_result = calendar_adapter.update_booking(
                CalendarBookingUpdateRequest(
                    agent_id=booking.agent_id,
                    external_booking_id=booking.external_booking_id,
                    contact_name=contact_name,
                    contact_phone=contact_phone,
                    service=service,
                    start_at=start_at,
                    status=status,
                )
            )
            booking.contact_name = contact_name
            booking.contact_phone = contact_phone
            booking.service = service
            booking.start_at = start_at
            booking.status = calendar_result.status
            booking.external_booking_id = calendar_result.external_booking_id
            booking.updated_at = now
            session.add(booking)
            self._emit_event(
                session,
                organization_id=organization_id,
                event_type="booking.updated",
                trace_id=trace_id,
                occurred_at=now,
                source="runtime",
                payload={
                    "booking_id": booking.id,
                    "call_id": None,
                    "contact": {
                        "name": booking.contact_name,
                        "phone": booking.contact_phone,
                    },
                    "service": booking.service,
                    "start_at": booking.start_at.isoformat(),
                    "agent_id": booking.agent_id,
                    "status": booking.status,
                },
            )
            session.commit()
            session.refresh(booking)
            return _serialize_booking(booking)

    def list_events(self, organization_id: str) -> list[dict]:
        with SessionLocal() as session:
            events = session.scalars(
                select(EventModel)
                .where(EventModel.tenant_id == organization_id)
                .order_by(EventModel.occurred_at.desc())
            ).all()
            return [_serialize_event(event) for event in events]

    def list_webhooks(self, organization_id: str) -> list[dict]:
        with SessionLocal() as session:
            hooks = session.scalars(
                select(WebhookSubscriptionModel)
                .where(WebhookSubscriptionModel.organization_id == organization_id)
                .order_by(WebhookSubscriptionModel.created_at.asc())
            ).all()
            return [_serialize_webhook(hook) for hook in hooks]

    def create_webhook(
        self,
        payload: WebhookCreateRequest,
        *,
        organization_id: str,
        now: datetime,
    ) -> dict:
        hook = WebhookSubscriptionModel(
            id=f"wh_{uuid4().hex[:8]}",
            organization_id=organization_id,
            target_url=payload.target_url,
            event_types=payload.event_types,
            secret=f"whsec_{uuid4().hex[:16]}",
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        with SessionLocal() as session:
            session.add(hook)
            session.commit()
            session.refresh(hook)
            return _serialize_webhook(hook)

    def delete_webhook(
        self,
        webhook_id: str,
        *,
        organization_id: str,
        now: datetime,
    ) -> dict:
        with SessionLocal() as session:
            hook = self._get_webhook_or_404(session, webhook_id=webhook_id, organization_id=organization_id)
            hook.is_active = False
            hook.updated_at = now
            session.add(hook)
            session.commit()
            session.refresh(hook)
            return _serialize_webhook(hook)

    def list_calls(self, organization_id: str) -> list[dict]:
        with SessionLocal() as session:
            calls = session.scalars(
                select(CallModel)
                .where(CallModel.organization_id == organization_id)
                .order_by(CallModel.created_at.desc())
            ).all()
            return [_serialize_call(call) for call in calls]

    def get_call(self, call_id: str, organization_id: str) -> dict:
        with SessionLocal() as session:
            call = self._get_call_or_404(session, call_id=call_id, organization_id=organization_id)
            return _serialize_call(call)

    def list_call_turns(self, call_id: str, organization_id: str) -> list[dict]:
        with SessionLocal() as session:
            self._get_call_or_404(session, call_id=call_id, organization_id=organization_id)
            turns = session.scalars(
                select(CallTurnModel).where(CallTurnModel.call_id == call_id).order_by(CallTurnModel.turn_index.asc())
            ).all()
            return [_serialize_call_turn(turn) for turn in turns]

    def get_call_transcript(self, call_id: str, organization_id: str) -> dict:
        with SessionLocal() as session:
            self._get_call_or_404(session, call_id=call_id, organization_id=organization_id)
            turns = session.scalars(
                select(CallTurnModel).where(CallTurnModel.call_id == call_id).order_by(CallTurnModel.turn_index.asc())
            ).all()
            transcript_lines: list[str] = []
            for turn in turns:
                if turn.user_text:
                    transcript_lines.append(f"User: {turn.user_text}")
                if turn.assistant_text:
                    transcript_lines.append(f"Assistant: {turn.assistant_text}")
            return {
                "call_id": call_id,
                "transcript_text": "\n".join(transcript_lines),
                "turns": [_serialize_call_turn(turn) for turn in turns],
            }

    def get_call_summary(self, call_id: str, organization_id: str) -> dict:
        with SessionLocal() as session:
            self._get_call_or_404(session, call_id=call_id, organization_id=organization_id)
            summary = session.get(CallSummaryModel, call_id)
            if summary is None:
                raise NotFoundError("Call summary not found")
            return _serialize_call_summary(summary)

    def create_call(
        self,
        payload: CallCreateRequest,
        *,
        organization_id: str,
        trace_id: str,
        now: datetime,
    ) -> dict:
        call = CallModel(
            id=f"call_{uuid4().hex[:8]}",
            organization_id=organization_id,
            agent_id=payload.agent_id,
            phone_number_id=payload.phone_number_id,
            channel=payload.channel,
            direction=payload.direction,
            from_number=payload.from_number,
            to_number=payload.to_number,
            status="active",
            outcome=None,
            duration_ms=None,
            recording_available=False,
            started_at=now,
            ended_at=None,
            created_at=now,
            updated_at=now,
        )
        with SessionLocal() as session:
            self._get_agent_or_404(session, agent_id=payload.agent_id, organization_id=organization_id)
            session.add(call)
            self._emit_event(
                session,
                organization_id=organization_id,
                event_type="call.started",
                trace_id=trace_id,
                occurred_at=now,
                source="runtime",
                payload={
                    "call_id": call.id,
                    "agent_id": call.agent_id,
                    "phone_number_id": call.phone_number_id,
                    "channel": call.channel,
                    "direction": call.direction,
                    "from": call.from_number,
                    "to": call.to_number,
                },
            )
            session.commit()
            session.refresh(call)
            return _serialize_call(call)

    def add_call_turn(
        self,
        call_id: str,
        payload: CallTurnCreateRequest,
        *,
        organization_id: str,
        trace_id: str,
        now: datetime,
    ) -> dict:
        with SessionLocal() as session:
            call = self._get_call_or_404(session, call_id=call_id, organization_id=organization_id)
            existing_count = session.scalar(
                select(func.count()).select_from(CallTurnModel).where(CallTurnModel.call_id == call_id)
            )
            turn = CallTurnModel(
                id=f"turn_{uuid4().hex[:8]}",
                call_id=call_id,
                turn_index=int(existing_count or 0),
                user_text=payload.user_text,
                assistant_text=payload.assistant_text,
                latency_ms=payload.latency_ms,
                provider_breakdown=payload.provider_breakdown,
                tool_calls=payload.tool_calls,
                created_at=now,
            )
            call.updated_at = now
            session.add(turn)
            self._emit_event(
                session,
                organization_id=organization_id,
                event_type="call.turn.completed",
                trace_id=trace_id,
                occurred_at=now,
                source="runtime",
                payload={
                    "call_id": call_id,
                    "turn_index": turn.turn_index,
                    "user_text": turn.user_text,
                    "assistant_text": turn.assistant_text,
                    "latency_ms": turn.latency_ms,
                    "provider_breakdown": turn.provider_breakdown,
                    "tool_calls": turn.tool_calls,
                },
            )
            session.commit()
            session.refresh(turn)
            return _serialize_call_turn(turn)

    def respond_to_call(
        self,
        call_id: str,
        payload: CallRespondRequest,
        *,
        organization_id: str,
        trace_id: str,
        now: datetime,
    ) -> dict:
        with SessionLocal() as session:
            call = self._get_call_or_404(session, call_id=call_id, organization_id=organization_id)
            existing_count = session.scalar(
                select(func.count()).select_from(CallTurnModel).where(CallTurnModel.call_id == call_id)
            )
            runtime_turn = runtime_orchestrator.respond(
                RuntimeTurnRequest(
                    call_id=call_id,
                    agent_id=call.agent_id,
                    turn_index=int(existing_count or 0),
                    trace_id=trace_id,
                    input_text=payload.input_text,
                    audio_ref=payload.audio_ref,
                    voice_id=payload.voice_id,
                )
            )
            turn = CallTurnModel(
                id=f"turn_{uuid4().hex[:8]}",
                call_id=call_id,
                turn_index=int(existing_count or 0),
                user_text=runtime_turn.user_text,
                assistant_text=runtime_turn.assistant_text,
                latency_ms=runtime_turn.latency_ms,
                provider_breakdown=runtime_turn.provider_breakdown,
                tool_calls=runtime_turn.tool_calls,
                response_audio_ref=runtime_turn.response_audio_ref,
                finish_reason=runtime_turn.finish_reason,
                created_at=now,
            )
            call.updated_at = now
            session.add(turn)
            self._emit_event(
                session,
                organization_id=organization_id,
                event_type="call.turn.completed",
                trace_id=trace_id,
                occurred_at=now,
                source="runtime",
                payload={
                    "call_id": call_id,
                    "turn_index": turn.turn_index,
                    "user_text": turn.user_text,
                    "assistant_text": turn.assistant_text,
                    "latency_ms": turn.latency_ms,
                    "provider_breakdown": turn.provider_breakdown,
                    "tool_calls": turn.tool_calls,
                    "response_audio_ref": turn.response_audio_ref,
                    "finish_reason": turn.finish_reason,
                },
            )
            session.commit()
            session.refresh(turn)
            return _serialize_call_turn(turn)

    def complete_call(
        self,
        call_id: str,
        payload: CallCompleteRequest,
        *,
        organization_id: str,
        trace_id: str,
        now: datetime,
    ) -> dict:
        with SessionLocal() as session:
            call = self._get_call_or_404(session, call_id=call_id, organization_id=organization_id)
            summary = session.get(CallSummaryModel, call_id)
            if summary is None:
                summary = CallSummaryModel(
                    call_id=call_id,
                    summary_text=payload.summary_text,
                    structured_summary=payload.structured_summary,
                    created_at=now,
                    updated_at=now,
                )
            else:
                summary.summary_text = payload.summary_text
                summary.structured_summary = payload.structured_summary
                summary.updated_at = now
            if payload.outcome == "failed":
                call.status = "failed"
            elif payload.outcome == "escalated":
                call.status = "escalated"
            else:
                call.status = "completed"
            call.outcome = payload.outcome
            call.duration_ms = payload.duration_ms
            call.recording_available = payload.recording_available
            call.ended_at = now
            call.updated_at = now
            session.add(summary)
            session.add(call)
            if payload.outcome == "failed":
                self._emit_event(
                    session,
                    organization_id=organization_id,
                    event_type="call.failed",
                    trace_id=trace_id,
                    occurred_at=now,
                    source="runtime",
                    payload={
                        "call_id": call.id,
                        "category": payload.failure_category or "internal",
                        "code": payload.failure_code or "unknown",
                        "message": payload.failure_message or "Call failed",
                    },
                )
            if payload.outcome == "escalated":
                self._emit_event(
                    session,
                    organization_id=organization_id,
                    event_type="call.escalated",
                    trace_id=trace_id,
                    occurred_at=now,
                    source="runtime",
                    payload={
                        "call_id": call.id,
                        "reason": payload.escalation_reason or "unknown",
                        "target": payload.escalation_target or "operator_queue",
                        "summary": payload.escalation_summary,
                    },
                )
            self._emit_event(
                session,
                organization_id=organization_id,
                event_type="call.ended",
                trace_id=trace_id,
                occurred_at=now,
                source="runtime",
                payload={
                    "call_id": call.id,
                    "duration_ms": call.duration_ms,
                    "outcome": call.outcome,
                    "cost": {"currency": "USD", "amount": "0.00"},
                    "recording_available": call.recording_available,
                },
            )
            session.commit()
            return _serialize_call(call)

    def list_webhook_deliveries(self, webhook_id: str, organization_id: str) -> list[dict]:
        with SessionLocal() as session:
            self._get_webhook_or_404(session, webhook_id=webhook_id, organization_id=organization_id)
            deliveries = session.scalars(
                select(WebhookDeliveryModel)
                .where(WebhookDeliveryModel.webhook_id == webhook_id)
                .order_by(WebhookDeliveryModel.created_at.desc())
            ).all()
            return [_serialize_delivery(delivery) for delivery in deliveries]

    def process_webhook_deliveries(
        self,
        *,
        organization_id: str,
        now: datetime,
        limit: int | None = None,
    ) -> dict:
        batch_size = max(1, min(limit or settings.webhook_delivery_batch_size, 100))
        with SessionLocal() as session:
            deliveries = session.scalars(
                select(WebhookDeliveryModel)
                .join(WebhookSubscriptionModel, WebhookSubscriptionModel.id == WebhookDeliveryModel.webhook_id)
                .where(
                    WebhookSubscriptionModel.organization_id == organization_id,
                    WebhookSubscriptionModel.is_active.is_(True),
                    WebhookDeliveryModel.status.in_(("pending", "retry_scheduled")),
                    or_(
                        WebhookDeliveryModel.next_attempt_at.is_(None),
                        WebhookDeliveryModel.next_attempt_at <= now,
                    ),
                )
                .order_by(WebhookDeliveryModel.created_at.asc())
                .limit(batch_size)
            ).all()

            processed_items: list[dict] = []
            delivered_count = 0
            scheduled_count = 0
            failed_count = 0

            for delivery in deliveries:
                hook = session.get(WebhookSubscriptionModel, delivery.webhook_id)
                event = session.get(EventModel, delivery.event_id)
                if hook is None or event is None:
                    delivery.status = "failed"
                    delivery.last_attempt_at = now
                    delivery.next_attempt_at = None
                    delivery.last_error = "Missing webhook subscription or event"
                    session.add(delivery)
                else:
                    delivery = self._attempt_webhook_delivery(
                        session,
                        delivery=delivery,
                        hook=hook,
                        event=_serialize_event(event),
                        attempted_at=now,
                    )

                serialized = _serialize_delivery(delivery)
                processed_items.append(serialized)
                if delivery.status == "delivered":
                    delivered_count += 1
                elif delivery.status == "retry_scheduled":
                    scheduled_count += 1
                else:
                    failed_count += 1

            session.commit()
            return {
                "processed": len(processed_items),
                "delivered": delivered_count,
                "retry_scheduled": scheduled_count,
                "failed": failed_count,
                "items": processed_items,
            }

    def retry_webhook_delivery(
        self,
        webhook_id: str,
        delivery_id: str,
        *,
        organization_id: str,
        now: datetime,
    ) -> dict:
        with SessionLocal() as session:
            hook = self._get_webhook_or_404(session, webhook_id=webhook_id, organization_id=organization_id)
            delivery = self._get_webhook_delivery_or_404(
                session,
                webhook_id=webhook_id,
                delivery_id=delivery_id,
            )
            event = session.get(EventModel, delivery.event_id)
            if event is None:
                raise NotFoundError("Event not found")

            if delivery.status != "delivered":
                delivery = self._attempt_webhook_delivery(
                    session,
                    delivery=delivery,
                    hook=hook,
                    event=_serialize_event(event),
                    attempted_at=now,
                )
                session.commit()
                session.refresh(delivery)

            return _serialize_delivery(delivery)

    def publish_agent(
        self,
        agent_id: str,
        *,
        organization_id: str,
        target_environment: str,
        trace_id: str,
        now: datetime,
    ) -> dict:
        with SessionLocal() as session:
            agent = self._get_agent_or_404(session, agent_id=agent_id, organization_id=organization_id)

            version_id = f"ver_{uuid4().hex[:8]}"
            version = AgentVersionModel(
                version_id=version_id,
                agent_id=agent.id,
                target_environment=target_environment,
                created_at=now,
                snapshot={
                    "id": agent.id,
                    "name": agent.name,
                    "template_id": agent.template_id,
                    "timezone": agent.timezone,
                    "default_language": agent.default_language,
                    "business_hours": agent.business_hours,
                    "status": agent.status,
                    "published_version_id": agent.published_version_id,
                },
            )
            agent.status = "published"
            agent.published_version_id = version_id
            agent.updated_at = now
            session.add(version)
            session.add(agent)
            self._emit_event(
                session,
                organization_id=organization_id,
                event_type="agent.published",
                trace_id=trace_id,
                occurred_at=now,
                source="control_plane",
                payload={
                    "agent_id": agent.id,
                    "version_id": version_id,
                    "environment": target_environment,
                    "published_by": "api_key",
                },
            )
            session.commit()
            return {
                "agent_id": agent.id,
                "version_id": version_id,
                "status": "published",
                "target_environment": target_environment,
            }

    def create_booking(
        self,
        payload: BookingCreateRequest,
        *,
        organization_id: str,
        trace_id: str,
        now: datetime,
    ) -> dict:
        calendar_adapter = get_calendar_adapter()
        calendar_result = calendar_adapter.create_booking(
            CalendarBookingRequest(
                agent_id=payload.agent_id,
                contact_name=payload.contact_name,
                contact_phone=payload.contact_phone,
                service=payload.service,
                start_at=payload.start_at,
            )
        )
        booking = BookingModel(
            id=f"bk_{uuid4().hex[:8]}",
            organization_id=organization_id,
            agent_id=payload.agent_id,
            contact_name=payload.contact_name,
            contact_phone=payload.contact_phone,
            service=payload.service,
            start_at=payload.start_at,
            status=calendar_result.status,
            external_booking_id=calendar_result.external_booking_id,
            created_at=now,
            updated_at=now,
        )
        with SessionLocal() as session:
            self._get_agent_or_404(session, agent_id=payload.agent_id, organization_id=organization_id)
            session.add(booking)
            self._emit_event(
                session,
                organization_id=organization_id,
                event_type="booking.created",
                trace_id=trace_id,
                occurred_at=now,
                source="runtime",
                payload={
                    "booking_id": booking.id,
                    "call_id": None,
                    "contact": {
                        "name": booking.contact_name,
                        "phone": booking.contact_phone,
                    },
                    "service": booking.service,
                    "start_at": booking.start_at.isoformat(),
                    "agent_id": booking.agent_id,
                },
            )
            session.commit()
            session.refresh(booking)
            return _serialize_booking(booking)

    def list_phone_numbers(self, organization_id: str) -> list[dict]:
        with SessionLocal() as session:
            numbers = session.scalars(
                select(PhoneNumberModel)
                .where(PhoneNumberModel.organization_id == organization_id)
                .order_by(PhoneNumberModel.created_at.asc())
            ).all()
            return [_serialize_phone_number(number) for number in numbers]

    def create_phone_number(
        self,
        payload: PhoneNumberCreateRequest,
        *,
        organization_id: str,
        now: datetime,
    ) -> dict:
        number = PhoneNumberModel(
            id=f"num_{uuid4().hex[:8]}",
            organization_id=organization_id,
            provider=payload.provider,
            number=payload.number,
            label=payload.label,
            status=payload.status,
            capabilities=payload.capabilities,
            created_at=now,
            updated_at=now,
        )
        with SessionLocal() as session:
            session.add(number)
            session.commit()
            session.refresh(number)
            return _serialize_phone_number(number)

    def update_phone_number(
        self,
        number_id: str,
        payload: PhoneNumberUpdateRequest,
        *,
        organization_id: str,
        now: datetime,
    ) -> dict:
        with SessionLocal() as session:
            number = session.scalar(
                select(PhoneNumberModel).where(
                    PhoneNumberModel.id == number_id,
                    PhoneNumberModel.organization_id == organization_id,
                )
            )
            if number is None:
                raise NotFoundError("Phone number not found")
            if payload.label is not None:
                number.label = payload.label
            if payload.status is not None:
                number.status = payload.status
            if payload.capabilities is not None:
                number.capabilities = payload.capabilities
            number.updated_at = now
            session.add(number)
            session.commit()
            session.refresh(number)
            return _serialize_phone_number(number)

    def list_integrations(self, organization_id: str) -> list[dict]:
        with SessionLocal() as session:
            integrations = session.scalars(
                select(IntegrationModel)
                .where(IntegrationModel.organization_id == organization_id)
                .order_by(IntegrationModel.provider.asc())
            ).all()
            return [_serialize_integration(item) for item in integrations]

    def connect_integration(
        self,
        provider: str,
        payload: IntegrationConnectRequest,
        *,
        organization_id: str,
        now: datetime,
    ) -> dict:
        normalized = provider.strip().lower()
        with SessionLocal() as session:
            integration = session.scalar(
                select(IntegrationModel).where(
                    IntegrationModel.organization_id == organization_id,
                    IntegrationModel.provider == normalized,
                )
            )
            if integration is None:
                integration = IntegrationModel(
                    id=f"int_{uuid4().hex[:8]}",
                    organization_id=organization_id,
                    provider=normalized,
                    status="connected",
                    config=payload.config,
                    last_tested_at=None,
                    created_at=now,
                    updated_at=now,
                )
            else:
                integration.status = "connected"
                integration.config = payload.config
                integration.updated_at = now
            session.add(integration)
            session.commit()
            session.refresh(integration)
            return _serialize_integration(integration)

    def test_integration(
        self,
        provider: str,
        *,
        organization_id: str,
        now: datetime,
    ) -> dict:
        normalized = provider.strip().lower()
        with SessionLocal() as session:
            integration = session.scalar(
                select(IntegrationModel).where(
                    IntegrationModel.organization_id == organization_id,
                    IntegrationModel.provider == normalized,
                )
            )
            if integration is None:
                raise NotFoundError("Integration not found")
            integration.last_tested_at = now
            integration.updated_at = now
            session.add(integration)
            session.commit()
            session.refresh(integration)
            return {
                "provider": normalized,
                "status": "healthy",
                "checked_at": integration.last_tested_at,
                "details": {"connection": integration.status},
            }

    def list_knowledge_bases(self, organization_id: str) -> list[dict]:
        with SessionLocal() as session:
            bases = session.scalars(
                select(KnowledgeBaseModel)
                .where(KnowledgeBaseModel.organization_id == organization_id)
                .order_by(KnowledgeBaseModel.created_at.desc())
            ).all()
            return [_serialize_knowledge_base(item) for item in bases]

    def create_knowledge_base(
        self,
        payload: KnowledgeBaseCreateRequest,
        *,
        organization_id: str,
        now: datetime,
    ) -> dict:
        base = KnowledgeBaseModel(
            id=f"kb_{uuid4().hex[:8]}",
            organization_id=organization_id,
            name=payload.name,
            description=payload.description,
            is_active=True,
            created_at=now,
            updated_at=now,
        )
        with SessionLocal() as session:
            session.add(base)
            session.commit()
            session.refresh(base)
            return _serialize_knowledge_base(base)

    def add_knowledge_document(
        self,
        knowledge_base_id: str,
        payload: KnowledgeBaseDocumentCreateRequest,
        *,
        organization_id: str,
        now: datetime,
    ) -> dict:
        with SessionLocal() as session:
            base = session.scalar(
                select(KnowledgeBaseModel).where(
                    KnowledgeBaseModel.id == knowledge_base_id,
                    KnowledgeBaseModel.organization_id == organization_id,
                )
            )
            if base is None:
                raise NotFoundError("Knowledge base not found")
            document = KnowledgeBaseDocumentModel(
                id=f"kbd_{uuid4().hex[:8]}",
                knowledge_base_id=base.id,
                title=payload.title,
                content=payload.content,
                source_url=payload.source_url,
                created_at=now,
                updated_at=now,
            )
            base.updated_at = now
            session.add(document)
            session.add(base)
            session.commit()
            session.refresh(document)
            return _serialize_knowledge_document(document)

    def get_usage_summary(self, organization_id: str) -> dict:
        with SessionLocal() as session:
            calls = session.scalars(
                select(CallModel).where(CallModel.organization_id == organization_id)
            ).all()
            total_calls = len(calls)
            completed_calls = sum(1 for call in calls if call.status == "completed")
            failed_calls = sum(1 for call in calls if call.status == "failed")
            escalated_calls = sum(1 for call in calls if call.status == "escalated")
            active_calls = sum(1 for call in calls if call.status == "active")
            total_duration_ms = sum(call.duration_ms or 0 for call in calls)
            average_duration_ms = int(total_duration_ms / total_calls) if total_calls else 0
            return {
                "total_calls": total_calls,
                "completed_calls": completed_calls,
                "failed_calls": failed_calls,
                "escalated_calls": escalated_calls,
                "active_calls": active_calls,
                "total_duration_ms": total_duration_ms,
                "average_duration_ms": average_duration_ms,
            }

    def get_usage_costs(self, organization_id: str) -> dict:
        with SessionLocal() as session:
            calls = session.scalars(
                select(CallModel).where(CallModel.organization_id == organization_id)
            ).all()
            total_duration_ms = sum(call.duration_ms or 0 for call in calls)

            turns = session.scalars(
                select(CallTurnModel)
                .join(CallModel, CallTurnModel.call_id == CallModel.id)
                .where(CallModel.organization_id == organization_id)
            ).all()
            tokens_in = 0
            tokens_out = 0
            for turn in turns:
                breakdown = turn.provider_breakdown or {}
                tokens_in += int(breakdown.get("tokens_in") or 0)
                tokens_out += int(breakdown.get("tokens_out") or 0)

            token_cost = (tokens_in + tokens_out) * 0.000002
            duration_cost = (total_duration_ms / 1000.0) * 0.001
            total_cost = round(token_cost + duration_cost, 6)

            return {
                "currency": "USD",
                "total_cost_usd": total_cost,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "duration_ms": total_duration_ms,
                "components": {
                    "token_cost_usd": round(token_cost, 6),
                    "duration_cost_usd": round(duration_cost, 6),
                },
            }

    def test_webhook(
        self,
        webhook_id: str,
        *,
        organization_id: str,
        trace_id: str,
        now: datetime,
    ) -> dict:
        with SessionLocal() as session:
            hook = self._get_webhook_or_404(session, webhook_id=webhook_id, organization_id=organization_id)
            event_id, delivery_id, delivery_status = self._emit_event(
                session,
                organization_id=organization_id,
                event_type="webhook.test",
                trace_id=trace_id,
                occurred_at=now,
                source="control_plane",
                payload={
                    "webhook_id": webhook_id,
                    "target_url": hook.target_url,
                },
                only_webhook_id=webhook_id,
            )
            session.commit()
            return {
                "webhook_id": webhook_id,
                "event_id": event_id,
                "delivery_id": delivery_id,
                "status": delivery_status or "simulated",
            }

    def process_lemonsqueezy_webhook(
        self,
        *,
        payload: dict,
        signature_verified: bool,
        received_at: datetime,
    ) -> dict:
        metadata = extract_event_metadata(payload)
        meta = payload.get("meta", {}) or {}
        attrs = payload.get("data", {}).get("attributes", {}) or {}
        custom_data = meta.get("custom_data", {}) or {}
        organization_id = custom_data.get("organization_id") or settings.default_organization_id
        event_name = metadata["event_name"] or "unknown"

        with SessionLocal() as session:
            event_log = BillingWebhookEventModel(
                id=f"lsw_{uuid4().hex[:10]}",
                organization_id=organization_id,
                provider="lemonsqueezy",
                event_name=event_name,
                resource_type=metadata["resource_type"],
                resource_id=metadata["resource_id"],
                signature_verified=signature_verified,
                payload=payload,
                received_at=received_at,
            )
            session.add(event_log)

            if metadata["resource_type"] == "subscriptions":
                self._upsert_subscription(
                    session,
                    organization_id=organization_id,
                    external_id=str(metadata["resource_id"]),
                    attrs=attrs,
                    received_at=received_at,
                    custom_data=custom_data,
                )
                if attrs.get("status") in {"active", "on_trial"}:
                    self._emit_event(
                        session,
                        organization_id=organization_id,
                        event_type="subscription.activated",
                        trace_id=f"ls_{uuid4().hex[:8]}",
                        occurred_at=received_at,
                        source="billing",
                        payload={
                            "subscription_id": str(metadata["resource_id"]),
                            "plan_code": custom_data.get("plan_code") or attrs.get("variant_name"),
                            "billing_provider": "lemonsqueezy",
                        },
                    )
                if attrs.get("status") in {"cancelled", "expired"}:
                    self._emit_event(
                        session,
                        organization_id=organization_id,
                        event_type="subscription.canceled",
                        trace_id=f"ls_{uuid4().hex[:8]}",
                        occurred_at=received_at,
                        source="billing",
                        payload={
                            "subscription_id": str(metadata["resource_id"]),
                            "billing_provider": "lemonsqueezy",
                        },
                    )

            if metadata["resource_type"] == "license-keys":
                self._upsert_license(
                    session,
                    organization_id=organization_id,
                    external_id=str(metadata["resource_id"]),
                    attrs=attrs,
                    received_at=received_at,
                )
            session.commit()

        return {
            "provider": "lemonsqueezy",
            "event_name": event_name,
            "resource_type": metadata["resource_type"],
            "resource_id": metadata["resource_id"],
            "status": "processed",
        }

    def record_license_validation(
        self,
        *,
        organization_id: str,
        validation_response: dict,
        received_at: datetime,
    ) -> dict:
        license_key = validation_response.get("license_key", {}) or {}
        if not license_key:
            return {"status": "no_license_data"}
        with SessionLocal() as session:
            record = self._upsert_license(
                session,
                organization_id=organization_id,
                external_id=str(license_key.get("id") or f"local_{uuid4().hex[:8]}"),
                attrs=license_key,
                received_at=received_at,
            )
            self._emit_event(
                session,
                organization_id=organization_id,
                event_type="license.validated",
                trace_id=f"lic_{uuid4().hex[:8]}",
                occurred_at=received_at,
                source="billing",
                payload={
                    "license_id": record.id,
                    "status": record.status,
                },
            )
            session.commit()
            return _serialize_license(record)

    def _upsert_subscription(self, session, *, organization_id: str, external_id: str, attrs: dict, received_at: datetime, custom_data: dict) -> SubscriptionModel:
        item = session.get(SubscriptionModel, external_id)
        if item is None:
            item = SubscriptionModel(
                id=external_id,
                organization_id=organization_id,
                created_at=received_at,
                updated_at=received_at,
                status=str(attrs.get("status") or "unknown"),
                status_formatted=attrs.get("status_formatted"),
                customer_email=attrs.get("user_email") or attrs.get("customer_email"),
                customer_name=attrs.get("user_name") or attrs.get("customer_name"),
                product_id=attrs.get("product_id"),
                variant_id=attrs.get("variant_id"),
                order_id=attrs.get("order_id"),
                store_id=attrs.get("store_id"),
                test_mode=bool(attrs.get("test_mode", False)),
                renews_at=_parse_optional_datetime(attrs.get("renews_at")),
                ends_at=_parse_optional_datetime(attrs.get("ends_at")),
                plan_code=custom_data.get("plan_code") or attrs.get("variant_name"),
                raw_attributes=attrs,
            )
        else:
            item.organization_id = organization_id
            item.plan_code = custom_data.get("plan_code") or attrs.get("variant_name")
            item.status = str(attrs.get("status") or item.status)
            item.status_formatted = attrs.get("status_formatted")
            item.customer_email = attrs.get("user_email") or attrs.get("customer_email")
            item.customer_name = attrs.get("user_name") or attrs.get("customer_name")
            item.product_id = attrs.get("product_id")
            item.variant_id = attrs.get("variant_id")
            item.order_id = attrs.get("order_id")
            item.store_id = attrs.get("store_id")
            item.test_mode = bool(attrs.get("test_mode", False))
            item.renews_at = _parse_optional_datetime(attrs.get("renews_at"))
            item.ends_at = _parse_optional_datetime(attrs.get("ends_at"))
            item.raw_attributes = attrs
            item.updated_at = received_at
        session.add(item)
        return item

    def _upsert_license(self, session, *, organization_id: str, external_id: str, attrs: dict, received_at: datetime) -> LicenseModel:
        item = session.get(LicenseModel, external_id)
        key_value = attrs.get("key")
        key_short = None
        if isinstance(key_value, str) and len(key_value) >= 8:
            key_short = f"{key_value[:4]}...{key_value[-4:]}"
        if item is None:
            item = LicenseModel(
                id=external_id,
                organization_id=organization_id,
                subscription_id=str(attrs.get("subscription_id")) if attrs.get("subscription_id") else None,
                order_id=attrs.get("order_id"),
                order_item_id=attrs.get("order_item_id"),
                product_id=attrs.get("product_id"),
                variant_id=attrs.get("variant_id"),
                customer_email=attrs.get("customer_email"),
                customer_name=attrs.get("customer_name"),
                key_short=key_short,
                status=str(attrs.get("status") or "unknown"),
                activation_limit=attrs.get("activation_limit"),
                activation_usage=attrs.get("activation_usage") or attrs.get("instance_count"),
                expires_at=_parse_optional_datetime(attrs.get("expires_at")),
                raw_attributes=attrs,
                created_at=received_at,
                updated_at=received_at,
            )
        else:
            item.organization_id = organization_id
            item.subscription_id = str(attrs.get("subscription_id")) if attrs.get("subscription_id") else item.subscription_id
            item.order_id = attrs.get("order_id")
            item.order_item_id = attrs.get("order_item_id")
            item.product_id = attrs.get("product_id")
            item.variant_id = attrs.get("variant_id")
            item.customer_email = attrs.get("customer_email")
            item.customer_name = attrs.get("customer_name")
            item.key_short = key_short
            item.status = str(attrs.get("status") or item.status)
            item.activation_limit = attrs.get("activation_limit")
            item.activation_usage = attrs.get("activation_usage") or attrs.get("instance_count")
            item.expires_at = _parse_optional_datetime(attrs.get("expires_at"))
            item.raw_attributes = attrs
            item.updated_at = received_at
        session.add(item)
        return item

    def _emit_event(
        self,
        session,
        *,
        organization_id: str,
        event_type: str,
        trace_id: str,
        occurred_at: datetime,
        source: str,
        payload: dict,
        only_webhook_id: str | None = None,
    ) -> tuple[str, str | None, str | None]:
        event_id = f"evt_{uuid4().hex[:10]}"
        event = EventModel(
            event_id=event_id,
            event_type=event_type,
            event_version="v1",
            occurred_at=occurred_at,
            trace_id=trace_id,
            tenant_id=organization_id,
            source=source,
            payload=payload,
        )
        session.add(event)
        session.flush()

        event_body = _serialize_event(event)

        hooks_query = select(WebhookSubscriptionModel).where(
            WebhookSubscriptionModel.is_active.is_(True),
            WebhookSubscriptionModel.organization_id == organization_id,
        )
        if only_webhook_id is not None:
            hooks_query = hooks_query.where(WebhookSubscriptionModel.id == only_webhook_id)
        hooks = session.scalars(hooks_query).all()

        first_delivery_id: str | None = None
        first_delivery_status: str | None = None
        for hook in hooks:
            subscribed = only_webhook_id is not None or "*" in hook.event_types or event_type in hook.event_types
            if not subscribed:
                continue
            delivery_id = f"wd_{uuid4().hex[:8]}"
            delivery = WebhookDeliveryModel(
                id=delivery_id,
                webhook_id=hook.id,
                event_id=event_id,
                event_type=event_type,
                status="pending",
                attempt_count=0,
                response_code=None,
                response_body=None,
                last_attempt_at=None,
                next_attempt_at=occurred_at,
                last_error=None,
                delivered_at=None,
                created_at=occurred_at,
            )
            session.add(delivery)
            session.flush()
            delivery = self._attempt_webhook_delivery(
                session,
                delivery=delivery,
                hook=hook,
                event=event_body,
                attempted_at=occurred_at,
            )
            if first_delivery_id is None:
                first_delivery_id = delivery_id
                first_delivery_status = delivery.status
        return event_id, first_delivery_id, first_delivery_status


store = AgentStore()
