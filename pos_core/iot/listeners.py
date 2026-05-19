import logging
from pos_core.events.bus import on_event
from pos_core.events.service import trigger_iot_broadcast

logger = logging.getLogger(__name__)

# Mapeos de estados amigables para dispositivos IoT (TablePads)
IOT_STATUS_STRINGS = {
    "PENDING": "EN COLA",
    "PREPARING": "PREPARANDO",
    "READY": "LISTO",
    "DELIVERED": "ENTREGADO",
    "CANCELLED": "CANCELADO",
}

@on_event("tables.vacated")
async def on_table_vacated(payload: dict, metadata: dict):
    """Limpia el TablePad cuando la mesa se libera."""
    table_id = payload.get("table_id")
    if table_id:
        logger.info(f"📡 [IoT EDA] Mesa {table_id} vaciada. Notificando reset al hardware.")
        await trigger_iot_broadcast(table_id, "clear_table", "Mesa libre", data={})

@on_event("tables.status_changed")
async def on_table_status_changed(payload: dict, metadata: dict):
    """Bloquea o actualiza el TablePad según el estado de la mesa."""
    table_id = payload.get("table_id")
    new_status = payload.get("new_status")
    
    if not table_id:
        return

    if new_status == "Reserved":
        logger.info(f"📡 [IoT EDA] Mesa {table_id} RESERVADA. Notificando bloqueo al hardware.")
        await trigger_iot_broadcast(table_id, "lock_table", "MESA RESERVADA", data={"locked": True})
    elif new_status == "Free":
        # A veces status_changed se usa en lugar de vacated
        await trigger_iot_broadcast(table_id, "clear_table", "Mesa libre", data={})

@on_event("sales.order_created")
async def on_order_created(payload: dict, metadata: dict):
    """Inicializa la vista de orden en el TablePad."""
    table_id = payload.get("table_id")
    order_id = payload.get("order_id")
    
    if table_id:
        logger.info(f"📡 [IoT EDA] Nueva orden {order_id} para mesa {table_id}. Notificando hardware.")
        await trigger_iot_broadcast(
            table_id, 
            "order_new", 
            "Orden recibida", 
            data={
                "order_id": order_id,
                "status": "EN COLA",
                "progress": 0
            }
        )

@on_event("kitchen.item_preparing")
async def on_item_preparing(payload: dict, metadata: dict):
    """Actualiza el progreso en el TablePad al iniciar preparación."""
    order_id = payload.get("order_id")
    # Necesitamos encontrar la mesa asociada a la orden
    # Para evitar acoplamiento con la DB aquí, el evento de cocina DEBERÍA incluir la table_id
    # Si no la incluye, tendríamos que buscarla o el evento debería ser enriquecido.
    # Vamos a verificar si KitchenTicket tiene table_id. Sí lo tiene.
    
    # Si el evento no trae table_id, podemos intentar obtenerlo de la orden
    table_id = payload.get("table_id")
    
    if not table_id:
        # Fallback: Algunos eventos podrían no traerlo. 
        # Pero según KitchenService.update_ticket_status, no lo estamos pasando.
        # DEBO modificar KitchenService para que lo pase.
        return

    logger.info(f"📡 [IoT EDA] Item preparando para orden {order_id} (Mesa {table_id}).")
    await trigger_iot_broadcast(
        table_id,
        "order_update",
        "Preparando...",
        data={
            "order_id": order_id,
            "status": "PREPARANDO",
            "progress": 50
        }
    )

@on_event("kitchen.item_ready")
async def on_item_ready(payload: dict, metadata: dict):
    """Notifica al cliente que su pedido está listo."""
    table_id = payload.get("table_id")
    order_id = payload.get("order_id")
    product_name = payload.get("product_name", "Pedido")

    if table_id:
        logger.info(f"📡 [IoT EDA] ¡Item LISTO! Mesa {table_id}, Orden {order_id}.")
        await trigger_iot_broadcast(
            table_id,
            "order_ready",
            f"¡{product_name} LISTO!",
            data={
                "order_id": order_id,
                "status": "LISTO",
                "progress": 100
            }
        )

@on_event("sales.order_cancelled")
async def on_order_cancelled(payload: dict, metadata: dict):
    """Informa de la cancelación y resetea el dispositivo."""
    table_id = payload.get("table_id")
    order_id = payload.get("order_id")

    if table_id:
        logger.info(f"📡 [IoT EDA] Orden {order_id} CANCELADA. Notificando hardware.")
        await trigger_iot_broadcast(
            table_id,
            "order_cancelled",
            "Orden Cancelada",
            data={
                "order_id": order_id,
                "status": "CANCELADO"
            }
        )

# --- BROADCAST TRIGGERS (Traducción de Eventos a UI Web) ---

@on_event("iot.waiter_requested")
async def on_waiter_requested(payload: dict, metadata: dict):
    """Traduce la solicitud del hardware a una actualización de la UI Dashboard."""
    from pos_core.events.service import trigger_broadcast
    from pos_core.database import async_session_maker
    from pos_core.tables.models import Table
    
    table_id = payload.get("table_id")
    if table_id:
        async with async_session_maker() as session:
            try:
                db_table = await session.get(Table, table_id)
                if db_table:
                    db_table.waiter_requested = True
                    session.add(db_table)
                    await session.commit()
                    await trigger_broadcast("tables")
                    logger.info(f"🔔 Solicitud de mesero registrada para Mesa {table_id}")
            except Exception as e:
                logger.error(f"❌ Error al marcar waiter_requested para mesa {table_id}: {e}")

    await trigger_broadcast("dashboard_stats")
    logger.info(f"🔔 Solicitud de mesero desde IoT (Mesa {payload.get('table_id')}) enviada a Dashboard.")

@on_event("iot.bill_requested")
async def on_bill_requested(payload: dict, metadata: dict):
    """Traduce la solicitud de cuenta a una actualización de la UI Dashboard."""
    from pos_core.events.service import trigger_broadcast
    from pos_core.database import async_session_maker
    from pos_core.tables.models import Table
    
    table_id = payload.get("table_id")
    if table_id:
        async with async_session_maker() as session:
            try:
                db_table = await session.get(Table, table_id)
                if db_table:
                    db_table.bill_requested = True
                    session.add(db_table)
                    await session.commit()
                    await trigger_broadcast("tables")
                    logger.info(f"🔔 Solicitud de cuenta registrada para Mesa {table_id}")
            except Exception as e:
                logger.error(f"❌ Error al marcar bill_requested para mesa {table_id}: {e}")

    await trigger_broadcast("dashboard_stats")
    logger.info(f"🔔 Solicitud de cuenta desde IoT (Mesa {payload.get('table_id')}) enviada a Dashboard.")

@on_event("tables.vacated")
async def trigger_ui_tables_on_vacated(payload: dict, metadata: dict):
    """Asegura que la UI Web se actualice cuando se libera una mesa."""
    from pos_core.events.service import trigger_broadcast
    await trigger_broadcast("tables")

@on_event("tables.status_changed")
async def trigger_ui_tables_on_status_changed(payload: dict, metadata: dict):
    """Asegura que la UI Web se actualice cuando cambia el estado de una mesa."""
    from pos_core.events.service import trigger_broadcast
    await trigger_broadcast("tables")
