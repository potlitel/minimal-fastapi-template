from typing import List
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user, get_session
from app.core.cqrs.mediator import mediator
from app.core.repositories import UserRepository
from app.features.users.get_active_users.get_active_users_handler import GetActiveUsersHandler
from app.features.users.get_active_users.get_active_users_query import GetActiveUsersQuery
from app.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.responses import UserResponse

# Instanciar el Repositorio de Usuarios
user_repository = UserRepository(db_model=User)

# 🚨 REGISTRO DEL MEDIATOR (Mapping de la Vertical Slice) 🚨
mediator.register_handler(GetActiveUsersQuery, GetActiveUsersHandler(repository=user_repository))

router = APIRouter(prefix="/users", tags=["Users"])

@router.get("/active", response_model=List[UserResponse], summary="Get all active users")
async def read_active_users(
    db: AsyncSession = Depends(get_session),
    skip: int = 0, 
    limit: int = 10, 
    current_user: User = Depends(get_current_user)
):
    """
    Endpoint para el caso de uso específico: Obtener Usuarios Activos.
    """
    # 1. Crear la Query (sin pasar filtros, el Handler los conoce)
    query = GetActiveUsersQuery(db=db, user_id=current_user.user_id, skip=skip, limit=limit)
    
    # 2. Enviar la Query al Mediator
    return await mediator.send(query, db)