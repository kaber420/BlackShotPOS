"""
Servicio central de notificaciones en tiempo real.
Se encarga de obtener datos frescos de la BD y despacharlos vía el PubSubManager.
"""
from pos_core.database import get_session
from typing import Any, Optional
from .manager import pos_broadcaster, iot_broadcaster
from .registry import get_provider, list_registered_topics
from .iot_registry import get_iot_mapper
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from pos_core.sales.models import OrderStatus

logger = logging.getLogger(__name__)




async def _fetch_topic_data(topic: str, db: AsyncSession) -> Optional[Any]:
    """
    Obtiene los datos actuales de la BD para un tópico POS dado usando el registro.
    """
    provider = get_provider(topic)
    if not provider:
        logger.warning(f"❓ No hay proveedor registrado para el tópico: {topic}")
        return None
    
    try:
        return await provider(db)
    except Exception as e:
        logger.error(f"❌ Error al ejecutar proveedor para '{topic}': {e}", exc_info=True)
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
    Despacha notificaciones a IoT usando el mapeador registrado para el tópico.
    """
    mapper = get_iot_mapper(topic)
    if mapper:
        try:
            await mapper(topic, data)
        except Exception as e:
            logger.error(f"❌ Error en mapeador IoT para '{topic}': {e}", exc_info=True)


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
