# Esta clase hereda TODA la funcionalidad CRUD de BaseRepository
# y está tipada genéricamente para saber que maneja objetos 'Bitacora'.
from typing import Optional, Type
from app.core.repositories.audit import AuditRepository
from app.core.repositories.base import BaseRepository
from app.models import Bitacora
from sqlalchemy.ext.asyncio import AsyncSession

class BitacoraRepository(BaseRepository):
    """
    Repositorio específico para la entidad Bitacora. 
    Hereda de BaseRepository pero está configurado para ser auditable por el AuditRepository (inyección cruzada controlada).
    Convención estándar en patrones de diseño para dejar un punto donde se pueda añadir lógica específica más adelante
    (ej., get_bitcora_by_user).
    """
    # def __init__(self, db_model: Type[Bitacora]):
    #     self.db_model = db_model # Bitacora Model
    # Sobreescribimos el constructor para no requerir la inyección de auditoría,
    # ya que es el repositorio de auditoría.
    def __init__(self, db_model: Type[Bitacora], audit_repo: Optional[AuditRepository] = None):
        """
        Inicializa el BitacoraRepository.

        - **param db_model**: Clase del modelo ORM Bitacora.
        - **param audit_repo**: Instancia del AuditRepository para auditar el acceso a los registros de Bitacora (logeo cruzado).
                                Debe ser una instancia que solo haga 'log'.
        """
        super().__init__(db_model, audit_repo)
        # O simplemente: self.db_model = db_model 
        # y omitir la llamada a super().__init__() si prefiere mantenerlo simple