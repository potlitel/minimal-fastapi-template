import logging
from opentelemetry import trace
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from prometheus_fastapi_instrumentator import Instrumentator

# Instrumentar logs
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import OTLPLogExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor

from fastapi import FastAPI
from app.core.config import get_settings

def setup_telemetry(app: FastAPI):
    settings = get_settings()

    # Configuración de OpenTelemetry
    
    # Configuración de recursos
    resource = Resource(attributes={"service.name": settings.telemetry.service_name})
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    
    # Configuración del exportador OTLP para trazas
    otlp_exporter = OTLPSpanExporter(
        endpoint=settings.telemetry.otlp_endpoint,
        insecure=settings.telemetry.insecure_otlp
    )
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
    
    # Configura el proveedor de logs
    logger_provider = LoggerProvider()
    otlp_exporter = OTLPLogExporter(endpoint="http://localhost:4317", insecure=True)
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_exporter))
    # Asigna el proveedor al handler
    handler = LoggingHandler(logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)

    # Instrumentación de la aplicación
    
    # Instrumentar FastAPI para OpenTelemetry
    FastAPIInstrumentor.instrument_app(app)
    # Instrumentar FastAPI para Prometheus
    Instrumentator().instrument(app).expose(app)
    # Instrumenta el log de la aplicación
    LoggingInstrumentor().instrument(set_logging_format=True)