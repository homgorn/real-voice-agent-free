from __future__ import annotations

import logging

from voiceagent_api.config import settings

logger = logging.getLogger(__name__)

_OTEL_AVAILABLE = False
_prometheus_available = False

try:
    from opentelemetry import metrics, trace
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import (
        ConsoleMetricExporter,
        PeriodicExportingMetricReader,
    )
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

    _OTEL_AVAILABLE = True
except ImportError:
    pass

try:
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    _prometheus_available = True
except ImportError:
    pass


def init_opentelemetry(app=None) -> None:
    if not _OTEL_AVAILABLE:
        return

    resource = Resource.create(
        {
            "service.name": "voiceagent-api",
            "service.version": "0.2.0",
            "deployment.environment": settings.env,
        }
    )

    trace.set_tracer_provider(TracerProvider(resource=resource))
    trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))

    metric_reader = PeriodicExportingMetricReader(ConsoleMetricExporter(), export_interval_millis=60000)
    metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=[metric_reader]))

    _meter = metrics.get_meter("voiceagent-api", "0.2.0")
    _meter.create_counter(
        "http_requests_total",
        description="Total HTTP requests",
        unit="1",
    )
    _meter.create_histogram(
        "http_request_duration_seconds",
        description="HTTP request duration in seconds",
        unit="s",
    )

    if app is not None:
        FastAPIInstrumentor.instrument_app(app)

    logger.info("OpenTelemetry initialized (env=%s)", settings.env)


def close_opentelemetry() -> None:
    if not _OTEL_AVAILABLE:
        return
    try:
        trace.get_tracer_provider().shutdown()
        metrics.get_meter_provider().shutdown()
    except Exception:
        pass
    logger.info("OpenTelemetry shut down")


def get_metrics_response():
    from fastapi.responses import Response

    if not _prometheus_available:
        return Response(content="prometheus_client not installed", media_type="text/plain")
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
