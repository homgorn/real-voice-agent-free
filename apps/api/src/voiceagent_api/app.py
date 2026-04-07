from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from voiceagent_api.config import settings
from voiceagent_api.db import close_database, create_database, ping_database
from voiceagent_api.errors import VoiceAgentError
from voiceagent_api.middleware import RateLimitMiddleware
from voiceagent_api.otel import close_opentelemetry, get_metrics_response, init_opentelemetry
from voiceagent_api.schemas import ErrorResponse

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.env == "test":
        yield
        return
    logger.info("Starting VoiceAgent API (env=%s)", settings.env)
    try:
        await create_database()
        await ping_database()
        logger.info("Database initialized and ready")
    except Exception:
        logger.warning("Database not available at startup (env=%s)", settings.env)
    try:
        init_opentelemetry(app)
    except Exception:
        logger.warning("OpenTelemetry not available")
    yield
    logger.info("Shutting down VoiceAgent API")
    try:
        await close_database()
    except Exception:
        pass
    try:
        close_opentelemetry()
    except Exception:
        pass
    logger.info("Database connections closed")


def create_app() -> FastAPI:
    app = FastAPI(
        title="VoiceAgent API",
        version="0.2.0",
        lifespan=lifespan,
        docs_url="/docs" if settings.env != "production" else None,
        redoc_url="/redoc" if settings.env != "production" else None,
    )

    app.add_middleware(SecurityHeadersMiddleware)

    if settings.env != "production":
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        allowed = [o.strip() for o in settings.allowed_origins.split(",") if o.strip()]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allowed,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=[
                "Authorization",
                "Content-Type",
                "Idempotency-Key",
                "X-Trace-Id",
            ],
            max_age=600,
        )

    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.allowed_hosts.split(",") if settings.allowed_hosts else ["*"],
    )

    app.add_middleware(RateLimitMiddleware)

    from voiceagent_api.routers.agents import router as agents_router
    from voiceagent_api.routers.api_keys import router as api_keys_router
    from voiceagent_api.routers.billing import router as billing_router
    from voiceagent_api.routers.bookings import router as bookings_router
    from voiceagent_api.routers.calls import router as calls_router
    from voiceagent_api.routers.dashboard import router as dashboard_router
    from voiceagent_api.routers.events import router as events_router
    from voiceagent_api.routers.health import router as health_router
    from voiceagent_api.routers.integrations import router as integrations_router
    from voiceagent_api.routers.knowledge_bases import router as knowledge_bases_router
    from voiceagent_api.routers.organizations import router as organizations_router
    from voiceagent_api.routers.partners import router as partners_router
    from voiceagent_api.routers.phone_numbers import router as phone_numbers_router
    from voiceagent_api.routers.usage import router as usage_router
    from voiceagent_api.routers.webhooks import router as webhooks_router

    app.include_router(health_router)
    app.include_router(organizations_router)
    app.include_router(api_keys_router)
    app.include_router(billing_router)
    app.include_router(agents_router)
    app.include_router(calls_router)
    app.include_router(dashboard_router)
    app.include_router(bookings_router)
    app.include_router(phone_numbers_router)
    app.include_router(integrations_router)
    app.include_router(knowledge_bases_router)
    app.include_router(partners_router)
    app.include_router(webhooks_router)
    app.include_router(events_router)
    app.include_router(usage_router)

    @app.get("/metrics")
    async def metrics_endpoint():
        return get_metrics_response()

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        from voiceagent_api.routers._helpers import trace_id_from_request

        trace_id = trace_id_from_request(request)
        body = ErrorResponse(
            error={
                "code": "validation_error",
                "message": "Invalid request payload",
                "category": "validation",
                "trace_id": trace_id,
            }
        )
        return JSONResponse(status_code=422, content=body.model_dump())

    @app.exception_handler(VoiceAgentError)
    async def voiceagent_error_handler(request: Request, exc: VoiceAgentError) -> JSONResponse:
        from voiceagent_api.routers._helpers import trace_id_from_request

        trace_id = trace_id_from_request(request)
        body = ErrorResponse(
            error={
                "code": exc.code,
                "message": exc.message,
                "category": exc.category,
                "trace_id": trace_id,
            }
        )
        return JSONResponse(status_code=exc.status_code, content=body.model_dump())

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        from voiceagent_api.routers._helpers import trace_id_from_request

        trace_id = trace_id_from_request(request)
        logger.error(
            "Unhandled exception: %s",
            exc,
            exc_info=True,
            extra={"path": request.url.path, "trace_id": trace_id},
        )
        body = ErrorResponse(
            error={
                "code": "internal_error",
                "message": "Internal server error",
                "category": "internal",
                "trace_id": trace_id,
            }
        )
        return JSONResponse(status_code=500, content=body.model_dump())

    return app


app = create_app()
