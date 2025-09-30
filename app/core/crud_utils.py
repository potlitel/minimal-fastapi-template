# crud_utils.py
CURRENT_MODULE = __name__
from fastapi import APIRouter, HTTPException, Depends
from typing import Callable, List, Optional, Type, Any, TypeVar
from pydantic import BaseModel, Field # Necesaria si IRequest hereda de un BaseModel
from app.core.constants import ALL_OPERATIONS, CREATE_OPERATION, DELETE_OPERATION, GET_ALL_OPERATION, GET_ONE_OPERATION, UPDATE_OPERATION
from app.core.cqrs.commands_queries import CreateItemCommand, DeleteItemCommand, GetItemByIdQuery, GetItemsQuery, UpdateItemCommand
from app.core.cqrs.handlers import CreateItemHandler, DeleteItemHandler, GetItemHandler, GetItemsHandler, UpdateItemHandler
# from app.core.cqrs.mediator import get_mediator
from app.core.cqrs.mediator import mediator  # Import the instance directly
from app.core.repositories import BaseRepository
from sqlalchemy.ext.asyncio import AsyncSession
from app.api import deps
from app.models import Base, User
from app.schemas.requests import BaseRequest

# --- Definiciones Mínimas Requeridas ---

class IRequest(BaseModel):
    """
    Clase base para Queries y Commands, debe heredar de BaseModel 
    para manejar los campos (db, user_id, y los dinámicos).
    """
    db: Any # Para AsyncSession o el tipo de tu sesión de DB
    user_id: Optional[str] = None
    # Campos base para operaciones unitarias (GET_ONE, UPDATE, DELETE):
    # Los hacemos opcionales para que GET_ALL y CREATE no fallen su validación.
    item_id: Optional[Any] = Field(default=None)         # ID del registro a buscar
    id_column_name: str = Field(default="id")           # Columna a usar para la búsqueda
    
# --- Tipos Genéricos y Constantes ---
T = TypeVar('T', bound=Base)
TRepository = TypeVar('TRepository', bound=BaseRepository)
ModelResponse = TypeVar("ModelResponse")
ModelRequest = TypeVar("ModelRequest")

def crud_router_factory(
    repository: TRepository,
    modelResponse: Type[ModelResponse],
    modelRequest: Type[ModelRequest] | None,
    model_name: str,
    id_column_name: str = "id",
    id_type: Type = str,
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

    # -------------------------------------------------------
    # FUNCIONALIDAD CLAVE: GENERACIÓN Y REGISTRO DINÁMICO
    # -------------------------------------------------------

    def create_and_register_handler(op_name: str, base_fields: dict, handler_logic: Callable):
        """Genera y registra las clases Request/Command y Handler únicas."""
        
        # 1. Crear el Request/Command ÚNICO (e.g., GetUsersAllQuery)
        request_type_name = f"{op_name.capitalize()}{model_name}Request"
        
        # --- CAMBIO CLAVE AQUÍ: Crear el namespace dinámico ---
    
        dynamic_annotations = base_fields.copy() # {'item_id': str}
        
        # Inicializa el diccionario de la clase (el namespace)
        dynamic_namespace = {
            '__module__': CURRENT_MODULE,
            '__annotations__': dynamic_annotations # <--- Pydantic lee los campos desde aquí
        }
        
        
        # IRequest debe ser la base (e.g., IRequest(BaseRequest) con campos db y user_id)
        UniqueRequest = type(request_type_name, (IRequest,), dynamic_namespace)
        
        # 2. Crear el Handler ÚNICO (e.g., GetUsersAllHandler)
        handler_type_name = f"{op_name.capitalize()}{model_name}Handler"
        
        # Definición del método handle para la clase Handler
        def handle_method(self, request: UniqueRequest, db: 'AsyncSession'):
            # Llama a la lógica específica, usando el repositorio inyectado
            return handler_logic(self.repository, request, db)
            
        # Creación de la clase Handler ÚNICA
        UniqueHandler = type(handler_type_name, (object,), {
            # Inyección de dependencia del repositorio
            "__init__": lambda self, repository: setattr(self, 'repository', repository), 
            "handle": handle_method,
            "handles": UniqueRequest
        })

        # 3. Registro en MediatR
        # MediatR mapea UniqueRequest -> Instancia Única de UniqueHandler
        mediator.register_handler(UniqueRequest, UniqueHandler(repository))
        return UniqueRequest 

    # ---
    
    # -------------------------------------------------------
    # DEFINICIÓN DE LÓGICA Y RUTAS PARA CADA OPERACIÓN
    # -------------------------------------------------------

    # --- GET ALL ---
    
    # Crear las rutas según las operaciones
    if GET_ALL_OPERATION in operations:
        def logic_get_all(repo, req, db):
            return repo.get_all(db, user_id=req.user_id)
        
        QueryAll = create_and_register_handler("getall", {}, logic_get_all)
        
        # Aquí verificamos si la operación está en la lista de operaciones seguras
        is_secure = GET_ALL_OPERATION in secure_operations
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
            # query = GetItemsQuery(user_id=user_id)
            query = QueryAll(db=db, user_id=user_id)
            return await mediator.send(query, db)
    
    if GET_ONE_OPERATION in operations:
        async def logic_get_one(repo, req, db):
            return await repo.get_by_id(req.item_id, db, user_id=req.user_id, id_column=req.id_column_name) 
        QueryOne = create_and_register_handler("getonebyid", {}, logic_get_one)
        
        # Aquí verificamos si la operación está en la lista de operaciones seguras
        is_secure = GET_ONE_OPERATION in secure_operations
        @router.get("/{item_id}", response_model=modelResponse, 
                    summary=f"Retrieve a single {model_name} by ID",
                    description=f"🎯Get a {model_name} object by its unique identifier.")
        async def read_one(item_id: id_type, 
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
            #query = GetItemByIdQuery(item_id=item_id, user_id=user_id)
            query = QueryOne(item_id=item_id, db=db, user_id=user_id,id_column_name=id_column_name) 
            return await mediator.send(query, db)
    
    if CREATE_OPERATION in operations:
        def logic_create(repo, req, db):
            return repo.create(db, item_data=req.item_data, user_id=req.user_id)
        CommandCreate = create_and_register_handler("create", {"item_data": dict}, logic_create)
        # Aquí verificamos si la operación está en la lista de operaciones seguras
        is_secure = CREATE_OPERATION in secure_operations
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
            # # command = CreateItemCommand(item_data=item.dict(), user_id=user_id)
            command = CommandCreate(item_data=item.model_dump(), db=db, user_id=user_id)
            return await mediator.send(command, db)

    if UPDATE_OPERATION in operations:
        async def logic_update(repo, req, db):
            # 1. BÚSQUEDA Y VALIDACIÓN (la verificación de existencia)
            # Lógica más compleja: obtener, validar y actualizar (como en tu original, pero encapsulado)
            db_item = await repo.get_by_id(req.item_id, db, user_id=req.user_id, id_column=id_column_name)
            if not db_item:
                # El handler es responsable de lanzar la excepción
                raise HTTPException(status_code=404, detail=f"{model_name} not found")
            # 2. ACTUALIZACIÓN (llama a tu método 'update' con el objeto validado)
            return repo.update(db, db_item, req.item_data, user_id=req.user_id)
            
        CommandUpdate = create_and_register_handler("update", {"item_data": dict}, logic_update)
        # Aquí verificamos si la operación está en la lista de operaciones seguras
        is_secure = UPDATE_OPERATION in secure_operations
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
             # Usamos item.model_dump(exclude_unset=True) para actualizaciones parciales
            command = CommandUpdate(item_id=item_id, item_data=item.model_dump(exclude_unset=True), db=db, user_id=user_id, id_column_name=id_column_name)
            return await mediator.send(command, db)

    if DELETE_OPERATION in operations:
        async def logic_delete(repo, req, db):
            # 🎯 Ejemplo de printf con logging (usando f-string)
            # 1. BÚSQUEDA Y VALIDACIÓN (la verificación de existencia)
            # Lógica más compleja: obtener, validar y actualizar (como en tu original, pero encapsulado)
            db_item = await repo.get_by_id(req.item_id, db, user_id=req.user_id, id_column=req.id_column_name)
            if not db_item:
                # El handler es responsable de lanzar la excepción
                raise HTTPException(status_code=404, detail=f"{model_name} not found")
            # return repo.delete(req.item_id, db, user_id=req.user_id) (ANTES)
            # 2. ELIMINACIÓN (Llamar a un método simple que acepta el objeto)
            # Esto requiere que repo.delete acepte el objeto, NO el ID.
            # return repo.delete_by_object(db, db_item, user_id=req.user_id) # 👈 CAMBIAR FIRMA
            # Cambiamos la llamada para usar el ID y la columna
            return await repo.delete_by_id(
                req.item_id, 
                db, 
                user_id=req.user_id, 
                id_column=req.id_column_name
            )


        CommandDelete = create_and_register_handler("delete", {}, logic_delete)
        # Aquí verificamos si la operación está en la lista de operaciones seguras
        is_secure = DELETE_OPERATION in secure_operations
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
            command = CommandDelete(item_id=item_id, db=db, user_id=user_id,id_column_name=id_column_name)
            await mediator.send(command, db)
            return # <--- Aquí el router retorna un HTTP 204 sin contenido
            
    return router