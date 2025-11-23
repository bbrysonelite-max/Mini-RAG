from __future__ import annotations

import logging
import os
from typing import Optional

from fastapi import FastAPI
try:  # pragma: no cover
    from opentelemetry import trace
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.logging import LoggingInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    _OTEL_AVAILABLE = True
except ImportError:  # pragma: no cover
    trace = None  # type: ignore
    FastAPIInstrumentor = None  # type: ignore
    LoggingInstrumentor = None  # type: ignore
    Resource = None  # type: ignore
    TracerProvider = None  # type: ignore
    BatchSpanProcessor = None  # type: ignore
    ConsoleSpanExporter = None  # type: ignore
    OTLPSpanExporter = None  # type: ignore
    _OTEL_AVAILABLE = False

logger = logging.getLogger(__name__)
_TRACING_CONFIGURED = False


def _is_enabled() -> bool:
    return _OTEL_AVAILABLE and os.getenv("OTEL_ENABLED", "").lower() in {"1", "true", "yes"}


def setup_tracing(app: FastAPI) -> None:
    """
    Configure OpenTelemetry tracing/logging if enabled via environment.
    """
    global _TRACING_CONFIGURED
    if _TRACING_CONFIGURED or not _is_enabled():
        return
    if not _OTEL_AVAILABLE:
        logger.warning("OpenTelemetry packages not installed; skipping tracing setup.")
        return

    resource = Resource.create(
        {
            "service.name": os.getenv("OTEL_SERVICE_NAME", "mini-rag-server"),
            "deployment.environment": os.getenv("OTEL_ENVIRONMENT", "development"),
        }
    )

    provider = TracerProvider(resource=resource)  # type: ignore[arg-type]
    exporter = _create_exporter()
    provider.add_span_processor(BatchSpanProcessor(exporter))  # type: ignore[arg-type]
    trace.set_tracer_provider(provider)  # type: ignore[arg-type]

    if FastAPIInstrumentor:
        FastAPIInstrumentor().instrument_app(app)
    if LoggingInstrumentor:
        LoggingInstrumentor().instrument(set_logging_format=False)

    _TRACING_CONFIGURED = True


def _create_exporter() -> ConsoleSpanExporter:
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    headers_value = os.getenv("OTEL_EXPORTER_OTLP_HEADERS")
    if endpoint and OTLPSpanExporter is not None:
        headers: Optional[dict[str, str]] = None
        if headers_value:
            headers = {}
            for segment in headers_value.split(","):
                if "=" not in segment:
                    continue
                key, value = segment.split("=", 1)
                headers[key.strip()] = value.strip()
        return OTLPSpanExporter(endpoint=endpoint, headers=headers)

    if ConsoleSpanExporter:
        return ConsoleSpanExporter()  # type: ignore[return-value]
    raise RuntimeError("OpenTelemetry console exporter unavailable.")

