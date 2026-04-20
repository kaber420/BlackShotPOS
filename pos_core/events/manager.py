"""
Manager de suscripciones Pub/Sub para WebSockets.
Centraliza las conexiones activas y permite el envío seguro de mensajes.
"""
from fastapi import WebSocket
from fastapi.encoders import jsonable_encoder
from typing import Dict, List, Any
import logging

logger = logging.getLogger(__name__)

class PubSubManager:
    def __init__(self):
        # Mapea un topic a una lista de WebSockets activos
        self.active_connections: Dict[str, List[WebSocket]] = {}

    def connect(self, websocket: WebSocket, topic: str):
        if topic not in self.active_connections:
            self.active_connections[topic] = []
        if websocket not in self.active_connections[topic]:
            self.active_connections[topic].append(websocket)
            logger.info(f"🔌 Suscrito WebSocket a '{topic}'. Total {topic}: {len(self.active_connections[topic])}")

    def disconnect(self, websocket: WebSocket, topic: str = None):
        if topic:
            if topic in self.active_connections and websocket in self.active_connections[topic]:
                self.active_connections[topic].remove(websocket)
                logger.info(f"🔌 Desuscrito de '{topic}'. Restantes {topic}: {len(self.active_connections[topic])}")
        else:
            # Buscar y eliminar de todos los topics
            for t, wss in self.active_connections.items():
                if websocket in wss:
                    wss.remove(websocket)
                    logger.info(f"🔌 Desuscrito (desconexión general) de '{t}'. Restantes: {len(wss)}")

    async def broadcast(self, topic: str, message: Any):
        """Envía un mensaje a todos los suscriptores de un tópico de forma segura."""
        if topic not in self.active_connections or not self.active_connections[topic]:
            return

        # Aseguramos que el mensaje sea serializable antes de intentar enviar
        try:
            safe_payload = {
                "topic": topic,
                "data": jsonable_encoder(message)
            }
        except Exception as e:
            logger.error(f"❌ Error al serializar mensaje para tópico '{topic}': {e}")
            return

        dead_connections = []
        for connection in self.active_connections[topic]:
            try:
                await connection.send_json(safe_payload)
            except Exception as e:
                logger.warning(f"⚠️ Error al enviar a socket en tópico '{topic}': {e}")
                dead_connections.append(connection)
        
        # Limpieza de conexiones muertas
        for dead in dead_connections:
            self.disconnect(dead, topic)

# Instancia global del manager
broadcaster = PubSubManager()
