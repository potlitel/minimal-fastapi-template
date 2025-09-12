# commands_queries.py
from pydantic import BaseModel

# Command para crear un nuevo item
class CreateItemCommand(BaseModel):
    item_data: dict

# Query para obtener un item por ID
class GetItemsQuery(BaseModel):
    pass
    
# Query para obtener un item por ID
class GetItemByIdQuery(BaseModel):
    item_id: str
    
# Command para actualizar un item existente
class UpdateItemCommand(BaseModel):
    item_id: str
    item_data: dict
    
# Command para eliminar un item
class DeleteItemCommand(BaseModel):
    item_id: str