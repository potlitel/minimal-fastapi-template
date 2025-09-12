# crud_utils.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Type, Any, TypeVar
from pydantic import BaseModel
from app.core.cqrs.commands_queries import CreateItemCommand, DeleteItemCommand, GetItemByIdQuery, GetItemsQuery, UpdateItemCommand
from app.core.cqrs.handlers import CreateItemHandler, DeleteItemHandler, GetItemHandler, GetItemsHandler, UpdateItemHandler
# from app.core.cqrs.mediator import get_mediator
from app.core.cqrs.mediator import mediator  # Import the instance directly
from app.core.repositories import BaseRepository
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.models import Base, User
from app.schemas.requests import BaseRequest

# Definimos un tipo genérico T que debe ser una subclase de Base
T = TypeVar('T', bound=Base)

def crud_router_factory(
    repository: BaseRepository,
    modelResponse: Type[Base],
    modelRequest: Type[BaseRequest],
    model_name: str
):
    router = APIRouter(prefix=f"/{model_name.lower()}", tags=[model_name])
    
    # Se registran los handlers para este router específico
    mediator.register_handler(CreateItemCommand, CreateItemHandler(repository))
    mediator.register_handler(GetItemsQuery, GetItemsHandler(repository))
    mediator.register_handler(GetItemByIdQuery, GetItemHandler(repository))
    mediator.register_handler(UpdateItemCommand, UpdateItemHandler(repository))
    mediator.register_handler(DeleteItemCommand, DeleteItemHandler(repository))
    
    @router.get("/", response_model=List[modelResponse], 
                     summary=f"Retrieve all {model_name} items", 
                     description=f"📚Fetch a list of all {model_name} records from the database.")
    async def read_all(db: AsyncSession = Depends(deps.get_session), 
                       _current_user: User = Depends(deps.get_current_user)
                       ):
        """
        Retrieve all items of type {model_name}.

        - **Returns**: List of {model_name} objects.
        """
        # return await repository.get_all(db)
        query = GetItemsQuery()
        return await mediator.send(query, db)
    
    @router.get("/{item_id}", response_model=modelResponse, 
                summary=f"Retrieve a single {model_name} by ID",
                description=f"🎯Get a {model_name} object by its unique identifier.")
    async def read_one(item_id: str, 
                       db: AsyncSession = Depends(deps.get_session), 
                       _current_user: User = Depends(deps.get_current_user)):
        """
        Retrieve one {model_name} by its ID.

        - **param item_id**: ID of the {model_name} to retrieve.
        - **Returns**: A single {model_name} object.
        - **Raises**: 404 if the {model_name} does not exist.
        """
        # item = await repository.get_by_id(item_id, db)
        # if not item:
        #     raise HTTPException(status_code=404, detail=f"{model_name} not found")
        # return item
        query = GetItemByIdQuery(item_id=item_id)
        return await mediator.send(query, db)
    
    @router.post("/", response_model=modelResponse, 
                      status_code=201,
                      response_model_exclude={"password"},
                      summary=f"Create a new {model_name}",
                      description=f"➕Add a new {model_name} to the database.")
    async def create_one(item: modelRequest, 
                         db: AsyncSession = Depends(deps.get_session), 
                         _current_user: User = Depends(deps.get_current_user)):
        """
        Create a new {model_name} record.

        - **param item**: A {model_name} object to create.
        - **Returns**: The created {model_name} with its assigned ID.
        """
        # return await repository.create(db, item.dict())
        command = CreateItemCommand(item_data=item.dict())
        return await mediator.send(command, db)

    @router.put("/{item_id}", response_model=modelResponse,
                summary=f"Update an existing {model_name}",
                description=f"✏️Modify the {model_name} identified by the given ID.")
    async def update_one(item_id: int, 
                         item: modelResponse, 
                         db: AsyncSession = Depends(deps.get_session), 
                         _current_user: User = Depends(deps.get_current_user)):
        """
        Update an existing {model_name} by ID.

        - **param item_id**: ID of the {model_name} to update.
        - **param item**: Partial or full data to update.
        - **Returns**: The updated {model_name} object.
        - **Raises**: 404 if the {model_name} does not exist.
        """
        db_item = await repository.get_by_id(item_id, db)
        if not db_item:
            raise HTTPException(status_code=404, detail=f"{model_name} not found")
        return await repository.update(db, db_item, item.dict(exclude_unset=True))
        # command = UpdateItemCommand(item_id=item_id, item_data=item.dict(exclude_unset=True))
        # return await mediator.send(command, db)

    @router.delete("/{item_id}", status_code=204,
                   summary=f"Delete a {model_name} by ID",
                   description=f"❌Remove the {model_name} specified by the unique ID from the database.")
    async def delete_one(item_id: str, 
                         db: AsyncSession = Depends(deps.get_session), 
                         _current_user: User = Depends(deps.get_current_user)):
        """
        Delete a {model_name} record by ID.

        - **param item_id**: ID of the {model_name} to delete.
        - **Raises**: 404 if the {model_name} does not exist.
        - **Returns**: HTTP 204 No Content on success.
        """
        # db_item = await repository.get_by_id(item_id, db)
        # if not db_item:
        #     raise HTTPException(status_code=404, detail=f"{model_name} not found")
        # await repository.delete(db, db_item)
        # return {"message": f"{model_name} deleted successfully"}
        command = DeleteItemCommand(item_id=item_id)
        return await mediator.send(command, db)
        
    return router