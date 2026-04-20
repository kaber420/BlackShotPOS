from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pos_core.database import get_session
from pos_core.events.manager import broadcaster
from .service import get_device_by_token, update_device_last_seen
import logging
import asyncio

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws/iot")
async def iot_websocket(websocket: WebSocket):
    """
    WebSocket especializado para dispositivos IoT (ESP32).
    Usa autenticación por token simple y payloads optimizados.
    """
    await websocket.accept()
    
    # 1. Autenticación via token en query string
    token = websocket.query_params.get("token")
    if not token:
        await websocket.send_json({"err": "no_token"})
        await websocket.close(code=1008)
        return

    async for db in get_session():
        device = await get_device_by_token(db, token)
        if not device:
            await websocket.send_json({"err": "invalid_token"})
            await websocket.close(code=1008)
            return
        
        # Asociación con la mesa
        table_id = device.table_id
        device_id = device.id
        topic = f"iot_table_{table_id}"
        
        logger.info(f"🤖 Dispositivo IoT conectado: {device.name or device.device_id} (Mesa {table_id})")
        
        # Suscribir al tópico de la mesa
        broadcaster.connect(websocket, topic)
        
        try:
            # Actualizar last_seen inicialmente
            await update_device_last_seen(db, device_id)
            
            # Bucle de escucha (para latidos o comandos como "Llamar Mesero")
            while True:
                data = await websocket.receive_json()
                action = data.get("action")
                
                if action == "ping":
                    await websocket.send_json({"ev": "pong"})
                    # Ocasionalmente actualizar last_seen
                    await update_device_last_seen(db, device_id)
                
                elif action == "call_waiter":
                    # Disparar un evento para el POS general
                    await broadcaster.broadcast("dashboard_stats", {
                        "type": "notification",
                        "msg": f"🔔 Mesa {table_id} solicita asistencia",
                        "table_id": table_id
                    })
                    await websocket.send_json({"ev": "msg", "msg": "Mesero en camino"})

        except WebSocketDisconnect:
            logger.info(f"🔌 Dispositivo IoT desconectado: {device.device_id}")
        except Exception as e:
            logger.error(f"❌ Error en WebSocket IoT: {e}")
        finally:
            broadcaster.disconnect(websocket, topic)
        break
