from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


def utc_now() -> datetime:
    return datetime.now(UTC)


class ErrorDetail(BaseModel):
    code: str
    message: str
    category: str
    trace_id: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class HealthResponse(BaseModel):
    status: Literal["ok"]


class ReadyResponse(BaseModel):
    status: Literal["ready"]
    environment: str


class OrganizationResponse(BaseModel):
    id: str
    name: str
    slug: str
    created_at: datetime
    updated_at: datetime


class OrganizationUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    slug: str | None = Field(default=None, min_length=2, max_length=120)

    @model_validator(mode="after")
    def validate_payload(self) -> "OrganizationUpdateRequest":
        if not self.name and not self.slug:
            raise ValueError("at least one field must be provided")
        return self


class ApiKeyMetadataResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    scopes: list[str]
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None = None


class ApiKeyListResponse(BaseModel):
    items: list[ApiKeyMetadataResponse]
    total: int


class ApiKeyCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    scopes: list[str] = Field(min_length=1)


class ApiKeyCreateResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    scopes: list[str]
    is_active: bool
    created_at: datetime
    last_used_at: datetime | None = None
    api_key: str


class ApiKeyDeleteResponse(BaseModel):
    id: str
    status: Literal["revoked"]


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    default_language: str
    timezone: str
    business_hours: dict[str, list[str]]
    definition: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TemplateListResponse(BaseModel):
    items: list[TemplateResponse]
    total: int


class TemplateInstantiateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    timezone: str | None = Field(default=None, min_length=2, max_length=64)
    default_language: str | None = Field(default=None, min_length=2, max_length=16)
    business_hours: dict[str, list[str]] | None = None


class PlanResponse(BaseModel):
    code: str
    name: str
    price_monthly_usd: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PlanListResponse(BaseModel):
    items: list[PlanResponse]
    total: int


class SubscriptionResponse(BaseModel):
    id: str
    organization_id: str
    plan_code: str | None = None
    status: str
    status_formatted: str | None = None
    customer_email: str | None = None
    customer_name: str | None = None
    product_id: int | None = None
    variant_id: int | None = None
    order_id: int | None = None
    store_id: int | None = None
    test_mode: bool
    renews_at: datetime | None = None
    ends_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class SubscriptionListResponse(BaseModel):
    items: list[SubscriptionResponse]
    total: int


class LicenseResponse(BaseModel):
    id: str
    organization_id: str
    subscription_id: str | None = None
    order_id: int | None = None
    order_item_id: int | None = None
    product_id: int | None = None
    variant_id: int | None = None
    customer_email: str | None = None
    customer_name: str | None = None
    key_short: str | None = None
    status: str
    activation_limit: int | None = None
    activation_usage: int | None = None
    expires_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class LicenseListResponse(BaseModel):
    items: list[LicenseResponse]
    total: int


class BillingWebhookResponse(BaseModel):
    provider: Literal["lemonsqueezy"]
    event_name: str
    resource_type: str | None = None
    resource_id: str | None = None
    status: Literal["processed"]


class LicenseValidateRequest(BaseModel):
    license_key: str = Field(min_length=5)
    instance_name: str | None = None
    instance_id: str | None = None


class LicenseValidateResponse(BaseModel):
    valid: bool
    error: str | None = None
    license_key: dict | None = None
    instance: dict | None = None
    meta: dict | None = None


class AgentCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    template_id: str = Field(min_length=3, max_length=120)
    timezone: str = Field(min_length=2, max_length=64)
    default_language: str = Field(min_length=2, max_length=16)
    business_hours: dict[str, list[str]] = Field(default_factory=dict)


class AgentUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    template_id: str | None = Field(default=None, min_length=3, max_length=120)
    timezone: str | None = Field(default=None, min_length=2, max_length=64)
    default_language: str | None = Field(default=None, min_length=2, max_length=16)
    business_hours: dict[str, list[str]] | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "AgentUpdateRequest":
        if (
            self.name is None
            and self.template_id is None
            and self.timezone is None
            and self.default_language is None
            and self.business_hours is None
        ):
            raise ValueError("at least one field must be provided")
        return self


class AgentResponse(BaseModel):
    id: str
    name: str
    template_id: str
    timezone: str
    default_language: str
    business_hours: dict[str, list[str]]
    status: Literal["draft", "published"]
    published_version_id: str | None = None
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    items: list[AgentResponse]
    total: int


class PublishAgentRequest(BaseModel):
    target_environment: Literal["staging", "production"] = "production"


class PublishAgentResponse(BaseModel):
    agent_id: str
    version_id: str
    status: Literal["published"]
    target_environment: Literal["staging", "production"]


class RollbackAgentRequest(BaseModel):
    version_id: str | None = Field(default=None, min_length=3, max_length=32)


class RollbackAgentResponse(BaseModel):
    agent_id: str
    version_id: str
    status: Literal["published"]
    target_environment: Literal["staging", "production"]


class AgentVersionResponse(BaseModel):
    version_id: str
    agent_id: str
    target_environment: Literal["staging", "production"]
    created_at: datetime
    snapshot: dict


class AgentVersionListResponse(BaseModel):
    items: list[AgentVersionResponse]
    total: int


class BookingCreateRequest(BaseModel):
    agent_id: str = Field(min_length=3, max_length=32)
    contact_name: str = Field(min_length=2, max_length=120)
    contact_phone: str = Field(min_length=6, max_length=32)
    service: str = Field(min_length=2, max_length=120)
    start_at: datetime


class BookingUpdateRequest(BaseModel):
    contact_name: str | None = Field(default=None, min_length=2, max_length=120)
    contact_phone: str | None = Field(default=None, min_length=6, max_length=32)
    service: str | None = Field(default=None, min_length=2, max_length=120)
    start_at: datetime | None = None
    status: Literal["confirmed", "cancelled", "rescheduled"] | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "BookingUpdateRequest":
        if (
            self.contact_name is None
            and self.contact_phone is None
            and self.service is None
            and self.start_at is None
            and self.status is None
        ):
            raise ValueError("at least one field must be provided")
        return self


class BookingResponse(BaseModel):
    id: str
    agent_id: str
    contact_name: str
    contact_phone: str
    service: str
    start_at: datetime
    status: Literal["confirmed", "cancelled", "rescheduled"]
    external_booking_id: str | None = None
    created_at: datetime
    updated_at: datetime


class BookingListResponse(BaseModel):
    items: list[BookingResponse]
    total: int


class PhoneNumberCreateRequest(BaseModel):
    provider: str = Field(min_length=2, max_length=64)
    number: str = Field(min_length=6, max_length=32)
    label: str | None = Field(default=None, min_length=2, max_length=120)
    status: Literal["active", "inactive"] = "active"
    capabilities: dict = Field(default_factory=dict)


class PhoneNumberUpdateRequest(BaseModel):
    label: str | None = Field(default=None, min_length=2, max_length=120)
    status: Literal["active", "inactive"] | None = None
    capabilities: dict | None = None

    @model_validator(mode="after")
    def validate_payload(self) -> "PhoneNumberUpdateRequest":
        if self.label is None and self.status is None and self.capabilities is None:
            raise ValueError("at least one field must be provided")
        return self


class PhoneNumberResponse(BaseModel):
    id: str
    organization_id: str
    provider: str
    number: str
    label: str | None = None
    status: Literal["active", "inactive"]
    capabilities: dict
    created_at: datetime
    updated_at: datetime


class PhoneNumberListResponse(BaseModel):
    items: list[PhoneNumberResponse]
    total: int


class IntegrationConnectRequest(BaseModel):
    config: dict = Field(default_factory=dict)


class IntegrationResponse(BaseModel):
    id: str
    organization_id: str
    provider: str
    status: str
    config: dict
    last_tested_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class IntegrationListResponse(BaseModel):
    items: list[IntegrationResponse]
    total: int


class IntegrationTestResponse(BaseModel):
    provider: str
    status: Literal["healthy", "failed"]
    checked_at: datetime
    details: dict


class KnowledgeBaseCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class KnowledgeBaseResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    description: str | None = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class KnowledgeBaseListResponse(BaseModel):
    items: list[KnowledgeBaseResponse]
    total: int


class KnowledgeBaseDocumentCreateRequest(BaseModel):
    title: str = Field(min_length=2, max_length=200)
    content: str = Field(min_length=1)
    source_url: str | None = Field(default=None, max_length=2048)


class KnowledgeBaseDocumentResponse(BaseModel):
    id: str
    knowledge_base_id: str
    title: str
    content: str
    source_url: str | None = None
    created_at: datetime
    updated_at: datetime


class EventResponse(BaseModel):
    event_id: str
    event_type: str
    event_version: str
    occurred_at: datetime
    trace_id: str
    tenant_id: str
    source: str
    payload: dict


class EventListResponse(BaseModel):
    items: list[EventResponse]
    total: int


class WebhookCreateRequest(BaseModel):
    target_url: str = Field(min_length=8, max_length=2048)
    event_types: list[str] = Field(min_length=1)


class WebhookResponse(BaseModel):
    id: str
    target_url: str
    event_types: list[str]
    secret: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WebhookListResponse(BaseModel):
    items: list[WebhookResponse]
    total: int


class WebhookTestResponse(BaseModel):
    webhook_id: str
    event_id: str
    delivery_id: str
    status: Literal["delivered", "failed", "retry_scheduled", "simulated"]


class WebhookDeliveryResponse(BaseModel):
    id: str
    webhook_id: str
    event_id: str
    event_type: str
    status: str
    attempt_count: int
    response_code: int | None = None
    response_body: str | None = None
    last_attempt_at: datetime | None = None
    next_attempt_at: datetime | None = None
    last_error: str | None = None
    delivered_at: datetime | None = None
    created_at: datetime


class WebhookDeliveryListResponse(BaseModel):
    items: list[WebhookDeliveryResponse]
    total: int


class WebhookDeliveryProcessResponse(BaseModel):
    processed: int
    delivered: int
    retry_scheduled: int
    failed: int
    items: list[WebhookDeliveryResponse]


class CallCreateRequest(BaseModel):
    agent_id: str = Field(min_length=3, max_length=32)
    phone_number_id: str | None = Field(default=None, min_length=3, max_length=32)
    channel: Literal["voice"] = "voice"
    direction: Literal["inbound", "outbound"]
    from_number: str = Field(min_length=6, max_length=32)
    to_number: str = Field(min_length=6, max_length=32)


class CallResponse(BaseModel):
    id: str
    agent_id: str
    phone_number_id: str | None = None
    channel: Literal["voice"]
    direction: Literal["inbound", "outbound"]
    from_number: str
    to_number: str
    status: Literal["active", "completed", "failed", "escalated"]
    outcome: str | None = None
    duration_ms: int | None = None
    recording_available: bool
    started_at: datetime
    ended_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class CallListResponse(BaseModel):
    items: list[CallResponse]
    total: int


class CallTurnCreateRequest(BaseModel):
    user_text: str = Field(min_length=1)
    assistant_text: str = Field(min_length=1)
    latency_ms: int = Field(ge=0)
    provider_breakdown: dict = Field(default_factory=dict)
    tool_calls: list[dict] = Field(default_factory=list)


class CallRespondRequest(BaseModel):
    input_text: str | None = Field(default=None, min_length=1)
    audio_ref: str | None = Field(default=None, min_length=3, max_length=255)
    voice_id: str | None = Field(default=None, min_length=2, max_length=64)

    @model_validator(mode="after")
    def validate_runtime_input(self) -> "CallRespondRequest":
        if not self.input_text and not self.audio_ref:
            raise ValueError("either input_text or audio_ref is required")
        return self


class CallTurnResponse(BaseModel):
    id: str
    call_id: str
    turn_index: int
    user_text: str
    assistant_text: str
    latency_ms: int
    provider_breakdown: dict
    tool_calls: list[dict]
    response_audio_ref: str | None = None
    finish_reason: str | None = None
    created_at: datetime


class CallTurnListResponse(BaseModel):
    items: list[CallTurnResponse]
    total: int


class CallTranscriptResponse(BaseModel):
    call_id: str
    transcript_text: str
    turns: list[CallTurnResponse]


class CallCompleteRequest(BaseModel):
    outcome: Literal["faq_resolved", "booking_created", "escalated", "lead_captured", "abandoned", "failed"]
    duration_ms: int = Field(ge=0)
    recording_available: bool = False
    summary_text: str = Field(min_length=1)
    structured_summary: dict = Field(default_factory=dict)
    failure_category: Literal["telephony", "stt", "tts", "llm", "tool", "integration", "internal"] | None = None
    failure_code: str | None = None
    failure_message: str | None = None
    escalation_reason: str | None = None
    escalation_target: str | None = None
    escalation_summary: str | None = None


class CallSummaryResponse(BaseModel):
    call_id: str
    summary_text: str
    structured_summary: dict
    created_at: datetime
    updated_at: datetime


class UsageSummaryResponse(BaseModel):
    total_calls: int
    completed_calls: int
    failed_calls: int
    escalated_calls: int
    active_calls: int
    total_duration_ms: int
    average_duration_ms: int


class UsageCostResponse(BaseModel):
    currency: Literal["USD"]
    total_cost_usd: float
    tokens_in: int
    tokens_out: int
    duration_ms: int
    components: dict


class PartnerResponse(BaseModel):
    id: str
    organization_id: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PartnerAccountCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, min_length=2, max_length=120)


class PartnerAccountResponse(BaseModel):
    id: str
    partner_id: str
    organization_id: str
    organization_name: str
    organization_slug: str
    created_at: datetime


class PartnerAccountListResponse(BaseModel):
    items: list[PartnerAccountResponse]
    total: int
