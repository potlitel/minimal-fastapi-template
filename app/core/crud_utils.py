# crud_utils.py
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional, Type, Any, TypeVar
from pydantic import BaseModel
from app.core.constants import ALL_OPERATIONS
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
    model_name: str,
    operations: Optional[List[str]] = None,
    secure_operations: Optional[List[str]] = None
):
    router = APIRouter(prefix=f"/{model_name.lower()}", tags=[model_name])
    
    # 1. Definir las operaciones principales por defecto
    if operations is None:
        operations = ALL_OPERATIONS
        
    # 2. Definir las operaciones seguras.
    #    Si no se especifican, se asume que todas las operaciones principales
    #    requieren seguridad. La clave es inicializarla a una lista vacía si es None,
    #    para evitar el TypeError.
    if secure_operations is None:
        secure_operations = operations
        
    # 3. Validar y crear las rutas
    invalid_secure_ops = [op for op in secure_operations if op not in operations]
    if invalid_secure_ops:
        raise ValueError(
            f"Las siguientes operaciones en 'secure_operations' "
            f"no están incluidas en 'operations': {invalid_secure_ops}. "
            "Las operaciones seguras deben ser un subconjunto de las operaciones principales."
        )

    # Registrar handlers según las operaciones solicitadas
    if "create" in operations:
        mediator.register_handler(CreateItemCommand, CreateItemHandler(repository))
    if "get_all" in operations:
        mediator.register_handler(GetItemsQuery, GetItemsHandler(repository))
    if "get_one" in operations:
        mediator.register_handler(GetItemByIdQuery, GetItemHandler(repository))
    if "update" in operations:
        mediator.register_handler(UpdateItemCommand, UpdateItemHandler(repository))
    if "delete" in operations:
        mediator.register_handler(DeleteItemCommand, DeleteItemHandler(repository))

    # ---
    
    # Crear las rutas según las operaciones
    if "get_all" in operations:
        # Aquí verificamos si la operación está en la lista de operaciones seguras
        is_secure = "get_all" in secure_operations
        @router.get("/", response_model=List[modelResponse], 
                     summary=f"Retrieve all {model_name} items", 
                     description=f"📚Fetch a list of all {model_name} records from the database.")
        async def read_all(db: AsyncSession = Depends(deps.get_session), 
                            # Inyectamos el usuario de forma condicional
                            current_user: Optional[User] = Depends(deps.get_current_user) if is_secure else None):
            """
            Retrieve all items of type {model_name}.

            - **Returns**: List of {model_name} objects.
            """
            # Lógica para manejar el user_id
            user_id = current_user.user_id if current_user else None
            query = GetItemsQuery(user_id=user_id)
            return await mediator.send(query, db)
    
    if "get_one" in operations:
        # Aquí verificamos si la operación está en la lista de operaciones seguras
        is_secure = "get_one" in secure_operations
        @router.get("/{item_id}", response_model=modelResponse, 
                    summary=f"Retrieve a single {model_name} by ID",
                    description=f"🎯Get a {model_name} object by its unique identifier.")
        async def read_one(item_id: str, 
                           db: AsyncSession = Depends(deps.get_session), 
                           # Inyectamos el usuario de forma condicional
                           current_user: Optional[User] = Depends(deps.get_current_user) if is_secure else None):
            """
            Retrieve one {model_name} by its ID.

            - **param item_id**: ID of the {model_name} to retrieve.
            - **Returns**: A single {model_name} object.
            - **Raises**: 404 if the {model_name} does not exist.
            """
            # Tu lógica para manejar el user_id
            user_id = current_user.user_id if current_user else None
            query = GetItemByIdQuery(item_id=item_id, user_id=user_id)
            return await mediator.send(query, db)
    
    if "create" in operations:
        # Aquí verificamos si la operación está en la lista de operaciones seguras
        is_secure = "create" in secure_operations
        @router.post("/", response_model=modelResponse, 
                      status_code=201,
                      response_model_exclude={"password"},
                      summary=f"Create a new {model_name}",
                      description=f"➕Add a new {model_name} to the database.")
        async def create_one(item: modelRequest, 
                             db: AsyncSession = Depends(deps.get_session), 
                             # Inyectamos el usuario de forma condicional
                             current_user: Optional[User] = Depends(deps.get_current_user) if is_secure else None):
            """
            Create a new {model_name} record.

            - **param item**: A {model_name} object to create.
            - **Returns**: The created {model_name} with its assigned ID.
            """
            # Lógica para manejar el user_id
            user_id = current_user.user_id if current_user else None
            command = CreateItemCommand(item_data=item.dict(), user_id=user_id)
            return await mediator.send(command, db)

    if "update" in operations:
        # Aquí verificamos si la operación está en la lista de operaciones seguras
        is_secure = "update" in secure_operations
        @router.put("/{item_id}", response_model=modelResponse,
                    summary=f"Update an existing {model_name}",
                    description=f"✏️Modify the {model_name} identified by the given ID.")
        async def update_one(item_id: int, 
                             item: modelResponse, 
                             db: AsyncSession = Depends(deps.get_session), 
                             # Inyectamos el usuario de forma condicional
                             current_user: Optional[User] = Depends(deps.get_current_user) if is_secure else None):
            """
            Update an existing {model_name} by ID.

            - **param item_id**: ID of the {model_name} to update.
            - **param item**: Partial or full data to update.
            - **Returns**: The updated {model_name} object.
            - **Raises**: 404 if the {model_name} does not exist.
            """
            # Tu lógica para manejar el user_id
            user_id = current_user.user_id if current_user else None
            db_item = await repository.get_by_id(item_id, db, user_id=user_id)
            if not db_item:
                raise HTTPException(status_code=404, detail=f"{model_name} not found")
            return await repository.update(db, db_item, item.dict(exclude_unset=True), user_id=user_id)

    if "delete" in operations:
        # Aquí verificamos si la operación está en la lista de operaciones seguras
        is_secure = "delete" in secure_operations
        @router.delete("/{item_id}", status_code=204,
                       summary=f"Delete a {model_name} by ID",
                       description=f"❌Remove the {model_name} specified by the unique ID from the database.")
        async def delete_one(item_id: str, 
                             db: AsyncSession = Depends(deps.get_session), 
                             # Inyectamos el usuario de forma condicional
                             current_user: Optional[User] = Depends(deps.get_current_user) if is_secure else None):
            """
            Delete a {model_name} record by ID.

            - **param item_id**: ID of the {model_name} to delete.
            - **Raises**: 404 if the {model_name} does not exist.
            - **Returns**: HTTP 204 No Content on success.
            """
            # Lógica para manejar el user_id
            user_id = current_user.user_id if current_user else None
            command = DeleteItemCommand(item_id=item_id, user_id=user_id)
            return await mediator.send(command, db)
            
    return router