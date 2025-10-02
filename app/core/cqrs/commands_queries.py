# commands_queries.py
from typing import Any, Optional
from pydantic import BaseModel

# Command para crear un nuevo item
class CreateItemCommand(BaseModel):
    item_data: dict
    user_id: Optional[str] = None

# Query para obtener un item por ID
class GetItemsQuery(BaseModel):
    user_id: Optional[str] = None
    
# Query para obtener un item por ID
class GetItemByIdQuery(BaseModel):
    # Identificador del ítem (el valor, ej. '123' o 'a1b2c3d4')
    item_id: Any
    # Nombre de la columna que contiene el ID (ej. 'id' o 'uuid').
    # Este campo es inyectado por el crud_router_factory.
    id_column_name: str
    # Usuario que realiza la consulta (para lógica de permisos)
    user_id: Optional[str] = None
    
# Command para actualizar un item existente
class UpdateItemCommand(BaseModel):
    # El valor del ID (puede ser int, str, UUID)
    item_id: Any 
    # El nombre de la columna ID (ej. 'id', 'uuid', 'slug')
    id_column_name: str 
    # Los datos a actualizar (como un dict genérico)
    item_data: dict
    # Usuario que realiza la consulta (para lógica de permisos)
    user_id: Optional[str] = None
    
# Command para eliminar un item
class DeleteItemCommand(BaseModel):
    # El valor del ID (puede ser int, str, UUID)
    item_id: str
    # El nombre de la columna ID (ej. 'id', 'uuid', 'slug')
    id_column_name: str 
    # Usuario que realiza la consulta (para lógica de permisos)
    user_id: Optional[str] = None