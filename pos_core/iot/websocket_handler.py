import logging
from fastapi import WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from pos_core.events.manager import pos_broadcaster, iot_broadcaster
from pos_core.events.service import trigger_broadcast
from pos_core.settings.service import get_settings
from .service import update_device_last_seen, update_device_health
from pos_core.events.bus import event_bus

logger = logging.getLogger(__name__)

# Mapeos de estados nativos para hardware IoT
IOT_STATUS_MAP = {
    "PENDING": "EN COLA",
    "PREPARING": "PREPARANDO",
    "READY": "LISTO",
    "DELIVERED": "ENTREGADO"
}

async def handle_iot_session(websocket: WebSocket, db: AsyncSession, device: any):
    """
    Maneja el ciclo de vida completo de un dispositivo IoT conectado vía WebSocket.
    """
    table_id = device.table_id
    device_id = device.id
    topic = f"iot_table_{table_id}"
    
    # 1. Suscripción y Notificación de Estado Online
    iot_broadcaster.connect(websocket, topic)
    await pos_broadcaster.broadcast("admin_iot", {
        "type": "status",
        "device_id": device_id,
        "status": "online"
    })

    # 2. Configuración Inicial (Zero-Config)
    try:
        settings = await get_settings(db)
        await websocket.send_json({
            "event": "config",
            "data": {
                "business_name": settings.name,
                "device_name": device.name or f"Mesa {table_id}",
                "table_id": int(table_id) if table_id else 0
            }
        })
    except Exception as e:
        logger.error(f"⚠️ Error al enviar config inicial a IoT {device_id}: {e}")

    # 3. Bucle de Comunicación Principal
    try:
        await update_device_last_seen(db, device_id)
        
        while True:
            data = await websocket.receive_json()
            action = data.get("action")
            payload = data.get("data") or data.get("payload") or {}
            
            if action == "ping":
                await websocket.send_json({"event": "pong"})
                await update_device_last_seen(db, device_id)
            
            elif action in ["health", "heartbeat"]:
                await _handle_health_report(db, device_id, data, payload)
            
            elif action == "sync_orders":
                await _handle_sync_orders(websocket, db, table_id)

            elif action == "call_waiter":
                await event_bus.publish("iot.waiter_requested", {"table_id": table_id, "device_id": device_id})
                await websocket.send_json({"event": "msg", "data": {"message": "Mesero en camino"}})

            elif action == "request_bill":
                await event_bus.publish("iot.bill_requested", {"table_id": table_id, "device_id": device_id})
                await websocket.send_json({"event": "msg", "data": {"message": "Solicitando cuenta..."}})

            elif action == "clear_table":
                await event_bus.publish("iot.clear_table_requested", {
                    "table_id": table_id,
                    "device_id": device_id
                })
                logger.info(f"🧹 Evento clear_table_requested emitido para Mesa {table_id} desde TablePad")

    except WebSocketDisconnect:
        logger.info(f"🔌 Dispositivo IoT desconectado: {device.device_id}")
        await pos_broadcaster.broadcast("admin_iot", {
            "type": "status",
            "device_id": device_id,
            "status": "offline"
        })
    except Exception as e:
        logger.error(f"❌ Error crítico en sesión IoT {device_id}: {e}")
    finally:
        iot_broadcaster.disconnect(websocket, topic)

async def _handle_health_report(db, device_id, data, payload):
    rssi = payload.get("rssi") if isinstance(payload, dict) else data.get("rssi")
    battery = payload.get("battery") if isinstance(payload, dict) else data.get("battery")
    free_heap = payload.get("free_heap") if isinstance(payload, dict) else data.get("free_heap")
    
    await update_device_health(db, device_id, rssi=rssi, battery=battery)
    await pos_broadcaster.broadcast("admin_iot", {
        "type": "health",
        "device_id": device_id,
        "rssi": rssi,
        "battery": battery,
        "free_heap": free_heap
    })

async def _handle_sync_orders(websocket, db, table_id):
    from pos_core.sales.services.order_lifecycle_service import get_orders
    from pos_core.sales.schemas import OrderRead
    from pos_core.sales.models import OrderStatus

    raw_orders = await get_orders(db)
    order_dicts = [OrderRead.model_validate(o).model_dump(mode="json") for o in raw_orders]
    active_orders = [
        o for o in order_dicts
        if o["table_id"] == table_id
        and o["status"] not in [OrderStatus.CANCELLED.value, OrderStatus.PAID.value]
    ]
    
    for order in active_orders:
        await websocket.send_json({
            "event": "order_new",
            "data": {
                "order_id": order["id"],
                "table_id": int(table_id) if table_id else 0,
                "status": IOT_STATUS_MAP.get(order["status"], order["status"]),
                "progress": 100 if order["status"] == "READY" else 0,
                "items": [
                    {
                        "id": i["id"],
                        "name": i["product"]["name"], 
                        "qty": i["quantity"],
                        "status": IOT_STATUS_MAP.get(i["status"], i["status"])
                    } for i in order["items"]
                ]
            }
        })
