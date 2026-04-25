"""
Servicio central de notificaciones en tiempo real.
Se encarga de obtener datos frescos de la BD y despacharlos vía el PubSubManager.
"""
from pos_core.database import get_session
from typing import Any, Optional
from .manager import pos_broadcaster, iot_broadcaster
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)


async def _fetch_topic_data(topic: str, db: AsyncSession) -> Optional[Any]:
    """
    Obtiene los datos actuales de la BD para un tópico POS dado.
    Función interna compartida por trigger_broadcast y get_initial_snapshot.
    NO toca el canal IoT.
    """
    from pos_core.sales.schemas import OrderRead

    if topic == "kitchen_orders":
        from pos_core.sales.order_service import get_kitchen_orders
        orders = await get_kitchen_orders(db)
        return [OrderRead.model_validate(o).model_dump(mode="json") for o in orders]

    elif topic == "recent_orders":
        from pos_core.sales.order_service import get_orders
        orders = await get_orders(db)
        data = [OrderRead.model_validate(o).model_dump(mode="json") for o in orders]
        return sorted(data, key=lambda x: x["created_at"], reverse=True)

    elif topic == "dashboard_stats":
        from pos_core.sales.analytics_service import get_dashboard_stats
        return await get_dashboard_stats(db)

    elif topic == "tables":
        from pos_core.tables.service import get_tables
        tables = await get_tables(db, include_inactive=True)
        return [t.model_dump(mode="json") for t in tables]

    elif topic == "inventory":
        from pos_core.inventory.service import get_ingredients
        from pos_core.inventory.models import Ingredient
        ingredients = await get_ingredients(db)
        return [i.model_dump(mode="json") for i in ingredients]

    elif topic == "admin_iot":
        from pos_core.iot.service import get_all_devices
        devices = await get_all_devices(db)
        return [d.model_dump(mode="json") for d in devices]

    return None


async def get_initial_snapshot(topic: str, db: AsyncSession) -> Optional[Any]:
    """
    Retorna el snapshot inicial de datos para un tópico POS.
    Llamar al suscribir un cliente para que reciba el estado actual inmediatamente.
    """
    try:
        return await _fetch_topic_data(topic, db)
    except Exception as e:
        logger.error(f"❌ Error al obtener snapshot inicial para '{topic}': {e}", exc_info=True)
        return None


async def trigger_broadcast(topic: str, data: Any = None):
    """
    Despacha actualizaciones de un tópico POS. Solo consulta la BD si no se proveen datos.
    NO toca el canal IoT.
    """
    if topic not in pos_broadcaster.active_connections or not pos_broadcaster.active_connections[topic]:
        return

    if data is not None:
        await pos_broadcaster.broadcast(topic, data)
        return

    async for db in get_session():
        try:
            result = await _fetch_topic_data(topic, db)
            if result is not None:
                await pos_broadcaster.broadcast(topic, result)
        except Exception as e:
            logger.error(f"❌ Error al procesar trigger_broadcast para '{topic}': {e}", exc_info=True)
        break


async def trigger_all_broadcasts():
    """Dispara actualizaciones para todos los tópicos POS conocidos."""
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
        payload = {"event": event, "data": data}
    else:
        from pos_core.iot.service import format_iot_payload
        payload = format_iot_payload(event, message, eta)
    
    await iot_broadcaster.broadcast(topic, payload)
