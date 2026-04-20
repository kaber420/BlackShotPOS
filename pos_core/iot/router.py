from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pos_core.database import get_session
from pos_core.events.manager import pos_broadcaster, iot_broadcaster
from pos_core.events.service import trigger_broadcast
from .service import get_device_by_token, update_device_last_seen, update_device_health
from pos_core.settings.service import get_settings
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
        iot_broadcaster.connect(websocket, topic)
        
        # Notificar al panel de admin que este dispositivo está ONLINE (vía pos_broadcaster)
        await pos_broadcaster.broadcast("admin_iot", {
            "type": "status",
            "device_id": device_id,
            "status": "online"
        })

        # --- ENVÍO DE CONFIGURACIÓN INICIAL (Zero-Config) ---
        try:
            settings = await get_settings(db)
            await websocket.send_json({
                "ev": "config",
                "business_name": settings.name,
                "device_name": device.name or f"Mesa {table_id}",
                "table_id": table_id
            })
        except Exception as e:
            logger.error(f"⚠️ Error al enviar config inicial: {e}")
        
        try:
            # Actualizar last_seen inicialmente
            await update_device_last_seen(db, device_id)
            
            # Bucle de escucha (para latidos o comandos como "Llamar Mesero")
            while True:
                data = await websocket.receive_json()
                action = data.get("action")
                
                if action == "ping":
                    await websocket.send_json({"ev": "pong"})
                    await update_device_last_seen(db, device_id)
                
                elif action == "health":
                    # Reporte de salud: rssi, battery, version
                    rssi = data.get("rssi")
                    battery = data.get("battery")
                    version = data.get("version")
                    
                    await update_device_health(db, device_id, rssi=rssi, battery=battery)
                    
                    # Notificar al panel de admin (vía pos_broadcaster)
                    await pos_broadcaster.broadcast("admin_iot", {
                        "type": "health",
                        "device_id": device_id,
                        "rssi": rssi,
                        "battery": battery,
                        "version": version
                    })
                
                elif action == "call_waiter":
                    # Disparar un evento para el POS general
                    await trigger_broadcast("dashboard_stats")
                    await websocket.send_json({"ev": "msg", "msg": "Mesero en camino"})

                elif action == "request_bill":
                    # Notificar al POS que la mesa quiere su cuenta
                    await trigger_broadcast("dashboard_stats") 
                    await websocket.send_json({"ev": "msg", "msg": "Solicitando cuenta..."})
                    logger.info(f"🧾 Mesa {table_id} solicitó la cuenta")

        except WebSocketDisconnect:
            logger.info(f"🔌 Dispositivo IoT desconectado: {device.device_id}")
            # Notificar al panel de admin que este dispositivo está OFFLINE (vía pos_broadcaster)
            await pos_broadcaster.broadcast("admin_iot", {
                "type": "status",
                "device_id": device_id,
                "status": "offline"
            })
        except Exception as e:
            logger.error(f"❌ Error en WebSocket IoT: {e}")
        finally:
            iot_broadcaster.disconnect(websocket, topic)
        break
