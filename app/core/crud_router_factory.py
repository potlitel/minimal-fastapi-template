# crud_utils.py
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List, Type
from pydantic import BaseModel
# from database import get_db
from app.api import api_messages, deps
from sqlalchemy.ext.asyncio import AsyncSession

def crud_router_factory(
    db_model: Type, 
    pydantic_model: Type[BaseModel], 
    model_name: str
):
    router = APIRouter(prefix=f"/{model_name.lower()}s", tags=[model_name])
    
    @router.get("/", response_model=List[pydantic_model])
    def read_all(db: AsyncSession = Depends(deps.get_session)):
        items = db.query(db_model).all()
        return items
    
    @router.get("/{item_id}", response_model=pydantic_model)
    def read_one(item_id: int, db: AsyncSession = Depends(deps.get_session)):
        item = db.query(db_model).filter(db_model.id == item_id).first()
        if not item:
            raise HTTPException(status_code=404, detail=f"{model_name} not found")
        return item
    
    @router.post("/", response_model=pydantic_model, status_code=201)
    def create_one(item: pydantic_model, db: AsyncSession = Depends(deps.get_session)):
        db_item = db_model(**item.dict())
        db.add(db_item)
        db.commit()
        db.refresh(db_item)
        return db_item

    @router.put("/{item_id}", response_model=pydantic_model)
    def update_one(item_id: int, item: pydantic_model, db: AsyncSession = Depends(deps.get_session)):
        db_item = db.query(db_model).filter(db_model.id == item_id).first()
        if not db_item:
            raise HTTPException(status_code=404, detail=f"{model_name} not found")
        
        for key, value in item.dict(exclude_unset=True).items():
            setattr(db_item, key, value)
            
        db.commit()
        db.refresh(db_item)
        return db_item

    @router.delete("/{item_id}", status_code=204)
    def delete_one(item_id: int, db: AsyncSession = Depends(deps.get_session)):
        db_item = db.query(db_model).filter(db_model.id == item_id).first()
        if not db_item:
            raise HTTPException(status_code=404, detail=f"{model_name} not found")
        
        db.delete(db_item)
        db.commit()
        return {"message": f"{model_name} deleted successfully"}
        
    return router