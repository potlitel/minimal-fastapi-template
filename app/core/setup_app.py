from contextlib import asynccontextmanager
import traceback
from typing import Any, Tuple
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.api_router import api_router, auth_router, users_router, bitacoras_router
from app.api.deps import GLOBAL_KAFKA_PRODUCER_SERVICE
from app.core.config import get_settings
from app.core.telemetry import set_noop_telemetry, setup_telemetry

KAFKA_IS_ENABLED = get_settings().kafka.enabled
TELEMETRY_IS_ENABLED = get_settings().telemetry.enabled
GLOBAL_TELEMETRY_PROCESSORS: Tuple[Any, Any, Any] = (None, None, None)
# Usamos Any temporalmente, el tipo real sería BatchSpanProcessor, BatchLogRecordProcessor

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Verificar si el productor de Kafka debe ser iniciado
    if KAFKA_IS_ENABLED:
        print("Iniciando recursos: Kafka Producer...")
        try:
            # INICIO: Asegurar que el productor se inicie correctamente
            await GLOBAL_KAFKA_PRODUCER_SERVICE.start()
        except Exception as e:
            # Crucial para el desarrollo: no queremos que la app muera solo por Kafka.
            print(f"ADVERTENCIA: Fallo al iniciar Kafka Producer. El servicio continuará sin productor. Error: {e}")
            # Puedes establecer un flag de estado global aquí si lo necesitas.
            # No obstante, si el productor está bien encapsulado, el `start()` manejará el estado.
            pass # Permitimos que el programa continúe.
    else:
        print("Kafka Producer DESHABILITADO por configuración. Omitiendo inicio.")

    # El yield permite que la aplicación entre en estado "running"
    yield

    # 2. Verificar si el productor de Kafka debe ser detenido
    if KAFKA_IS_ENABLED:
        print("Cerrando recursos: Kafka Producer...")
        try:
            # FIN: Ejecutar el cierre.
            await GLOBAL_KAFKA_PRODUCER_SERVICE.stop()
        except Exception as e:
            print(f"ADVERTENCIA: Fallo al detener Kafka Producer. Error: {e}")
            pass
    # 🔑 SHUTDOWN DE TELEMETRY: (Fuera del bloque try/except de Kafka)
    if TELEMETRY_IS_ENABLED and GLOBAL_TELEMETRY_PROCESSORS[0] is not None:
        print("Cerrando recursos: Telemetry Processors...")
        # Desempaquetar los procesadores y el proveedor
        span_processor, log_processor, tracer_provider = GLOBAL_TELEMETRY_PROCESSORS
        
        # Los procesadores de lotes deben cerrarse explícitamente
        try:
            # Nota: estos shutdown NO son asíncronos
            span_processor.shutdown()
            log_processor.shutdown()
            # Opcional: cerrar el proveedor de trazas también
            tracer_provider.shutdown() 
        except Exception as e:
            print(f"ADVERTENCIA: Fallo al cerrar Telemetry. Error: {e}")
            pass
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#     print("Iniciando recursos: Kafka Producer...")
#     try:
#         # 1. INICIO: Asegurar que el productor se inicie correctamente
#         await GLOBAL_KAFKA_PRODUCER_SERVICE.start() 
#         yield
#     finally:
#         print("Cerrando recursos: Kafka Producer...")
#         # 2. FIN: Ejecutar el cierre. Esto es crucial para evitar el __del__
#         await GLOBAL_KAFKA_PRODUCER_SERVICE.stop() 
#         # Es posible que el error provenga de que el loop se detiene antes de que stop() termine
#         # Sin embargo, con await, debería funcionar.

# Inicializar FastAPI con el Lifespan
def create_app() -> FastAPI:
    app = FastAPI(
        lifespan=lifespan,
        title=get_settings().title,
        version=get_settings().version,
        description=get_settings().description,
        openapi_url="/openapi.json",
        docs_url="/",
    )
    
    # Manejador de excepciones global
    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        print(f"Error inesperado: {exc}")
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error interno del servidor durante el request {request}. Revise logs para más información.{exc}"},
        )

    # Configuración de Middlewares
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
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=get_settings().security.allowed_hosts,
    )

    # Inclusión de Routers
    app.include_router(auth_router)
    app.include_router(api_router)
    app.include_router(users_router)
    app.include_router(bitacoras_router)
    
    # Configuración de Telemetría
    # setup_telemetry(app)
    # 🔑 CLAVE: Condición para activar la Telemetría
    if TELEMETRY_IS_ENABLED:
        print("Telemetry ACTIVA por configuración. Aplicando setup_telemetry.")
        
        # Almacenamos las instancias devueltas
        global GLOBAL_TELEMETRY_PROCESSORS
        GLOBAL_TELEMETRY_PROCESSORS = setup_telemetry(app)
    else:
        # 🚨 FIX: Desactivación explícita del estado global
        set_noop_telemetry()
        print("Telemetry DESHABILITADA por configuración. Omitiendo setup.")
    
    return app