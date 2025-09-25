# repositories.py
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import api_messages, deps
from typing import Type

from app.core.security.password import get_password_hash
from app.models import Base, Bitacora, User

class BaseRepository:
    def __init__(self, db_model: Base):
        """
        Initialize the repository with a specific SQLAlchemy ORM model.

        - **param db_model**: The ORM model class representing a database table.
        """
        self.db_model = db_model
        
    async def _log_action(self, db: AsyncSession, user_id: str, entity: str, action: str):
        log_entry = Bitacora(user_id=user_id, entity=entity, action=action)
        db.add(log_entry)
        await db.commit()

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 10, user_id: str = None):
        """
        Retrieve a list of all records for the model, with pagination.

        - **param db**: Database session for async operations.
        - **param skip**: Number of records to skip (offset).
        - **param limit**: Maximum number of records to return.
        - **returns**: List of model instances.
        - **raises**: 500 HTTPException if database query fails.
        """
        try:
            print(f"La consulta get_all se está ejecutando para el modelo: {self.db_model.__name__}")
            result = await db.execute(select(self.db_model).offset(skip).limit(limit))
            if user_id:
                await self._log_action(db, user_id, self.db_model.__name__, 'READ_ALL')
            return result.scalars().all()
        except SQLAlchemyError as e:
            # Logging o print del error
            print(f"Error en get_all for {self.db_model} entity: {e}")
            raise HTTPException(status_code=500, detail="Error al obtener todos los registros")

    async def get_by_id(self, item_id: str, db: AsyncSession, user_id: str = None):
        """
        Retrieve a single record by its unique identifier.

        - **param item_id**: ID of the record to fetch.
        - **param db**: Database session.
        - **returns**: Single model instance or None.
        - **raises**: 500 HTTPException if retrieval query fails.
        """
        try:
            result = await db.execute(select(self.db_model).filter(self.db_model.user_id == item_id))
            if user_id:
                await self._log_action(db, user_id, self.db_model.__name__, 'READ')
            return result.scalars().first()
        except SQLAlchemyError as e:
            print(f"Error en get_by_id for {self.db_model} entity: {e}")
            raise HTTPException(status_code=500, detail=f"Error en get_by_id for {self.db_model} entity")

    async def create(self, db: AsyncSession, item_data: dict, user_id: str = None) -> Base:
        """
        Create a new record in the database.

        - **param db**: Database session.
        - **param item_data**: Dictionary of data for new record.
        - **returns**: Created model instance.
        - **raises**: 400 HTTPException if there is a database integrity error 
          (e.g., duplicate email).
        """
        db_item = self.db_model(**item_data)
        db.add(db_item)
        try:
            await db.commit()
            await db.refresh(db_item)
            if user_id:
                await self._log_action(db, user_id, self.db_model.__name__, 'CREATE')
        except IntegrityError:  # pragma: no cover
            await db.rollback()

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=api_messages.EMAIL_ADDRESS_ALREADY_USED,
            )
        return db_item

    async def update(self, db: AsyncSession, db_item, item_data: dict, user_id: str = None) -> Base:
        """
        Update an existing record with new data.

        - **param db**: Database session.
        - **param db_item**: Existing instance to update.
        - **param item_data**: Dictionary of fields to modify.
        - **returns**: Updated model instance.
        """
        try:
            for key, value in item_data.items():
                setattr(db_item, key, value)
            await db.commit()
            await db.refresh(db_item)
            if user_id:
                await self._log_action(db, user_id, self.db_model.__name__, 'UPDATE')
        except SQLAlchemyError as e:
            await db.rollback()
            print(f"Error en update for {self.db_model} entity: {e}")
            raise HTTPException(status_code=500, detail="Error al actualizar el registro")
        return db_item

    async def delete(self, db: AsyncSession, db_item, user_id: str = None):
        """
        Delete a record from the database.

        - **param db**: Database session.
        - **param db_item**: Instance to delete.
        - **returns**: Confirmation message.
        """
        try:
            await db.delete(db_item)
            await db.commit()
            if user_id:
                await self._log_action(db, user_id, self.db_model.__name__, 'DELETE')
        except SQLAlchemyError as e:
            await db.rollback()
            print(f"Error en delete for {self.db_model} entity: {e}")
            raise HTTPException(status_code=500, detail="Error al eliminar el registro")
        # return {"message": "Item deleted successfully"}
        return db_item
    
    
class UserRepository(BaseRepository):
    async def create(self, db: AsyncSession, item_data: dict, user_id: str = None) -> Base:
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
