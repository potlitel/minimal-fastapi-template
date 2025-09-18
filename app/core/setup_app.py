import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.api_router import api_router, auth_router, user_router, bitacora_router
from app.core.config import get_settings
from app.core.telemetry import setup_telemetry

def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.title,
        version=settings.version,
        description=settings.description,
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
            content={"detail": "Error interno del servidor. Revise logs para más información."},
        )

    # Configuración de Middlewares
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            str(origin).rstrip("/")
            for origin in settings.security.backend_cors_origins
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.security.allowed_hosts,
    )

    # Inclusión de Routers
    app.include_router(auth_router)
    app.include_router(api_router)
    app.include_router(user_router)
    app.include_router(bitacora_router)
    
    # Configuración de Telemetría
    setup_telemetry(app)
    
    return app