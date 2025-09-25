# handlers.py
# from repositories import BaseRepository
from app.core.repositories import BaseRepository
from app.core.cqrs.commands_queries import *
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

class GetItemsHandler:
    def __init__(self, repository: BaseRepository):
        # Initialize the handler with a repository instance for data access
        self.repository = repository
        
    async def handle(self, query: GetItemsQuery, db: AsyncSession):
        # Handle the request to get all items from the repository
        # return await self.repository.get_all(db)
        # Ahora pasas el user_id del query al repositorio
        return await self.repository.get_all(db, user_id=query.user_id)

class GetItemHandler:
    def __init__(self, repository: BaseRepository):
        # Initialize the handler with a repository instance for data access
        self.repository = repository
        
    async def handle(self, query: GetItemByIdQuery, db: AsyncSession):
        # Handle the request to get a single item by its ID
        item = await self.repository.get_by_id(query.item_id, db, user_id=query.user_id)
        # item = await self.repository.get_by_id(query.item_id, db)
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
        # return await self.repository.create(db, command.item_data)
        return await self.repository.create(db, command.item_data, user_id=command.user_id)
        
class UpdateItemHandler:
    def __init__(self, repository: BaseRepository):
        # Initialize the handler with a repository instance for data access
        self.repository = repository
        
    async def handle(self, command: UpdateItemCommand, db: AsyncSession):
        # Handle the request to update an existing item
        # db_item = await self.repository.get_by_id(command.item_id, db)
        db_item = await self.repository.get_by_id(command.item_id, db, user_id=command.user_id)
        if not db_item:
            # Raise a 404 error if the item to update is not found
            raise HTTPException(status_code=404, detail="Item not found")
        # Update the item in the repository and return the updated item
        # return await self.repository.update(db, db_item, command.item_data)
        return await self.repository.update(db, db_item, command.item_data, user_id=command.user_id)

class DeleteItemHandler:
    def __init__(self, repository: BaseRepository):
        # Initialize the handler with a repository instance for data access
        self.repository = repository
        
    async def handle(self, command: DeleteItemCommand, db: AsyncSession):
        # Handle the request to delete an item by its ID
        # db_item = await self.repository.get_by_id(command.item_id, db)
        db_item = await self.repository.get_by_id(command.item_id, db, user_id=command.user_id)
        if not db_item:
            # Raise a 404 error if the item to delete is not found
            raise HTTPException(status_code=404, detail="Item not found")
        # Delete the item from the repository
        # await self.repository.delete(db, db_item)
        await self.repository.delete(db, db_item, user_id=command.user_id)
        return {"message": "Item deleted successfully"}
