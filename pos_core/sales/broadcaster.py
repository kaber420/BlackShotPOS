"""
Broadcaster de eventos para comunicación en tiempo real vía WebSockets.

Implementa el patrón Pub/Sub. Mantiene un registro de los clientes conectados
por "topic" y despacha eventos JSON a los suscriptores.
"""
from fastapi import WebSocket
from typing import Dict, List
import json

class PubSubManager:
    def __init__(self):
        # Mapea un topic a una lista de WebSockets activos
        self.active_connections: Dict[str, List[WebSocket]] = {}

    def connect(self, websocket: WebSocket, topic: str):
        if topic not in self.active_connections:
            self.active_connections[topic] = []
        if websocket not in self.active_connections[topic]:
            self.active_connections[topic].append(websocket)
            print(f"🔌 Suscrito WebSocket a '{topic}'. Total {topic}: {len(self.active_connections[topic])}")

    def disconnect(self, websocket: WebSocket, topic: str = None):
        if topic:
            if topic in self.active_connections and websocket in self.active_connections[topic]:
                self.active_connections[topic].remove(websocket)
                print(f"🔌 Desuscrito de '{topic}'. Restantes {topic}: {len(self.active_connections[topic])}")
        else:
            # Buscar y eliminar de todos los topics
            for t, wss in self.active_connections.items():
                if websocket in wss:
                    wss.remove(websocket)
                    print(f"🔌 Desuscrito (desconexión general) de '{t}'. Restantes: {len(wss)}")

    async def broadcast(self, topic: str, message: dict):
        if topic in self.active_connections:
            dead_connections = []
            for connection in self.active_connections[topic]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    # Si falla al enviar, marcamos para remover
                    print(f"Error boradcasting to socket in {topic}: {e}")
                    dead_connections.append(connection)
            
            for dead in dead_connections:
                self.disconnect(dead, topic)

# Instancia global — se importará desde router.py
broadcaster = PubSubManager()
