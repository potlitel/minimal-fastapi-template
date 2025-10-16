# crud_utils.py
CURRENT_MODULE = __name__
from fastapi import APIRouter, HTTPException, Depends, logger
from typing import Callable, Dict, List, Optional, Type, Any, TypeVar
from pydantic import BaseModel, ConfigDict, Field # Necesaria si IRequest hereda de un BaseModel
from app.core.constants import ALL_OPERATIONS, CREATE_OPERATION, DELETE_OPERATION, GET_ALL_OPERATION, GET_COUNT_OPERATION, GET_ONE_OPERATION, UPDATE_OPERATION
from app.core.cqrs.commands_queries import CreateItemCommand, DeleteItemCommand, GetItemByIdQuery, GetItemsQuery, UpdateItemCommand
from app.core.cqrs.handlers import CreateItemHandler, DeleteItemHandler, GetItemHandler, GetItemsHandler, UpdateItemHandler, CountItemsHandler
# from app.core.cqrs.mediator import get_mediator
from app.core.cqrs.mediator import mediator  # Import the instance directly
from app.core.events.producers.kafka_producer import KafkaProducerService
from app.core.pagedResult.types import PagedResult
from app.core.repositories.base import BaseRepository
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
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
# --- Tipos Genéricos y Constantes ---
T = TypeVar('T', bound=Base)
TRepository = TypeVar('TRepository', bound=BaseRepository)
ModelResponse = TypeVar("ModelResponse")
ModelRequest = TypeVar("ModelRequest")

# --- Constantes para simplificar el código ---
# Mapeo del nombre de la operación al Handler existente
HANDLER_MAP = {
    GET_ALL_OPERATION: GetItemsHandler,
    GET_ONE_OPERATION: GetItemHandler,
    CREATE_OPERATION: CreateItemHandler,
    UPDATE_OPERATION: UpdateItemHandler,
    DELETE_OPERATION: DeleteItemHandler,
    GET_COUNT_OPERATION: CountItemsHandler
}

def crud_router_factory(
    repository: TRepository,
    modelResponse: Type[ModelResponse],
    modelRequest: Type[ModelRequest] | None,
    model_name: str,
    id_column_name: str = "id",
    id_type: Type = str,
    operations: Optional[List[str]] = None,
    secure_operations: Optional[List[str]] = None,
    kafka_topic: Optional[str] = None
):
    """
    Factoría Dinámica de Routers CRUD (Create, Read, Update, Delete).

    Esta función genera un `APIRouter` de FastAPI completamente funcional
    para una entidad de base de datos específica, siguiendo el patrón CQRS/Mediator.
    Elimina la necesidad de escribir manualmente los endpoints CRUD repetitivos.

    ### ⚙️ Mecanismo Clave: Inyección de Dependencias (DI) y CQRS
    1.  **Generación de Request:** Por cada operación CRUD permitida, se crea una clase 
        Pydantic (`Command`/`Query`) única en tiempo de ejecución (el "Sello Único").
    2.  **Mapeo a Handler:** Esta clase única se registra inmediatamente en el **Mediator**
        y se mapea a un *Handler* de lógica de negocio (ej. `GetItemsHandler`), inyectándole 
        el repositorio específico (`repository`) de la entidad actual.
    3.  **Endpoint:** El endpoint de FastAPI usa esta clase Pydantic generada para recibir
        los parámetros (URL, Body, Query) y construye el objeto `Request`.
    4.  **Ejecución:** El endpoint simplemente llama a `mediator.send(request, db)`,
        garantizando que la lógica de negocio se ejecuta de forma desacoplada y limpia.

    :param repository: Instancia del repositorio de la entidad (ej. UserRepository), 
                       que implementa la lógica de acceso a datos para SQLAlchemy.
    :param modelResponse: El esquema Pydantic para la respuesta HTTP (lo que devuelve el API).
    :param modelRequest: El esquema Pydantic para la solicitud HTTP (lo que se recibe en CREATE/UPDATE).
    :param model_name: Nombre de la entidad (ej. "User"), usado para prefijos de URL y Swagger.
    :param id_column_name: Nombre de la columna clave usada para buscar/modificar (default: "id").
    :param id_type: Tipo de la clave primaria (default: `str`).
    :param operations: Lista de operaciones CRUD a incluir (ej. ['READ_ALL', 'CREATE']). 
                       Si es `None`, incluye todas las operaciones definidas en `ALL_OPERATIONS`.
    :param secure_operations: Lista de operaciones que requieren autenticación (`Depends(get_current_user)`). 
                              Si es `None`, todas las operaciones se consideran seguras.
    :param kafka_topic: Nombre del tópico de Kafka para publicar eventos de mutación (CREATE/UPDATE/DELETE). 
                        Si es `None`, la publicación de eventos se omite.
                        
    :returns: Un `APIRouter` de FastAPI listo para ser incluido en la aplicación principal.
    :raises ValueError: Si una operación en `secure_operations` no está en `operations`.
    """
    router = APIRouter(prefix=f"/{model_name.lower()}", tags=[model_name])
    
    # Mapeo de campos requeridos para cada Command/Query
    REQUEST_FIELDS_MAP = {
        GET_ALL_OPERATION: {"skip": (int, 0), "limit": (int, 10)},
        GET_ONE_OPERATION: {"item_id": (id_type, ...), "id_column_name": (str, ...)}, 
        CREATE_OPERATION: {"item_data": (dict, ...)},
        UPDATE_OPERATION: {"item_id": (str, ...), "item_data": (dict, ...), "id_column_name": (str, ...)},
        DELETE_OPERATION: {"item_id": (str, ...), "id_column_name": (str, ...)},
        GET_COUNT_OPERATION: {},
    }
    
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


    # --- Funciones Auxiliares para Dependencia Condicional ---

    # 🔑 FUNCIÓN CLAVE: Devuelve un producer o None si el tópico no está configurado.
    # Esto asegura que el tipo en la función de ruta es siempre KafkaProducerService (o Optional)
    # y el valor por defecto es simple.
    def get_kafka_producer_or_none(kafka_topic: Optional[str] = None):
        # Esto es solo un placeholder, la dependencia real debe ser inyectada.
        # El problema es la forma en que FastAPI maneja el `if kafka_topic else None` en el decorador.
        # DEBEMOS HACER QUE EL CÓDIGO SEA ESTÁTICO EN LA FIRMA.
        return Depends(deps.get_kafka_producer)
    # -------------------------------------------------------
    # FUNCIONALIDAD CLAVE: GENERACIÓN Y REGISTRO DINÁMICO
    # -------------------------------------------------------

    def create_request_and_map_handler(op_name: str, handler_class: Type, **kwargs):
        """
        Genera dinámicamente una clase de Request/Command ÚNICA (el 'Sello') 
        y registra su mapeo con el Handler de lógica de negocio correspondiente.

        Esta función establece el vínculo central en el patrón Mediator/CQRS para 
        una operación CRUD específica (ej., GET_ALL) y una entidad (ej., User).

        :param op_name: Nombre de la operación (ej., 'getall', 'create'). 
                        Se usa para generar el nombre de la clase Request/Command.
        :param handler_class: La clase Handler preexistente (ej., GetItemsHandler) 
                            que contiene la lógica de negocio para esta operación.

        :returns: La clase de Request/Command dinámica recién creada (ej., GetUsersAllRequest).
                Esta clase debe ser usada en el endpoint de FastAPI para construir el objeto.

        ### 🧠 El Mecanismo del "Sello Único" (Clase Dinámica)

        La función utiliza la herramienta `type()` de Python para crear una clase Pydantic en tiempo de ejecución. 
        Esto es crucial porque permite que cada entidad (Users, Items, etc.) tenga su propia Request
        personalizada (aunque se basen en los mismos campos) sin necesidad de definirlas manualmente.

        **Ejemplo Demostrativo (para la operación 'getall' en la entidad 'User'):**

        1.  **Datos de entrada:** La función toma los campos del mapeo global (ej., `skip: int = 0`, `limit: int = 10`) y la clase base `IRequest` (que añade `db` y `user_id`).
        
        2.  **Creación del Sello:** La función construye y retorna una nueva clase:
            
            ```python
            # Resultado de type() al construir la Query de paginación para User:
            class GetUsersAllRequest(IRequest):
                skip: int = Field(default=0)
                limit: int = Field(default=10)
                # user_id y db vienen de IRequest
            ```
            
            El objeto retornado, `UniqueRequest` (ej., **`GetUsersAllRequest`**), es el "Sello Único". Este sello ahora tiene los atributos **`.skip`**, **`.limit`**, **`.user_id`**, etc., y es la única clave que el **Mediator** necesita para encontrar el **Handler** (`GetItemsHandler`) que ejecutará la lógica de la paginación.

        **Proceso de Registro:**
        La función también garantiza que esta clase `UniqueRequest` se registra inmediatamente con una nueva instancia del `handler_class`, inyectándole el `repository` específico de la entidad.
        Para más ayuda, consultar https://gemini.google.com/app/a98aec1368ec4956
        """
        
        request_type_name = f"{op_name.capitalize()}{model_name}Request"
        if op_name == GET_ONE_OPERATION:
            base_fields = {"item_id": (kwargs.get('id_type'), ...), "id_column_name": (str, ...)}
        base_fields = REQUEST_FIELDS_MAP.get(op_name, {}) 

        # --- DICIONARIOS CLAVE PARA CONSTRUCCIÓN DINÁMICA ---
        dynamic_annotations: Dict[str, Any] = {}
        dynamic_fields: Dict[str, Any] = {} 
        
        # 1. Iterar sobre los campos para separar la anotación del valor/Field
        for field_name, (field_type, field_default) in base_fields.items():
            
            # 1a. REGISTRAR ANOTACIÓN: Todos los campos DEBEN estar en __annotations__
            dynamic_annotations[field_name] = field_type
            
            # 1b. REGISTRAR VALOR O FIELD: Para el namespace de la clase
            if field_default is ...:
                # Si es requerido (usamos el default implícito de Pydantic)
                pass 
            else:
                # Si tiene un valor por defecto (ej. skip=0, limit=10), usamos Field
                # Esto es lo que Pydantic V2 espera: Field(default=...)
                dynamic_fields[field_name] = Field(default=field_default, annotation=field_type)


        # 2. Construir el Namespace Final
        # El namespace de la clase necesita:
        # - '__module__': Para evitar advertencias.
        # - '__annotations__': Para que Pydantic conozca los tipos.
        # - Los campos con valores por defecto (ej. skip=Field(...))
        dynamic_namespace = {
            '__module__': handler_class.__module__,
            '__annotations__': dynamic_annotations, # <--- ¡Aquí Pydantic busca 'skip'!
            **dynamic_fields # <--- Aquí añadimos los campos con Field
        }
        
        # 3. Creación de la clase Command/Query ÚNICA
        # UniqueRequest hereda de IRequest (que debe heredar de pydantic.BaseModel)
        UniqueRequest = type(request_type_name, (IRequest,), dynamic_namespace)
        
        # 4. Registro en MediatR
        mediator.register_handler(UniqueRequest, handler_class(repository))
        
        return UniqueRequest 
    # ---
    
    # -------------------------------------------------------
    # DEFINICIÓN DE LÓGICA Y RUTAS PARA CADA OPERACIÓN
    # -------------------------------------------------------

    # --- GET ALL ---
    
    # Crear las rutas según las operaciones
    if GET_ALL_OPERATION in operations:
        QueryAll = create_request_and_map_handler(GET_ALL_OPERATION, HANDLER_MAP[GET_ALL_OPERATION])
        
        # 🔑 CLAVE: Definir el modelo de respuesta dinámico para PagedResult[modelResponse]
        # Pydantic genera un modelo en tiempo de ejecución para el genérico
        PagedModelResponse = PagedResult[modelResponse]
        
        # Aquí verificamos si la operación está en la lista de operaciones seguras
        is_secure = GET_ALL_OPERATION in secure_operations
        @router.get("/", response_model=PagedModelResponse, 
                     summary=f"Retrieve all {model_name} items", 
                     description=f"📚Fetch a list of all {model_name} records from the database.")
        async def read_all(db: AsyncSession = Depends(deps.get_session),
                           skip: int = 0, 
                           limit: int = 10, 
                           # Inyectamos el usuario de forma condicional
                           current_user: Optional[User] = Depends(deps.get_current_user) if is_secure else None):
            """
            Retrieve all items of type {model_name}.

            - **Returns**: List of {model_name} objects.
            """
            # Lógica para manejar el user_id
            user_id = current_user.user_id if current_user else None
            query = QueryAll(db=db, user_id=user_id, skip=skip, limit=limit)
            return await mediator.send(query, db)
        
    if GET_COUNT_OPERATION in operations:
        QueryCount = create_request_and_map_handler(GET_COUNT_OPERATION, HANDLER_MAP[GET_COUNT_OPERATION])
        
        is_secure = GET_COUNT_OPERATION in secure_operations
        @router.get("/count", response_model=int,
                            summary=f"Get count of {model_name} items",
                            description=f"🔢 Retrieves the total number of {model_name} records in the database, optionally respecting user scope.")
        async def get_count(db: AsyncSession = Depends(deps.get_session),
                            current_user: Optional[User] = Depends(deps.get_current_user) if is_secure else None):
            """
            Calcula y devuelve la cantidad total de registros de la entidad {model_name}.
            
            Este endpoint se utiliza para obtener rápidamente el número de registros,
            siendo fundamental para la paginación y la visualización de totales en el frontend. 
            
            **Mecanismo de Ejecución:**
            1.  Crea la Query única mapeada (ej., `GetCountUserRequest`).
            2.  Inyecta la sesión de DB (`db`) y, si es una operación segura (`is_secure` es True),
                el ID del usuario actual (`user_id`).
            3.  Delega la ejecución al Handler registrado (`GetCountHandler`).
            4.  El Handler utiliza el repositorio para realizar un conteo eficiente a nivel de base de datos.
                Si se pasa `user_id`, el Handler puede aplicar filtros de negocio (ej. 'solo mis tareas').

            - **Returns**: El número total de registros como un entero (`int`).
            - **Security**: Aplica la seguridad definida en `secure_operations` para filtrar por propietario/permisos.
            """
            user_id = current_user.user_id if current_user else None
            query = QueryCount(db=db, user_id=user_id)
            return await mediator.send(query, db)
    
    if GET_ONE_OPERATION in operations:
        QueryOne = create_request_and_map_handler(GET_ONE_OPERATION, HANDLER_MAP[GET_ONE_OPERATION])
        
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
            query = QueryOne(item_id=item_id, db=db, user_id=user_id,id_column_name=id_column_name) 
            return await mediator.send(query, db)
    
    if CREATE_OPERATION in operations:
        CommandCreate = create_request_and_map_handler(CREATE_OPERATION, HANDLER_MAP[CREATE_OPERATION])
        # Aquí verificamos si la operación está en la lista de operaciones seguras
        is_secure = CREATE_OPERATION in secure_operations
        @router.post("/", 
                     response_model=modelResponse, 
                     status_code=201,
                     response_model_exclude={"password"},
                     summary=f"Create a new {model_name}",
                     description=f"➕Add a new {model_name} to the database.")
        async def create_one(item: modelRequest, 
                             db: AsyncSession = Depends(deps.get_session), 
                             # Inyectamos el usuario de forma condicional
                             current_user: Optional[User] = Depends(deps.get_current_user) if is_secure else None,
                             # 🔑 CORRECCIÓN APLICADA: Declaramos la dependencia SIEMPRE
                            # y manejamos el `kafka_topic` dentro del cuerpo de la función.
                            # Esto elimina la expresión `if/else` de la firma.
                            kafka_producer: KafkaProducerService = Depends(deps.get_kafka_producer)
                            ):
            """
            Create a new {model_name} record.
            Crea un nuevo registro y publica un evento de creación a Kafka (si está configurado).
            Implementa el patrón de Commit Dual Simplificado.

            - **param item**: A {model_name} object to create.
            - **Returns**: The created {model_name} with its assigned ID.
            """
            user_id = current_user.user_id if current_user else None
            command = CommandCreate(item_data=item.model_dump(), db=db, user_id=user_id)
            # 1. EJECUTAR HANDLER (Persistencia DB y Auditoría)
            # El Handler se encarga de llamar a repository.create() y hacer el db.commit()
            # return await mediator.send(command, db)
            db_item = await mediator.send(command, db) 
            # 2. 🔑 COMMIT DUAL: Publicar evento solo si la DB fue exitosa
            if kafka_producer and kafka_topic:
                try:
                    entity_id = str(getattr(db_item, id_column_name))
                    event_data = {
                        "id": entity_id,
                        "entity": model_name,
                        "action": f"{model_name.upper()}_CREATED",
                        "payload": item.model_dump() # Usamos el payload de la request
                    }
                    
                    # Esperamos el envío (send_and_wait) para alta fiabilidad
                    await kafka_producer.produce(
                        topic=kafka_topic,
                        value=event_data,
                        key=entity_id
                    )
                except Exception as kafka_e:
                    logger.warning(f"Advertencia Crítica: DB commit exitoso, pero fallo al publicar evento a Kafka. Tópico: {kafka_topic}. Error: {kafka_e}")
                    # NOTA: No revertimos la transacción de la DB.

            return db_item

    if UPDATE_OPERATION in operations:
        CommandUpdate = create_request_and_map_handler(UPDATE_OPERATION, HANDLER_MAP[UPDATE_OPERATION])
        is_secure = UPDATE_OPERATION in secure_operations
        @router.put("/{item_id}", 
                    response_model=modelResponse,
                    summary=f"Update an existing {model_name}",
                    description=f"✏️Modify the {model_name} identified by the given ID.")
        async def update_one(item_id: int, 
                             item: modelResponse, 
                             db: AsyncSession = Depends(deps.get_session), 
                             # Inyectamos el usuario de forma condicional
                             current_user: Optional[User] = Depends(deps.get_current_user) if is_secure else None,
                             # 🔑 CORRECCIÓN APLICADA: Declaramos la dependencia SIEMPRE
                            # y manejamos el `kafka_topic` dentro del cuerpo de la función.
                            # Esto elimina la expresión `if/else` de la firma.
                            kafka_producer: KafkaProducerService = Depends(deps.get_kafka_producer)
                             ):
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
            # return await mediator.send(command, db)
            db_item = await mediator.send(command, db)
            
            # 2. 🔑 COMMIT DUAL: Publicar evento
            if kafka_producer and kafka_topic:
                try:
                    entity_id = str(getattr(db_item, id_column_name))
                    event_data = {
                        "id": entity_id,
                        "entity": model_name,
                        "action": f"{model_name.upper()}_UPDATED",
                        "payload": item.model_dump()
                    }
                    await kafka_producer.produce(topic=kafka_topic, value=event_data, key=entity_id)
                except Exception as kafka_e:
                    logger.warning(f"Advertencia: Fallo al publicar evento de UPDATE a Kafka. Error: {kafka_e}")
            
            return db_item

    if DELETE_OPERATION in operations:
        CommandDelete = create_request_and_map_handler(DELETE_OPERATION, HANDLER_MAP[DELETE_OPERATION])
        # Aquí verificamos si la operación está en la lista de operaciones seguras
        is_secure = DELETE_OPERATION in secure_operations
        @router.delete("/{item_id}", 
                       status_code=204,
                       response_model=None, # ✅ CLAVE: Indicar que no devuelve cuerpo (solo 204)
                       summary=f"Delete a {model_name} by ID",
                       description=f"❌Remove the {model_name} specified by the unique ID from the database.")
        async def delete_one(item_id: str, 
                             db: AsyncSession = Depends(deps.get_session), 
                             # Inyectamos el usuario de forma condicional
                             current_user: Optional[User] = Depends(deps.get_current_user) if is_secure else None,
                             # 🔑 CORRECCIÓN APLICADA: Declaramos la dependencia SIEMPRE
                             # y manejamos el `kafka_topic` dentro del cuerpo de la función.
                             # Esto elimina la expresión `if/else` de la firma.
                             kafka_producer: KafkaProducerService = Depends(deps.get_kafka_producer)
                             ):
            """
            Delete a {model_name} record by ID.

            - **param item_id**: ID of the {model_name} to delete.
            - **Raises**: 404 if the {model_name} does not exist.
            - **Returns**: HTTP 204 No Content on success.
            """
            # Lógica para manejar el user_id
            user_id = current_user.user_id if current_user else None
            command = CommandDelete(item_id=item_id, db=db, user_id=user_id,id_column_name=id_column_name)
            # await mediator.send(command, db)
            # El Handler ejecuta la eliminación y hace el db.commit()
            await mediator.send(command, db) 
            
            # 2. 🔑 COMMIT DUAL: Publicar evento de eliminación
            if kafka_producer and kafka_topic:
                try:
                    entity_id = str(item_id)
                    event_data = {
                        "id": entity_id,
                        "entity": model_name,
                        "action": f"{model_name.upper()}_DELETED",
                        "payload": {"status": "deleted"} # Payload mínimo para DELETED
                    }
                    await kafka_producer.produce(topic=kafka_topic, value=event_data, key=entity_id)
                except Exception as kafka_e:
                    logger.warning(f"Advertencia: Fallo al publicar evento de DELETE a Kafka. Error: {kafka_e}")
            
            return # <--- Aquí el router retorna un HTTP 204 sin contenido
            
    return router