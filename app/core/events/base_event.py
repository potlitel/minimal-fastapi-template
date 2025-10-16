# app/core/events/base_event.py

import time
from pydantic import BaseModel
from typing import Any

class DomainEvent(BaseModel):
    """
    DTO base para cualquier evento de dominio emitido.
    """
    event_name: str
    """Nombre único del evento (ej: 'user.created')."""
    payload: dict[str, Any]
    """Carga útil de datos del evento."""
    timestamp: float
    """Timestamp UNIX de la creación del evento."""
    
    # Método de fábrica para crear eventos fácilmente
    @classmethod
    def create(cls, name: str, data: dict) -> 'DomainEvent':
        return cls(event_name=name, payload=data, timestamp=time.time())

# app/core/events/event_producer.py (Interfaz)
from abc import ABC, abstractmethod

class IEventProducer(ABC):
    """Interfaz para desacoplar el Handler del sistema de mensajería (Kafka)."""
    @abstractmethod
    async def publish(self, topic: str, event: DomainEvent) -> None:
        pass