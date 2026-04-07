from __future__ import annotations

from functools import lru_cache

from openai import OpenAI

from voiceagent_api.config import settings


def openai_enabled() -> bool:
    return bool(settings.openai_api_key)


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    client_options: dict[str, object] = {
        "api_key": settings.openai_api_key,
        "timeout": settings.openai_timeout_seconds,
    }
    if settings.openai_base_url:
        client_options["base_url"] = settings.openai_base_url
    return OpenAI(**client_options)


def reset_openai_client() -> None:
    get_openai_client.cache_clear()
