# commands_queries.py
from typing import Optional
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
    item_id: str
    user_id: Optional[str] = None
    
# Command para actualizar un item existente
class UpdateItemCommand(BaseModel):
    item_id: str
    item_data: dict
    user_id: Optional[str] = None
    
# Command para eliminar un item
class DeleteItemCommand(BaseModel):
    item_id: str
    user_id: Optional[str] = None