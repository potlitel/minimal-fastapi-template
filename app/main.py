import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

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

from app.api.api_router import api_router, auth_router, user_router
from app.core.config import get_settings

# Configuración de recursos
resource = Resource(attributes={"service.name": "fastapi-service"})
tracer_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer_provider)

# Configuración del exportador OTLP para trazas
otlp_exporter = OTLPSpanExporter(endpoint="http://localhost:4317", insecure=True)
span_processor = BatchSpanProcessor(otlp_exporter)
tracer_provider.add_span_processor(span_processor)

# Configura el proveedor de logs
logger_provider = LoggerProvider()
otlp_exporter = OTLPLogExporter(endpoint="http://otel-collector:4317", insecure=True)
logger_provider.add_log_record_processor(BatchLogRecordProcessor(otlp_exporter))

# Asigna el proveedor al handler
handler = LoggingHandler(logger_provider=logger_provider)
logging.getLogger().addHandler(handler)

# Instrumenta el log de la aplicación
LoggingInstrumentor().instrument(set_logging_format=True)

app = FastAPI(
    title="Minimal Fastapi Postgres Template",
    version="6.1.0",
    description="https://github.com/potlitel/minimal-fastapi-template",
    openapi_url="/openapi.json",
    docs_url="/",
)

# Instrumentar FastAPI para OpenTelemetry
FastAPIInstrumentor.instrument_app(app)

# Instrumentar FastAPI para Prometheus
Instrumentator().instrument(app).expose(app)

app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"Error inesperado: {exc}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor. Revise logs para más información."},
    )

app.include_router(auth_router)
app.include_router(api_router)
app.include_router(user_router)

# Sets all CORS enabled origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        str(origin).rstrip("/")
        for origin in get_settings().security.backend_cors_origins
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Guards against HTTP Host Header attacks
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=get_settings().security.allowed_hosts,
)

# from app.core.setup_app import create_app

# app = create_app()