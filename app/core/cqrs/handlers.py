# handlers.py
# from repositories import BaseRepository
import math
from typing import List
from app.core.repositories.base import BaseRepository
from app.core.cqrs.commands_queries import *
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

class GetItemsHandler:
    def __init__(self, repository: BaseRepository):
        # Initialize the handler with a repository instance for data access
        self.repository = repository
        
    async def handle(self, query: GetItemsQuery, db: AsyncSession):
        """
        Maneja la query para obtener ítems y encapsular el resultado en PagedResult.
        """
        # return await self.repository.get_all(db, 
        #                                      skip=query.skip,    
        #                                      limit=query.limit,
        #                                      user_id=query.user_id)
        # El repositorio retorna la lista de ítems y el conteo total
        items: List[Any]
        total_count: int
        
        items, total_count = await self.repository.get_all(
            db, 
            skip=query.skip,    
            limit=query.limit,
            user_id=query.user_id
        )
        
        # --- Lógica de cálculo de Paginación ---
        limit = query.limit # Puede ser 0 si limit no fue pasado, manejar esto.
        skip = query.skip
        
        # Prevenir división por cero si limit es 0 o negativo, usar un valor seguro.
        effective_limit = limit if limit > 0 else 10

        # pageNumber y totalPages
        total_pages = math.ceil(total_count / effective_limit) if total_count > 0 else 0
        
        # pageNumber es (skip / limit) + 1. Usar max(1, ...) para que no sea 0 si skip=0
        page_number = max(1, (skip // effective_limit) + 1)
        
        # hasPreviousPage y hasNextPage
        has_previous_page = page_number > 1
        has_next_page = page_number < total_pages

        # Crear y devolver la instancia de PagedResult. 
        # Tenga en cuenta que el tipo genérico Pydantic lo resolverá el endpoint.
        # Por ahora, devolvemos un diccionario o un BaseModel no genérico
        return {
            "items": items,
            "pageNumber": page_number,
            "pageSize": effective_limit,
            "totalPages": total_pages,
            "totalCount": total_count,
            "hasPreviousPage": has_previous_page,
            "hasNextPage": has_next_page,
        }

class GetItemHandler:
    def __init__(self, repository: BaseRepository):
        # Initialize the handler with a repository instance for data access
        self.repository = repository
        
    async def handle(self, query: GetItemByIdQuery, db: AsyncSession):
        # Handle the request to get a single item by its ID
        item = await self.repository.get_by_id(
            query.item_id, 
            db, 
            user_id=query.user_id,
            # Añadimos el argumento que se generó dinámicamente en la Query
            id_column=query.id_column_name 
        )
        if not item:
            # Raise a 404 error if the item is not found
            raise HTTPException(status_code=404, detail="Item not found")
        return item
        
class CreateItemHandler:
    def __init__(self, repository: BaseRepository):
        # Initialize the handler with a repository instance for data access
        self.repository = repository
        
    async def handle(self, command: CreateItemCommand, db: AsyncSession):
        # Handle the request to create a new item in the repository
        return await self.repository.create(db, command.item_data, user_id=command.user_id)
        
class UpdateItemHandler:
    def __init__(self, repository: BaseRepository):
        # Initialize the handler with a repository instance for data access
        self.repository = repository
        
    async def handle(self, command: UpdateItemCommand, db: AsyncSession):
        # Handle the request to update an existing item
        db_item = await self.repository.get_by_id(
            command.item_id, 
            db, 
            user_id=command.user_id,
            id_column=command.id_column_name
        )
        if not db_item:
            # Raise a 404 error if the item to update is not found
            raise HTTPException(status_code=404, detail="Item not found")
        # Update the item in the repository and return the updated item
        return await self.repository.update(db, db_item, command.item_data, user_id=command.user_id)

class DeleteItemHandler:
    def __init__(self, repository: BaseRepository):
        # Initialize the handler with a repository instance for data access
        self.repository = repository
        
    async def handle(self, command: DeleteItemCommand, db: AsyncSession):
        # Handle the request to delete an item by its ID
        db_item = await self.repository.get_by_id(
            command.item_id, 
            db, 
            user_id=command.user_id,
            id_column=command.id_column_name
        )
        if not db_item:
            # Raise a 404 error if the item to delete is not found
            raise HTTPException(status_code=404, detail="Item not found")
        # Delete the item from the repository
        await self.repository.delete_by_id(
            command.item_id, 
            db, 
            user_id=command.user_id, 
            id_column=command.id_column_name
        )
        return {"message": "Item deleted successfully"}
    

