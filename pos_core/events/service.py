"""
Servicio central de notificaciones en tiempo real.
Se encarga de obtener datos frescos de la BD y despacharlos vía el PubSubManager.
"""
from pos_core.database import get_session
from typing import Any, Optional
from .manager import pos_broadcaster, iot_broadcaster
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from pos_core.sales.models import OrderStatus

logger = logging.getLogger(__name__)

# Mapeos de estados amigables para dispositivos IoT (TablePads)
IOT_STATUS_STRINGS = {
    OrderStatus.PENDING: "EN COLA",
    OrderStatus.PREPARING: "PREPARANDO",
    OrderStatus.READY: "LISTO",
    OrderStatus.DELIVERED: "ENTREGADO",
    OrderStatus.PAID: "PAGADO",
    OrderStatus.CANCELLED: "CANCELADO",
}

IOT_STATUS_PROGRESS = {
    OrderStatus.PENDING: 0,
    OrderStatus.PREPARING: 50,
    OrderStatus.READY: 100,
    OrderStatus.DELIVERED: 100,
    OrderStatus.PAID: 100,
    OrderStatus.CANCELLED: 0,
}


async def _fetch_topic_data(topic: str, db: AsyncSession) -> Optional[Any]:
    """
    Obtiene los datos actuales de la BD para un tópico POS dado.
    Función interna compartida por trigger_broadcast y get_initial_snapshot.
    NO toca el canal IoT.
    """
    from pos_core.sales.schemas import OrderRead

    if topic == "kitchen_orders":
        from pos_core.sales.services.order_lifecycle_service import get_kitchen_orders
        orders = await get_kitchen_orders(db)
        return [OrderRead.model_validate(o).model_dump(mode="json") for o in orders]

    elif topic == "recent_orders":
        from pos_core.sales.services.order_lifecycle_service import get_orders
        orders = await get_orders(db)
        data = [OrderRead.model_validate(o).model_dump(mode="json") for o in orders]
        return sorted(data, key=lambda x: x["created_at"], reverse=True)

    elif topic == "dashboard_stats":
        from pos_core.analytics.service import get_dashboard_stats
        return await get_dashboard_stats(db)

    elif topic == "tables":
        from pos_core.tables.service import get_tables
        tables = await get_tables(db, include_inactive=True)
        return [t.model_dump(mode="json") for t in tables]

    elif topic == "inventory":
        from pos_core.inventory.services.ingredient_service import get_ingredients
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


async def trigger_broadcast(topic: str, data: Any = None, db: Optional[AsyncSession] = None):
    """
    Despacha actualizaciones de un tópico POS. Solo consulta la BD si no se proveen datos.
    Implementa Dual-Dispatch: Si el cambio afecta a una mesa, notifica también al canal IoT.
    """
    # 1. Obtener los datos si no se proveyeron
    result = data
    if result is None:
        if db is not None:
            try:
                result = await _fetch_topic_data(topic, db)
            except Exception as e:
                logger.error(f"❌ Error al procesar trigger_broadcast con sesión para '{topic}': {e}", exc_info=True)
                return
        else:
            # Fallback: abrir sesión si no se provee una
            async for db_session in get_session():
                try:
                    result = await _fetch_topic_data(topic, db_session)
                except Exception as e:
                    logger.error(f"❌ Error al procesar trigger_broadcast para '{topic}': {e}", exc_info=True)
                break

    if result is None:
        return

    # 2. Despacho POS (Web)
    if topic in pos_broadcaster.active_connections and pos_broadcaster.active_connections[topic]:
        await pos_broadcaster.broadcast(topic, result)

    # 3. Despacho IoT (Dual-Dispatch)
    await _map_and_dispatch_iot(topic, result)


async def _map_and_dispatch_iot(topic: str, data: Any):
    """
    Analiza los datos de un tópico POS y despacha notificaciones ligeras a los 
    dispositivos IoT correspondientes si aplica.
    """
    if topic == "tables":
        # 'data' es una lista de dicts de mesas
        for table in data:
            table_id = table.get("id")
            if not table_id:
                continue
            
            # Si la mesa está libre, limpiamos el TablePad
            if not table.get("is_occupied"):
                await trigger_iot_broadcast(table_id, "clear_table", "", data={})
            else:
                # Si está ocupada pero no tenemos detalle de orden aquí, 
                # enviamos un estado genérico. Generalmente tables se actualiza 
                # junto con kitchen_orders, que da más detalle.
                pass

    elif topic == "kitchen_orders":
        # 'data' es una lista de dicts de órdenes
        # Agrupamos por mesa para no saturar con múltiples mensajes si hay varias órdenes (raro pero posible)
        for order in data:
            table_id = order.get("table_id")
            if not table_id:
                continue
            
            status_raw = order.get("status")
            status_str = IOT_STATUS_STRINGS.get(status_raw, str(status_raw))
            progress = IOT_STATUS_PROGRESS.get(status_raw, 0)
            
            await trigger_iot_broadcast(
                table_id, 
                "order_update", 
                "", 
                data={
                    "order_id": order.get("id"),
                    "status": status_str,
                    "progress": progress
                }
            )


async def trigger_standard_broadcasts():
    """Dispara actualizaciones para los tópicos POS estándar (Cocina, Recientes, Stats, Mesas)."""
    async for db in get_session():
        for topic in ["kitchen_orders", "recent_orders", "dashboard_stats", "tables"]:
            await trigger_broadcast(topic, db=db)
        break


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
