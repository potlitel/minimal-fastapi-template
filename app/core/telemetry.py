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
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.sdk.trace import TracerProvider as NoOpTracerProvider
from opentelemetry.sdk._logs import LoggerProvider as NoOpLoggerProvider

from fastapi import FastAPI
from app.core.config import get_settings


# Lista global para mantener las referencias de los instrumentadores
# para poder desinstrumentar si es necesario.
# (Aunque en FastAPI se hace con uninstrument_app, es bueno tener las referencias)
ACTIVE_INSTRUMENTORS: list[BaseInstrumentor] = []

def setup_telemetry(app: FastAPI):
    """
    Configura y activa OpenTelemetry para trazas (Tracing) y logs.
    Retorna los procesadores y el proveedor de trazas para el cierre (shutdown) manual.
    """
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
    # CAPTURAMOS los procesadores:
    span_processor = BatchSpanProcessor(otlp_exporter)
    tracer_provider.add_span_processor(span_processor)
    
    # Configura el proveedor de logs
    logger_provider = LoggerProvider()
    otlp_exporter = OTLPLogExporter(endpoint="http://localhost:4317", insecure=True)
    log_processor = BatchLogRecordProcessor(otlp_exporter)
    logger_provider.add_log_record_processor(log_processor)
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
    
    # 🔑 CLAVE: Devolver los objetos que necesitan shutdown
    return span_processor, log_processor, tracer_provider
    
    # Nota: TracerProvider y LoggerProvider también tienen shutdown(), pero 
    # a menudo basta con cerrar sus procesadores, ya que estos manejan la exportación.
    # Cerrar los procesadores de lotes es lo más crítico.
    
def set_noop_telemetry():
    """
    Desactiva explícitamente OpenTelemetry estableciendo proveedores No-Op.
    Al no usar el Log API, evitamos el 'ImportError'.
    """
    # Usamos las rutas de clases que están disponibles en tu sistema.
    from opentelemetry.sdk.trace import TracerProvider as NoOpTracerProvider
    
    # 1. Reemplazar el TracerProvider global con uno que no haga nada
    trace.set_tracer_provider(NoOpTracerProvider())
    
    # 2. LoggerProvider No-Op: Al no llamar a logs.set_logger_provider(), 
    # la librería se comporta como No-Op para logs si no se configura un handler.
    # Desinstrumentamos el logging para asegurar que no capture nada.
    try:
        LoggingInstrumentor().uninstrument()
    except Exception:
        pass # Ignoramos si no estaba instrumentado
    
    # También debemos eliminar los handlers OTLP que se hayan añadido
    root_logger = logging.getLogger()
    for handler in root_logger.handlers:
        if isinstance(handler, LoggingHandler):
            root_logger.removeHandler(handler)
            
    print("OpenTelemetry configurado a modo NO-OP.")