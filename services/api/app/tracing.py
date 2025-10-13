"""Optional OpenTelemetry tracing integration for ApplyLens API.

Enable by setting environment variables:
  OTEL_ENABLED=1
  OTEL_EXPORTER_OTLP_ENDPOINT=http://jaeger:4318

This will instrument FastAPI, SQLAlchemy, and HTTP clients automatically.
"""

import logging
import os

logger = logging.getLogger(__name__)


def init_tracing(app):
    """Initialize OpenTelemetry tracing if enabled via environment.

    Args:
        app: FastAPI application instance

    Environment Variables:
        OTEL_ENABLED: Set to "1" to enable tracing
        OTEL_EXPORTER_OTLP_ENDPOINT: OTLP endpoint (e.g., http://jaeger:4318)
        OTEL_SERVICE_NAME: Service name (default: "applylens-api")
    """
    if os.getenv("OTEL_ENABLED", "0") != "1":
        logger.info("OpenTelemetry tracing is disabled (OTEL_ENABLED != 1)")
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import \
            OTLPSpanExporter
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.requests import RequestsInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import \
            SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Service resource
        service_name = os.getenv("OTEL_SERVICE_NAME", "applylens-api")
        resource = Resource.create(
            {
                "service.name": service_name,
                "service.version": os.getenv("APP_VERSION", "unknown"),
                "deployment.environment": os.getenv("ENV", "development"),
            }
        )

        # Tracer provider
        provider = TracerProvider(resource=resource)

        # OTLP exporter
        otlp_endpoint = os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318"
        )
        exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

        # Set global tracer
        trace.set_tracer_provider(provider)

        # Instrument FastAPI
        FastAPIInstrumentor.instrument_app(app)
        logger.info("✓ FastAPI instrumented for tracing")

        # Instrument SQLAlchemy
        from app.db import engine

        SQLAlchemyInstrumentor().instrument(engine=engine)
        logger.info("✓ SQLAlchemy instrumented for tracing")

        # Instrument HTTP requests
        RequestsInstrumentor().instrument()
        logger.info("✓ Requests instrumented for tracing")

        logger.info(
            f"✓ OpenTelemetry tracing initialized (service: {service_name}, endpoint: {otlp_endpoint})"
        )

    except ImportError as e:
        logger.warning(f"OpenTelemetry libraries not installed: {e}")
        logger.warning(
            "Install with: pip install opentelemetry-distro opentelemetry-exporter-otlp"
        )
    except Exception as e:
        logger.error(f"Failed to initialize tracing: {e}")
