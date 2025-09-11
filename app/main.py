import traceback
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from app.api.api_router import api_router, auth_router, user_router
from app.core.config import get_settings

app = FastAPI(
    title="Minimal Fastapi Postgres Template",
    version="6.1.0",
    description="https://github.com/potlitel/minimal-fastapi-template",
    openapi_url="/openapi.json",
    docs_url="/",
)

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
