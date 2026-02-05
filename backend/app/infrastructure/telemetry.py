"""OpenTelemetry integration for distributed tracing and monitoring."""
import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# OpenTelemetry components
_tracer = None
_meter = None
_initialized = False


def initialize_telemetry(
    service_name: str = "cc-switch",
    otlp_endpoint: Optional[str] = None,
    enable_tracing: bool = True,
    enable_metrics: bool = True
):
    """
    Initialize OpenTelemetry for distributed tracing and metrics.
    
    Args:
        service_name: Name of the service for tracing
        otlp_endpoint: OTLP endpoint URL (e.g., http://localhost:4318)
        enable_tracing: Enable distributed tracing
        enable_metrics: Enable metrics collection
    """
    global _tracer, _meter, _initialized
    
    if _initialized:
        logger.warning("Telemetry already initialized")
        return
    
    try:
        from opentelemetry import trace, metrics
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.resources import Resource
        
        # Get OTLP endpoint from environment or parameter
        otlp_endpoint = otlp_endpoint or os.getenv("OTLP_ENDPOINT")
        
        # Create resource with service name
        resource = Resource.create({
            "service.name": service_name,
            "service.version": os.getenv("SERVICE_VERSION", "1.0.0"),
        })
        
        if enable_tracing:
            # Setup tracing
            trace.set_tracer_provider(TracerProvider(resource=resource))
            _tracer = trace.get_tracer(__name__)
            
            if otlp_endpoint:
                try:
                    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
                    span_exporter = OTLPSpanExporter(endpoint=f"{otlp_endpoint}/v1/traces")
                    span_processor = BatchSpanProcessor(span_exporter)
                    trace.get_tracer_provider().add_span_processor(span_processor)
                    logger.info(f"OpenTelemetry tracing enabled with OTLP endpoint: {otlp_endpoint}")
                except Exception as e:
                    logger.warning(f"Failed to setup OTLP exporter: {e}. Tracing will use console output.")
            else:
                logger.info("OpenTelemetry tracing enabled (console exporter)")
        
        if enable_metrics:
            # Setup metrics
            metrics.set_meter_provider(MeterProvider(resource=resource))
            _meter = metrics.get_meter(__name__)
            
            if otlp_endpoint:
                try:
                    from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
                    from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
                    metric_exporter = OTLPMetricExporter(endpoint=f"{otlp_endpoint}/v1/metrics")
                    metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=5000)
                    metrics.get_meter_provider()._sdk_config.metric_readers.append(metric_reader)
                    logger.info(f"OpenTelemetry metrics enabled with OTLP endpoint: {otlp_endpoint}")
                except Exception as e:
                    logger.warning(f"Failed to setup OTLP metrics exporter: {e}. Metrics will use console output.")
            else:
                logger.info("OpenTelemetry metrics enabled (console exporter)")
        
        _initialized = True
        logger.info("OpenTelemetry initialized successfully")
        
    except ImportError:
        logger.warning("OpenTelemetry packages not installed. Install with: pip install opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp")
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry: {e}", exc_info=True)


def get_tracer():
    """Get OpenTelemetry tracer."""
    if not _initialized:
        logger.warning("Telemetry not initialized. Call initialize_telemetry() first.")
    return _tracer


def get_meter():
    """Get OpenTelemetry meter."""
    if not _initialized:
        logger.warning("Telemetry not initialized. Call initialize_telemetry() first.")
    return _meter


def instrument_fastapi(app):
    """
    Instrument FastAPI application with OpenTelemetry.
    
    Args:
        app: FastAPI application instance
    """
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI instrumented with OpenTelemetry")
    except ImportError:
        logger.warning("FastAPI instrumentation not available. Install opentelemetry-instrumentation-fastapi")
    except Exception as e:
        logger.error(f"Failed to instrument FastAPI: {e}", exc_info=True)


def instrument_httpx():
    """
    Instrument httpx with OpenTelemetry.
    """
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        HTTPXClientInstrumentor().instrument()
        logger.info("httpx instrumented with OpenTelemetry")
    except ImportError:
        logger.warning("httpx instrumentation not available. Install opentelemetry-instrumentation-httpx")
    except Exception as e:
        logger.error(f"Failed to instrument httpx: {e}", exc_info=True)


