from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import api_messages
from app.core import database_session
from app.core.repositories.audit import AuditRepository
from app.core.repositories.bitacora import BitacoraRepository
from app.core.repositories.user import UserRepository
from app.core.security.jwt import verify_jwt_token
from app.models import Bitacora, User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/access-token")
"""
Esquema de seguridad OAuth2.

Define el mecanismo para esperar un token Bearer en el encabezado 'Authorization'.
La URL 'auth/access-token' informa a los clientes dónde obtener dicho token.
Este objeto se utiliza como una dependencia en las rutas protegidas.
"""

# -----------------------------------------------------------------------------
## Gestión de Sesiones de Base de Datos
# -----------------------------------------------------------------------------
async def get_session() -> AsyncGenerator[AsyncSession]:
    """
    Dependencia de FastAPI para la gestión asíncrona de la sesión de base de datos (Unit of Work).

    Este patrón garantiza que:
    1. Se obtenga una nueva sesión de SQLAlchemy al inicio de cada solicitud.
    2. La sesión se mantenga abierta durante toda la vida útil de la solicitud (request).
    3. La sesión se cierre automáticamente al finalizar, independientemente del resultado
       (éxito o excepción), gracias al uso de 'async with' (context manager).

    :yield: La sesión asíncrona (AsyncSession).
    """
    async with database_session.get_async_session() as session:
        yield session


# -----------------------------------------------------------------------------
## Lógica de Autenticación y Autorización
# -----------------------------------------------------------------------------
async def get_current_user(
    # 🔑 Dependency: Extrae el token 'Bearer' del encabezado de la solicitud
    token: Annotated[str, Depends(oauth2_scheme)],
    # 🔑 Dependency: Inyecta la sesión de DB para la consulta
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Dependencia de FastAPI responsable de la autenticación del usuario a partir del token JWT.

    Este proceso verifica la validez del token, extrae el identificador del usuario (sub),
    y consulta la base de datos para recuperar la instancia del modelo 'User'.

    :param token: El token JWT extraído del encabezado 'Authorization' por oauth2_scheme.
    :param session: Sesión de base de datos inyectada.
    :raises HTTPException 401: Si el token es inválido o el usuario ha sido eliminado.
    :returns: La instancia del modelo User si el token es válido y el usuario existe.
    """
    
    # 1. VERIFICACIÓN DEL TOKEN:
    # Se valida la firma y el tiempo de expiración del JWT, retornando el payload (claims).
    token_payload = verify_jwt_token(token)

    # 2. BÚSQUEDA DEL USUARIO:
    # Se usa el 'sub' (subject) del payload (típicamente user_id) para buscar el usuario en la DB.
    user = await session.scalar(select(User).where(User.user_id == token_payload.sub))

    # 3. VERIFICACIÓN DE EXISTENCIA:
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=api_messages.JWT_ERROR_USER_REMOVED,
        )
    
    # 4. ÉXITO:
    # El usuario está autenticado y activo, se devuelve el objeto User
    return user

# =================================================================
# 1. REPOSITORIOS GLOBALES (Contenedor de Inversión de Control)
# =================================================================

# 1.1. Instancia Global del AuditRepository
GLOBAL_AUDIT_REPO = AuditRepository(db_model=Bitacora)

# 1.2. Instancia Global del UserRepository
# 🔑 CLAVE: Inyectamos GLOBAL_AUDIT_REPO al inicializar UserRepository
GLOBAL_USER_REPO = UserRepository(
    db_model=User, 
    audit_repo=GLOBAL_AUDIT_REPO 
)

# 🔑 1.3. Instancia Global del BitacoraRepository (NO usa auditoría)
GLOBAL_BITACORA_REPO = BitacoraRepository(
    db_model=Bitacora, 
    audit_repo=None # Correcto: no se audita a sí mismo
)

# =================================================================
# 2. DEPENDENCIAS DE FASTAPI (Funciones para inyección)
# =================================================================

def get_audit_repository():
    """Dependencia para obtener la instancia global del AuditRepository."""
    return GLOBAL_AUDIT_REPO

def get_user_repository():
    """Dependencia para obtener la instancia global del UserRepository."""
    return GLOBAL_USER_REPO

def get_bitacora_repository():
    """Dependencia para obtener la instancia global del BitacoraRepository."""
    return GLOBAL_BITACORA_REPO

