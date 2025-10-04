from typing import Type
from sqlalchemy.ext.asyncio import AsyncSession
from app.models import Bitacora


class AuditRepository:
    def __init__(self, db_model: Type[Bitacora]):
        """
        Inicializa el repositorio de auditoría, responsable únicamente de persistir los registros de Bitacora.

        - **param db_model**: Clase del modelo ORM Bitacora.
        """
        self.db_model = db_model # Bitacora Model
        
    async def log(self, db: AsyncSession, user_id: str, entity: str, action: str) -> None:
        """
        Registra una acción en la tabla de bitácora.
        Maneja su propia transacción (commit) para el log, haciéndola atómica respecto a la acción principal.

        - **param db**: Sesión asíncrona de la base de datos.
        - **param user_id**: ID del usuario que realizó la acción.
        - **param entity**: Nombre de la entidad afectada (ej. 'User', 'Product').
        - **param action**: Tipo de operación o acción realizada (ej. 'CREATE', 'VIEW_ALL').
        - **returns**: None.
        """
        # La lógica de transacción del log debe ser independiente
        log_entry = self.db_model(user_id=user_id, entity=entity, action=action)
        db.add(log_entry)
        try:
            # 💡 IMPORTANTE: El log debe confirmar su propia transacción para ser atómico
            # respecto al evento del log, NO al evento principal.
            await db.commit() 
            await db.refresh(log_entry)
        except Exception as e:
            await db.rollback()
            print(f"ERROR: Fallo al guardar la entrada de bitácora: {e}")
            # No lanzamos HTTPException para no interrumpir la operación principal
            # si el log falla, pero es crítico loguear el error.