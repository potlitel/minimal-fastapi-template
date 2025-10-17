#!/bin/bash
# Script: create-topics.sh

# Configuración
KAFKA_BROKER='broker:29092' 
TOPICS=("user_events" "order_events")

echo "✅ Broker de Kafka está listo (Verificado por Healthcheck). Procediendo a la creación de tópicos."

# --- Creación de Tópicos ---

for TOPIC_NAME in "${TOPICS[@]}"; do
    kafka-topics --bootstrap-server "$KAFKA_BROKER" \
                 --create \
                 --if-not-exists \
                 --topic "$TOPIC_NAME" \
                 --partitions 1 \
                 --replication-factor 1
    
    if [ $? -eq 0 ]; then
        echo "Tópico $TOPIC_NAME: Creado o ya existente."
    else
        # Si esto falla aquí, es un problema de conectividad o permisos, 
        # no de disponibilidad inicial.
        echo "ERROR: Falló la creación del tópico $TOPIC_NAME."
    fi
done

echo "Script de creación de tópicos finalizado."

exit 0