from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pos_core.database import get_session
from pos_core.events.manager import pos_broadcaster, iot_broadcaster
from pos_core.events.service import trigger_broadcast
from .service import get_device_by_token, update_device_last_seen, update_device_health
from pos_core.settings.service import get_settings
from pos_core.sales.services.order_lifecycle_service import get_orders
from pos_core.sales.schemas import OrderRead
from pos_core.sales.models import OrderStatus
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
            await websocket.send_json({"event": "system_error", "data": {"code": "AUTH_FAILED", "message": "invalid_token"}})
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
            config_payload = {
                "event": "config",
                "data": {
                    "business_name": settings.name,
                    "device_name": device.name or f"Mesa {table_id}",
                    "table_id": int(table_id) if table_id else 0
                }
            }
            await websocket.send_json(config_payload)
            logger.info(f"📡 Configuración enviada a Mesa {table_id}: {settings.name}")
        except Exception as e:
            logger.error(f"⚠️ Error al enviar config inicial: {e}")
        
        try:
            # Actualizar last_seen inicialmente
            await update_device_last_seen(db, device_id)
            
            # Bucle de escucha (para latidos o comandos como "Llamar Mesero")
            while True:
                data = await websocket.receive_json()
                action = data.get("action")
                payload = data.get("data") or data.get("payload") or {}
                
                if action == "ping":
                    await websocket.send_json({"event": "pong"})
                    await update_device_last_seen(db, device_id)
                
                elif action in ["health", "heartbeat"]:
                    # Reporte de salud nativo (Acepta ambos nombres)
                    rssi = payload.get("rssi") if isinstance(payload, dict) else data.get("rssi")
                    battery = payload.get("battery") if isinstance(payload, dict) else data.get("battery")
                    free_heap = payload.get("free_heap") if isinstance(payload, dict) else data.get("free_heap")
                    
                    await update_device_health(db, device_id, rssi=rssi, battery=battery)
                    
                    # Notificar al panel de admin
                    await pos_broadcaster.broadcast("admin_iot", {
                        "type": "health",
                        "device_id": device_id,
                        "rssi": rssi,
                        "battery": battery,
                        "free_heap": free_heap
                    })
                
                elif action == "sync_orders":
                    # Recuperar órdenes activas para esta mesa
                    logger.info(f"🔄 Mesa {table_id} solicitó sincronización de órdenes")
                    raw_orders = await get_orders(db)
                    order_dicts = [OrderRead.model_validate(o).model_dump(mode="json") for o in raw_orders]
                    active_orders = [
                        o for o in order_dicts
                        if o["table_id"] == table_id
                        and o["status"] not in [OrderStatus.CANCELLED.value]
                        and o["status"] != OrderStatus.PAID.value
                    ]
                    
                    logger.info(f"📤 Enviando {len(active_orders)} órdenes activas a Mesa {table_id}")
                    for order in active_orders:
                        # Mapear estados a lenguaje nativo
                        status_map = {
                            "PENDING": "EN COLA",
                            "PREPARING": "PREPARANDO",
                            "READY": "LISTO",
                            "DELIVERED": "ENTREGADO"
                        }
                        
                        await websocket.send_json({
                            "event": "order_new",
                            "data": {
                                "order_id": order["id"],
                                "table_id": int(table_id) if table_id else 0,
                                "status": status_map.get(order["status"], order["status"]),
                                "progress": 100 if order["status"] == "READY" else 0,
                                "items": [
                                    {
                                        "id": i["id"],
                                        "name": i["product"]["name"], 
                                        "qty": i["quantity"],
                                        "status": status_map.get(i["status"], i["status"])
                                    } for i in order["items"]
                                ]
                            }
                        })

                elif action == "call_waiter":
                    await trigger_broadcast("dashboard_stats")
                    await websocket.send_json({"event": "msg", "data": {"message": "Mesero en camino"}})

                elif action == "request_bill":
                    await trigger_broadcast("dashboard_stats") 
                    await websocket.send_json({"event": "msg", "data": {"message": "Solicitando cuenta..."}})
                    logger.info(f"🧾 Mesa {table_id} solicitó la cuenta")

                elif action == "clear_table":
                    from pos_core.tables.service import vacate_table_service
                    await vacate_table_service(db, table_id)
                    await trigger_broadcast("tables")  # Notificar al POS central la actualización de mesas
                    logger.info(f"🧹 Mesa {table_id} liberada desde TablePad")

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
