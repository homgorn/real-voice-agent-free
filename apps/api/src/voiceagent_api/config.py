from __future__ import annotations

from collections.abc import Mapping

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_api_keys(raw_value: str) -> dict[str, set[str]]:
    parsed: dict[str, set[str]] = {}
    for item in raw_value.split(";"):
        item = item.strip()
        if not item:
            continue
        try:
            _name, key, scopes_raw = item.split(",", 2)
        except ValueError:
            continue
        scopes = {scope.strip() for scope in scopes_raw.split("|") if scope.strip()}
        if key.strip():
            parsed[key.strip()] = scopes
    return parsed


def _parse_bootstrap_api_keys(raw_value: str) -> list[dict[str, object]]:
    parsed: list[dict[str, object]] = []
    for item in raw_value.split(";"):
        item = item.strip()
        if not item:
            continue
        try:
            name, key, scopes_raw = item.split(",", 2)
        except ValueError:
            continue
        scopes = [scope.strip() for scope in scopes_raw.split("|") if scope.strip()]
        if key.strip():
            parsed.append({"name": name.strip(), "key": key.strip(), "scopes": scopes})
    return parsed


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="VOICEAGENT_",
        case_sensitive=False,
        extra="ignore",
    )

    env: str = "development"
    log_level: str = "INFO"
    database_url: str = "sqlite+pysqlite:///./voiceagent.db"
    webhook_timeout_seconds: float = 5.0
    webhook_max_attempts: int = 5
    webhook_retry_backoff_seconds: int = 30
    webhook_delivery_batch_size: int = 25
    webhook_worker_poll_interval_seconds: float = 5.0
    idempotency_ttl_seconds: int = 86400
    runtime_default_voice_id: str = "alloy"
    lemon_squeezy_api_base: str = "https://api.lemonsqueezy.com"
    lemon_squeezy_webhook_secret: str = "test-signing-secret"
    default_organization_id: str = "org_default"
    default_organization_name: str = "Default Organization"
    allowed_origins: str = "*"
    allowed_hosts: str = "*"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_pool_recycle: int = 3600
    valkey_url: str = ""
    rate_limit_default: int = 60
    rate_limit_strict: int = 10
    api_keys: str = Field(
        default="bootstrap,dev-secret-key,orgs:read|orgs:write|api_keys:read|api_keys:write|billing:read|billing:write|agents:read|agents:write|agents:publish|"
        "bookings:read|bookings:write|calls:read|calls:write|events:read|"
        "templates:read|templates:write|phone_numbers:read|phone_numbers:write|integrations:read|integrations:write|"
        "knowledge_bases:read|knowledge_bases:write|usage:read|partners:read|partners:write|webhooks:read|webhooks:write;"
        "readonly,read-only-key,orgs:read|api_keys:read|billing:read|agents:read|bookings:read|calls:read|events:read|"
        "templates:read|phone_numbers:read|integrations:read|knowledge_bases:read|usage:read|partners:read|webhooks:read"
    )

    @property
    def parsed_api_keys(self) -> Mapping[str, set[str]]:
        return _parse_api_keys(self.api_keys)

    @property
    def bootstrap_api_keys(self) -> list[dict[str, object]]:
        return _parse_bootstrap_api_keys(self.api_keys)


settings = Settings()
