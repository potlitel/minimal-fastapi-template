from fastapi import HTTPException, status
from sqlalchemy import select
from app.api import api_messages
from app.core.repositories.base import BaseRepository
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security.password import get_password_hash
from app.models import Base, User

class UserRepository(BaseRepository):
    """
    Repositorio específico para la entidad User. 
    Aquí se añadirán métodos personalizados de persistencia o consulta para usuarios.
    """
    async def create(self, db: AsyncSession, item_data: dict, user_id: str = None) -> Base:
        """
        Crea un nuevo registro de usuario en la base de datos y audita la acción.

        - **param db**: Sesión asíncrona de la base de datos.
        - **param item_data**: Diccionario de datos para el nuevo registro de usuario.
        - **param user_id**: ID del usuario que ejecuta la operación (para fines de auditoría).
        - **returns**: Instancia del modelo creado.
        """
        # lógica personalizada para User antes o después
        # Ejemplo: hash de contraseña, validaciones extra
        user = await db.scalar(select(User).where(User.email == item_data['email']))
        if user is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_messages.EMAIL_ADDRESS_ALREADY_USED,
            )
        user = User(
            email=item_data['email'],
            hashed_password=get_password_hash(item_data['password']),
        )
        # Crear un diccionario solo con los atributos necesarios
        user_data = {
            'email': user.email,
            'hashed_password': user.hashed_password,
        }
        return await super().create(db, user_data, user_id)