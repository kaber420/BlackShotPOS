"""
Servicio central de notificaciones en tiempo real.
Se encarga de obtener datos frescos de la BD y despacharlos vía el PubSubManager.
"""
from pos_core.database import get_session
from typing import Any
from .manager import pos_broadcaster, iot_broadcaster
import logging

logger = logging.getLogger(__name__)

async def trigger_broadcast(topic: str, data: Any = None):
    """
    Despacha actualizaciones de un tópico de POS. Solo consulta la BD si no se proveen datos.
    """
    if topic not in pos_broadcaster.active_connections or not pos_broadcaster.active_connections[topic]:
        return

    if data is not None:
        await pos_broadcaster.broadcast(topic, data)
        return

    async for db in get_session():
        try:
            data = None
            
            if topic == "kitchen_orders":
                from pos_core.sales.service import get_kitchen_orders
                data = await get_kitchen_orders(db)
                
            elif topic == "dashboard_stats":
                from pos_core.sales.service import get_dashboard_stats
                data = await get_dashboard_stats(db)
                
            elif topic == "recent_orders":
                from pos_core.sales.service import get_orders_json
                data = await get_orders_json(db)
                # Ordenar por fecha de creación descendente (más recientes primero)
                data = sorted(data, key=lambda x: x["created_at"], reverse=True)
                
            elif topic == "tables":
                from pos_core.tables.service import get_tables
                tables = await get_tables(db, include_inactive=True)
                # Serializamos a dict mediante model_dump
                data = [t.model_dump(mode="json") for t in tables]

            if data is not None:
                await pos_broadcaster.broadcast(topic, data)
                
        except Exception as e:
            logger.error(f"❌ Error al procesar trigger_broadcast para '{topic}': {e}", exc_info=True)
        finally:
            break

async def trigger_all_broadcasts():
    """Dispara actualizaciones para todos los tópicos conocidos."""
    for topic in ["kitchen_orders", "dashboard_stats", "recent_orders", "tables"]:
        await trigger_broadcast(topic)

async def trigger_iot_broadcast(table_id: int, event: str, message: str, eta: int = 0, data: Any = None):
    """
    Despacha una notificación a los dispositivos IoT (ESP32) de forma totalmente independiente.
    """
    topic = f"iot_table_{table_id}"
    # Si no hay nadie escuchando en la mesa, no perdemos tiempo
    if topic not in iot_broadcaster.active_connections or not iot_broadcaster.active_connections[topic]:
        return

    if data:
        payload = data
    else:
        from pos_core.iot.service import format_iot_payload
        payload = format_iot_payload(event, message, eta)
    
    await iot_broadcaster.broadcast(topic, payload)
