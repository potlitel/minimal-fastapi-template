# handlers.py
# from repositories import BaseRepository
from app.core.repositories import BaseRepository
from app.core.cqrs.commands_queries import *
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException

# class CreateItemHandler:
#     def __init__(self, repository: BaseRepository):
#         self.repository = repository

#     def handle(self, command: CreateItemCommand, db: Session):
#         return self.repository.create(db, {"name": command.name})

# class GetItemHandler:
#     def __init__(self, repository: BaseRepository):
#         self.repository = repository

#     def handle(self, query: GetItemQuery, db: Session):
#         return self.repository.get_by_id(db, query.item_id)

# class UpdateItemHandler:
#     def __init__(self, repository: BaseRepository):
#         self.repository = repository

#     def handle(self, command: UpdateItemCommand, db: Session):
#         item = self.repository.get_by_id(db, command.item_id)
#         if not item:
#             return None
#         return self.repository.update(db, item, command.dict(exclude_unset=True))
        
# class DeleteItemHandler:
#     def __init__(self, repository: BaseRepository):
#         self.repository = repository

#     def handle(self, command: DeleteItemCommand, db: Session):
#         item = self.repository.get_by_id(db, command.item_id)
#         if not item:
#             return None
#         return self.repository.delete(db, item)

class GetItemsHandler:
    def __init__(self, repository: BaseRepository):
        self.repository = repository
        
    async def handle(self, query: GetItemsQuery, db: AsyncSession):
        return await self.repository.get_all(db)

class GetItemHandler:
    def __init__(self, repository: BaseRepository):
        self.repository = repository
        
    async def handle(self, query: GetItemByIdQuery, db: AsyncSession):
        item = await self.repository.get_by_id(query.item_id, db)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return item
        
class CreateItemHandler:
    def __init__(self, repository: BaseRepository):
        self.repository = repository
        
    async def handle(self, command: CreateItemCommand, db: AsyncSession):
        return await self.repository.create(db, command.item_data)
        
class UpdateItemHandler:
    def __init__(self, repository: BaseRepository):
        self.repository = repository
        
    async def handle(self, command: UpdateItemCommand, db: AsyncSession):
        db_item = await self.repository.get_by_id(command.item_id, db)
        if not db_item:
            raise HTTPException(status_code=404, detail="Item not found")
        return await self.repository.update(db, db_item, command.item_data)

class DeleteItemHandler:
    def __init__(self, repository: BaseRepository):
        self.repository = repository
        
    async def handle(self, command: DeleteItemCommand, db: AsyncSession):
        db_item = await self.repository.get_by_id(command.item_id, db)
        if not db_item:
            raise HTTPException(status_code=404, detail="Item not found")
        await self.repository.delete(db, db_item)
        return {"message": "Item deleted successfully"}