# commands_queries.py
from typing import Any, Optional
from pydantic import BaseModel

# Command para crear un nuevo item
class CreateItemCommand(BaseModel):
    """
    Define la intención de **CREAR** un nuevo recurso.
    Actúa como un DTO que encapsula los datos necesarios para la operación, 
    separando la intención de la ejecución.
    """
    item_data: dict
    """Diccionario que contiene los campos y valores del nuevo ítem a crear."""
    user_id: Optional[str] = None
    """ID del usuario que realiza la operación (esencial para auditoría y permisos)."""

# Query para obtener un item por ID
class GetItemsQuery(BaseModel):
    """
    Define la intención de **RECUPERAR** una colección de recursos.
    Este DTO genérico es usado para listar ítems, típicamente soportando
    paginación (skip/limit) y filtrado básico a través de la Factory.
    """
    user_id: Optional[str] = None
    """ID del usuario que realiza la consulta (para implementar filtros de seguridad/visibilidad)."""
    
# Query para obtener un item por ID
class GetItemByIdQuery(BaseModel):
    """
    Define la intención de **RECUPERAR** un único recurso utilizando un identificador.
    Este DTO es crucial para las operaciones de lectura detallada (READ ONE).
    """
    item_id: Any
    """
    El valor identificador único del ítem (puede ser int, str, o UUID). 
    Su tipo es 'Any' para soportar la genericidad del sistema.
    """
    id_column_name: str
    """
    Nombre de la columna de la base de datos que se utilizará para la búsqueda (ej. 'id', 'uuid', 'nombre').
    Este campo es inyectado dinámicamente por el crud_router_factory para genericidad.
    """
    user_id: Optional[str] = None
    """ID del usuario que realiza la consulta (para lógica de permisos/propiedad)."""
    
# Command para actualizar un item existente
class UpdateItemCommand(BaseModel):
    """
    Define la intención de **ACTUALIZAR** los datos de un recurso existente.
    Contiene tanto el identificador del ítem a modificar como los nuevos datos.
    """
    item_id: Any 
    """El valor identificador del ítem a actualizar (int, str, UUID)."""
    id_column_name: str 
    """
    Nombre de la columna de la base de datos a utilizar para la búsqueda del ítem. 
    Inyectado por la Factory.
    """
    item_data: dict
    """Diccionario con los datos del ítem a actualizar."""
    user_id: Optional[str] = None
    """ID del usuario que realiza la consulta (para lógica de permisos/propiedad)."""
    
# Command para eliminar un item
class DeleteItemCommand(BaseModel):
    """
    Define la intención de **ELIMINAR** un recurso específico.
    Solo necesita el identificador y el contexto de seguridad para ser ejecutado.
    """
    item_id: Any
    """El valor identificador del ítem a eliminar (int, str, UUID)."""
    id_column_name: str 
    """
    Nombre de la columna de la base de datos a utilizar para la búsqueda del ítem. 
    Inyectado por la Factory.
    """
    user_id: Optional[str] = None
    """ID del usuario que realiza la operación (para registrar la baja)."""