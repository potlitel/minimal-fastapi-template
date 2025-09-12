# mediator.py
from typing import Dict, Any, Type
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

class Mediator:
    """Clase mediadora para el patrón MediatR."""
    
    def __init__(self):
        self._handlers: Dict[Type[Any], Any] = {}

    def register_handler(self, request_type: Type[Any], handler_instance: Any):
        """Registra un handler para un tipo de solicitud específico."""
        self._handlers[request_type] = handler_instance

    def send(self, request: Any, db: AsyncSession):
        """Envía una solicitud al handler registrado y lo ejecuta."""
        handler = self._handlers.get(type(request))
        if not handler:
            raise ValueError(f"No handler registered for request type: {type(request).__name__}")
        return handler.handle(request, db)

# Se crea una instancia global del mediador
mediator = Mediator()

def get_mediator():
    """Dependencia para inyectar el mediador en los endpoints."""
    yield mediator