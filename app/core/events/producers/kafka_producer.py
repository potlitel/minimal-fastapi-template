# producers/kafka_producer.py
from aiokafka import AIOKafkaProducer
from typing import Optional
import json

from fastapi import logger

class KafkaProducerService:
    """
    Servicio robusto para producir mensajes a Kafka de forma asíncrona.
    Gestiona la conexión única del productor y los parámetros de fiabilidad.
    """
    def __init__(self, bootstrap_servers: str):
        """
        Inicializa la instancia del productor. Solo los parámetros básicos del cliente van aquí.

        - **param bootstrap_servers**: Lista de brokers de Kafka (ej. "localhost:9092").
        """
        # 🔑 CONFIGURACIÓN DEL CLIENTE
        self.producer: Optional[AIOKafkaProducer] = AIOKafkaProducer(
            bootstrap_servers=bootstrap_servers,
            # Serializador: Convierte el diccionario Python a JSON y luego a bytes (utf-8)
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            # Tiempo de espera para la respuesta del broker antes de fallar (10s)
            request_timeout_ms=10000, 
        )
        self.is_running = False

    async def start(self):
        """
        Inicia el productor de Kafka, aplicando las configuraciones de robustez 
        y fiabilidad que deben pasarse al método start().
        """
        if self.is_running:
            return
            
        if self.producer is None:
            raise RuntimeError("El productor AIOKafkaProducer no fue inicializado correctamente.")
        
        try:
            # 🔑 CONFIGURACIÓN DE ROBUSTEZ Y RENDIMIENTO (VA EN start())
            await self.producer.start()
            self.is_running = True
            print("🟢 Kafka Producer iniciado correctamente.")
            
        except Exception as e:
            print(f"🔴 Error crítico al iniciar Kafka Producer: {e}")
            raise # Lanzar la excepción para que el lifespan de FastAPI falle

    async def stop(self):
        """Cierra la conexión del productor de forma limpia."""
        if self.is_running and self.producer:
            await self.producer.stop()
            self.is_running = False
            print("🔴 Kafka Producer detenido.")

    async def produce(self, topic: str, value: dict, key: Optional[str] = None):
        """
        Produce un mensaje a un tópico de Kafka de forma asíncrona y espera la confirmación (send_and_wait).

        - **param topic**: Nombre del tópico de destino.
        - **param value**: Diccionario con el contenido del mensaje (se serializa a JSON).
        - **param key**: Clave del mensaje (se usa para garantizar el orden por partición).
        """
        if not self.is_running or self.producer is None:
            logger.warning(f"Intento de producción fallido: el productor de Kafka no está iniciado. Tópico: {topic}")
            raise ConnectionError("El productor de Kafka no está activo.")
            
        key_bytes = key.encode('utf-8') if key else None
        
        # Envío síncrono para el cliente asíncrono. Asegura que el evento se persista
        # antes de continuar (Commit Dual Simplificado).
        await self.producer.send_and_wait(
            topic=topic,
            value=value,
            key=key_bytes
        )
        logger.debug(f"📩 Evento enviado a Kafka en el tópico '{topic}' (Key: {key}).")