"""
Servicio central de notificaciones en tiempo real.
Se encarga de obtener datos frescos de la BD y despacharlos vía el PubSubManager.
"""
from pos_core.database import get_session
from .manager import broadcaster
import logging

logger = logging.getLogger(__name__)

async def trigger_broadcast(topic: str):
    """
    Función orquestadora para despachar actualizaciones de un tópico específico.
    """
    if topic not in broadcaster.active_connections or not broadcaster.active_connections[topic]:
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
                await broadcaster.broadcast(topic, data)
                
        except Exception as e:
            logger.error(f"❌ Error al procesar trigger_broadcast para '{topic}': {e}", exc_info=True)
        finally:
            break

async def trigger_all_broadcasts():
    """Dispara actualizaciones para todos los tópicos conocidos."""
    for topic in ["kitchen_orders", "dashboard_stats", "recent_orders", "tables"]:
        await trigger_broadcast(topic)
