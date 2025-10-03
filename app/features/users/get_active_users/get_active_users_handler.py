
import time
from app.core.repositories import BaseRepository
from sqlalchemy.ext.asyncio import AsyncSession
from app.features.users.get_active_users.get_active_users_query import GetActiveUsersQuery
from app.models import RefreshToken, User


class GetActiveUsersHandler:
    """
    Handler dedicado para obtener usuarios considerados 'activos'.
    Lógica de Negocio: Un usuario está activo si tiene al menos un Refresh Token NO expirado.
    """
    
    # El Handler aún recibe el repositorio, cumpliendo con la Inversión de Dependencias.
    def __init__(self, repository: BaseRepository[User]):
        # El repositorio debe ser tipado con el modelo User.
        self.repository = repository
        
    async def handle(self, query: GetActiveUsersQuery, db: AsyncSession):
        # 1. Aplicación de la Regla de Negocio
        # Obtener el tiempo UNIX actual (en segundos) para la comparación
        current_unix_time = int(time.time())
        
        # El token tampoco debe haber sido marcado como 'used=True'
        filter_criterion = [
            # Utilizamos la relación User.refresh_tokens y el método any()
            User.refresh_tokens.any(
                # El campo 'exp' (timestamp futuro) debe ser mayor que el tiempo actual
                (RefreshToken.exp > current_unix_time) & 
                # El token no debe haber sido consumido
                (RefreshToken.used == False)
            )
        ] 
        
        # 2. Llamada al Repositorio Genérico para la ejecución
        users = await self.repository.get_by_filters(
            db, 
            filters=filter_criterion, 
            user_id=query.user_id,
            skip=query.skip,
            limit=query.limit
        )
        return users