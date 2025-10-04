# # repositories.py
# from fastapi import Depends, HTTPException, status
# from sqlalchemy import and_, select
# from sqlalchemy.orm import Session
# from sqlalchemy.exc import IntegrityError, SQLAlchemyError
# from sqlalchemy.ext.asyncio import AsyncSession
# from app.api import api_messages, deps
# from typing import Any, List, Optional, Type
# from sqlalchemy import delete
# from sqlalchemy.future import select

# from app.core.constants import CREATE_OPERATION, DELETE_OPERATION, GET_ALL_OPERATION, GET_BY_FILTERS, GET_ONE_OPERATION, UPDATE_OPERATION
# from app.core.security.password import get_password_hash
# from app.models import Base, Bitacora, User

# from typing import TypeVar, Generic

# # 1. Definir una variable de tipo para el Modelo de Base de Datos (TDBModel)
# # Esto le dice a Python que esta variable de tipo será reemplazada por un modelo (ej. User, Pet)
# TDBModel = TypeVar('TDBModel', bound=Base) 

# class BaseRepository(Generic[TDBModel]):
#     def __init__(self, db_model: Type[TDBModel]):
#         """
#         Initialize the repository with a specific SQLAlchemy ORM model.

#         - **param db_model**: The ORM model class representing a database table.
#         """
#         self.db_model = db_model
        
#     async def _log_action(self, db: AsyncSession, user_id: str, entity: str, action: str):
#         log_entry = Bitacora(user_id=user_id, entity=entity, action=action)
#         db.add(log_entry)
#         await db.commit()

#     async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 10, user_id: str = None):
#         """
#         Retrieve a list of all records for the model, with pagination.

#         - **param db**: Database session for async operations.
#         - **param skip**: Number of records to skip (offset).
#         - **param limit**: Maximum number of records to return.
#         - **returns**: List of model instances.
#         - **raises**: 500 HTTPException if database query fails.
#         """
#         try:
#             print(f"La consulta get_all se está ejecutando para el modelo: {self.db_model.__name__}")
#             result = await db.execute(select(self.db_model).offset(skip).limit(limit))
#             if user_id:
#                 await self._log_action(db, user_id, self.db_model.__name__, GET_ALL_OPERATION)
#             return result.scalars().all()
#         except SQLAlchemyError as e:
#             # Logging o print del error
#             print(f"Error en get_all for {self.db_model} entity: {e}")
#             raise HTTPException(status_code=500, detail="Error al obtener todos los registros")

#     async def get_by_id(self, item_id: str, db: AsyncSession, user_id: str = None, id_column: str = "id"):
#         """
#         Retrieve a single record by its unique identifier.

#         - **param item_id**: ID of the record to fetch.
#         - **param db**: Database session.
#         - **returns**: Single model instance or None.
#         - **raises**: 500 HTTPException if retrieval query fails, 404 if not found.
#         - **param id_column**: Name of the column to use for filtering (e.g., 'id', 'uuid', 'slug').
#         """
#         try: 
#             # --- CAMBIO CLAVE: Usar getattr() para obtener la columna dinámicamente ---    
#             # 1. Obtener la columna del modelo usando su nombre (id_column)
#             id_attribute = getattr(self.db_model, id_column)
#             print(f"La consulta get_by_id se está ejecutando para el modelo: {self.db_model.__name__} usando la columna id: {id_attribute}")
#             # 2. Construir la sentencia de selección
#             stmt = select(self.db_model).filter(id_attribute == item_id)
#             # stmt = select(self.db_model).filter(self.db_model.user_id == item_id)
#             result = await db.execute(stmt)
#             db_item = result.scalars().first()
            
#             # 1. VERIFICACIÓN DE ELEMENTO NO ENCONTRADO (404)
#             if db_item is None:
#                 raise HTTPException(
#                     status_code=404, 
#                     detail=f"{self.db_model.__name__} not found"
#                 )
#             # 2. Lógica de Log (Solo si el elemento fue encontrado)
#             if user_id:
#                 await self._log_action(db, user_id, self.db_model.__name__, GET_ONE_OPERATION)
#             # 3. Retorno del elemento
#             return db_item
    
#         except HTTPException:
#         # Capturamos la 404 que acabamos de lanzar y la propagamos.
#             raise
        
#         except SQLAlchemyError as e:
#             # Capturamos cualquier error de DB (e.g., timeout, sintaxis, conexión) y lanzamos 500.
#             print(f"Error en get_by_id for {self.db_model} entity: {e}")
#             raise HTTPException(status_code=500, detail=f"Error en get_by_id for {self.db_model} entity")

#     async def create(self, db: AsyncSession, item_data: dict, user_id: str = None) -> Base:
#         """
#         Create a new record in the database.

#         - **param db**: Database session.
#         - **param item_data**: Dictionary of data for new record.
#         - **returns**: Created model instance.
#         - **raises**: 400 HTTPException if there is a database integrity error 
#           (e.g., duplicate email).
#         """
#         db_item = self.db_model(**item_data)
#         db.add(db_item)
#         try:
#             await db.commit()
#             await db.refresh(db_item)
#             if user_id:
#                 await self._log_action(db, user_id, self.db_model.__name__, CREATE_OPERATION)
#         except IntegrityError:  # pragma: no cover
#             await db.rollback()

#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=api_messages.EMAIL_ADDRESS_ALREADY_USED,
#             )
#         return db_item

#     async def update(self, db: AsyncSession, db_item, item_data: dict, user_id: str = None) -> Base:
#         """
#         Update an existing record with new data.

#         - **param db**: Database session.
#         - **param db_item**: Existing instance to update.
#         - **param item_data**: Dictionary of fields to modify.
#         - **returns**: Updated model instance.
#         """
#         try:
#             for key, value in item_data.items():
#                 setattr(db_item, key, value)
#             await db.commit()
#             await db.refresh(db_item)
#             if user_id:
#                 await self._log_action(db, user_id, self.db_model.__name__, UPDATE_OPERATION)
#         except SQLAlchemyError as e:
#             await db.rollback()
#             print(f"Error en update for {self.db_model} entity: {e}")
#             raise HTTPException(status_code=500, detail="Error al actualizar el registro")
#         return db_item

#     async def delete(self, item_id: Any, db: AsyncSession, user_id: str = None, id_column: str = "id"):
#         """
#         Delete a record from the database by its ID.
        
#         - **param item_id**: The unique identifier of the item to delete.
#         - **param db**: Database session.
#         - **param id_column**: Name of the column to use for lookup (e.g., 'id', 'uuid').
#         - **returns**: Confirmation message or raises 404.
#         """
#         # 1. Buscar el elemento (Esto se hacía antes en el router, pero es mejor encapsularlo aquí)
#         # Se asume que tienes un método self.get_by_id(id, db, user_id)
#         db_item_to_delete = await self.get_by_id(item_id, db, user_id=user_id, id_column=id_column)
        
#         if not db_item_to_delete:
#             # El repositorio o el handler deben lanzar el error si no se encuentra
#             raise HTTPException(status_code=404, detail=f"{self.db_model.__name__} not found")
            
#         try:
#             # 2. Eliminar el objeto encontrado
#             await db.delete(db_item_to_delete)
#             await db.commit()
#             if user_id:
#                 # Asumiendo que _log_action está disponible
#                 await self._log_action(db, user_id, self.db_model.__name__, DELETE_OPERATION) 
                
#         except SQLAlchemyError as e:
#             await db.rollback()
#             print(f"Error en delete for {self.db_model} entity: {e}")
#             raise HTTPException(status_code=500, detail="Error al eliminar el registro")
#         return None    
    
#     # Define tu método en la clase BaseRepository:
#     async def delete_by_object(self, db: AsyncSession, db_item_to_delete: Base, user_id: Optional[str] = None) -> None:
#         """
#         Deletes a record from the database using an already loaded/validated ORM model instance.
#         This is the preferred method when the object has been retrieved by a Handler (e.g., DeleteItemHandler).

#         :param db: The active asynchronous SQLAlchemy session.
#         :param db_item_to_delete: The existing ORM model instance (e.g., the 'User' instance) to be deleted.
#         :param user_id: The ID of the user performing the operation (for logging/auditing purposes).
#         :returns: None, indicating a successful response (HTTP 204 No Content).
#         :raises HTTPException: If a SQLAlchemy error occurs (e.g., concurrency or foreign key constraint).
#         """
#         try:
#             # 1. Adjuntar/Fusionar el objeto a la sesión activa (CLAVE PARA LA ELIMINACIÓN)
#             # Esto asegura que el objeto es conocido y rastreado por la sesión 'db'.
#             db_item_to_delete = await db.merge(db_item_to_delete)
#             # 1. Eliminar el objeto adjunto
#             await db.delete(db_item_to_delete)
#             # 3. Confirmar la transacción
#             await db.commit()
            
#             # 2. Loguear la acción (si aplica)
#             if user_id:
#                 # Asegúrate de que DELETE_OPERATION esté definida y _log_action exista
#                 await self._log_action(db, user_id, self.db_model.__name__, DELETE_OPERATION) 
                
#         except SQLAlchemyError as e:
#             await db.rollback()
#             print(f"Error en delete_by_object for {self.db_model.__name__}: {e}")
#             # Este error es típicamente un error de concurrencia o de la DB (HTTP 500)
#             raise HTTPException(status_code=500, detail="Error al eliminar el registro en la base de datos")
            
#         return None
    
#     async def delete_by_id(self, item_id: Any, db: AsyncSession, user_id: Optional[str] = None, id_column: str = "id"):
#         """
#         Deletes a record by directly executing a DELETE statement based on a key.
#         This high-performance method is used for fast deletions that bypass loading the object 
#         into the session first.

#         :param item_id: The value of the primary key or the ID column to delete (e.g., 5 or 'a1b2c3d4').
#         :param db: The asynchronous SQLAlchemy session.
#         :param user_id: The ID of the user performing the operation (for logging/auditing).
#         :param id_column: The name of the column to use as the search key (e.g., 'id', 'uuid', 'name').
#         :returns: None, as the successful response for deletion is typically 204 No Content.
#         :raises HTTPException: If a SQLAlchemy error occurs during the deletion process.
#         """
#         try:
#             # 1. Obtener la columna dinámica
#             id_attribute = getattr(self.db_model, id_column)
            
#             # 2. Construir la sentencia DELETE
#             stmt = delete(self.db_model).where(id_attribute == item_id)
            
#             # 3. Ejecutar la sentencia DELETE
#             result = await db.execute(stmt)
            
#             # 4. Confirmar la transacción
#             await db.commit()
            
#             # Opcional: Si necesitas loguear el ID del item eliminado:
#             if user_id:
#                 await self._log_action(db, user_id, self.db_model.__name__, DELETE_OPERATION)
                
#         except SQLAlchemyError as e:
#             await db.rollback()
#             print(f"Error en delete_by_id (Query): {e}")
#             raise HTTPException(status_code=500, detail="Error de DB al ejecutar la eliminación.")
            
#         return None # Para el 204 No Content
    
#     async def get_by_filters(self, db: AsyncSession, filters: List[Any], user_id: str = None, 
#                              skip: int = 0, limit: int = 100) -> List[Base]:
#         """
#         Retrieve records by a list of SQLAlchemy filter criteria.
#         """
#         try:
#             # 1. Construir el SELECT
#             stmt = select(self.db_model).where(and_(*filters))
#             # 2. Aplicar paginación
#             stmt = stmt.offset(skip).limit(limit)
#             # 3. Ejecutar y obtener resultados
#             result = await db.execute(stmt)
            
#             if user_id:
#                 # Opcional: Loguear la acción
#                 await self._log_action(db, user_id, self.db_model.__name__, GET_BY_FILTERS)
                
#             return result.scalars().all()
#         except SQLAlchemyError as e:
#             print(f"Error en get_by_filters for {self.db_model}: {e}")
#             raise HTTPException(status_code=500, detail="Error al obtener registros con filtro")
        
# class UserRepository(BaseRepository):
#     async def create(self, db: AsyncSession, item_data: dict, user_id: str = None) -> Base:
#         # lógica personalizada para User antes o después
#         # Ejemplo: hash de contraseña, validaciones extra
#         user = await db.scalar(select(User).where(User.email == item_data['email']))
#         if user is not None:
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail=api_messages.EMAIL_ADDRESS_ALREADY_USED,
#             )
#         user = User(
#             email=item_data['email'],
#             hashed_password=get_password_hash(item_data['password']),
#         )
#         # Crear un diccionario solo con los atributos necesarios
#         user_data = {
#             'email': user.email,
#             'hashed_password': user.hashed_password,
#         }
#         return await super().create(db, user_data, user_id)

# # Esta clase hereda TODA la funcionalidad CRUD de BaseRepository
# # y está tipada genéricamente para saber que maneja objetos 'Bitacora'.
# class BitacoraRepository(BaseRepository):
#     """
#     Repositorio específico para la entidad Bitacora. 
#     Aquí se añadirán métodos personalizados de consulta si son necesarios.
#     Convención estándar en patrones de diseño para dejar un punto donde se pueda añadir lógica específica más adelante.
#     (ej., get_bitcora_by_user).
#     """
#     pass 