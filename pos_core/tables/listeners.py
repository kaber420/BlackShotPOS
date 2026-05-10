import logging
from datetime import datetime, timezone
from pos_core.events.bus import on_event
from pos_core.database import async_session_maker
from .models import Table
from .service import vacate_table_service

logger = logging.getLogger(__name__)

@on_event("sales.order_created")
async def on_order_created(payload: dict, metadata: dict):
    """
    Cuando se crea una orden, si tiene mesa, la marca como Ocupada.
    """
    table_id = payload.get("table_id")
    if not table_id:
        return

    async with async_session_maker() as session:
        try:
            db_table = await session.get(Table, table_id)
            if db_table and db_table.status != "Occupied":
                db_table.status = "Occupied"
                db_table.occupied_at = datetime.now(timezone.utc)
                session.add(db_table)
                await session.commit()
                logger.info(f"📍 Mesa {db_table.number} marcada como OCUPADA por orden {payload.get('order_id')}")
                
                # Opcional: Disparar broadcast de UI para actualizar el mapa de mesas
                from pos_core.events.service import trigger_broadcast
                await trigger_broadcast("tables", db=session)
        except Exception as e:
            logger.error(f"❌ Error al ocupar mesa {table_id} vía evento: {e}")

@on_event("sales.order_status_changed")
async def on_order_status_changed(payload: dict, metadata: dict):
    """
    Si una orden se cancela, libera la mesa.
    """
    new_status = payload.get("new_status")
    table_id = payload.get("table_id")
    
    # Aquí podríamos importar OrderStatus, pero para evitar acoplamiento usamos el string/valor
    if new_status == "CANCELLED" and table_id:
        async with async_session_maker() as session:
            try:
                await vacate_table_service(session, table_id)
                logger.info(f"📍 Mesa {table_id} LIBERADA por cancelación de orden {payload.get('order_id')}")
                
                from pos_core.events.service import trigger_broadcast
                await trigger_broadcast("tables", db=session)
            except Exception as e:
                logger.error(f"❌ Error al liberar mesa {table_id} por cancelación: {e}")

@on_event("sales.order_deleted")
async def on_order_deleted(payload: dict, metadata: dict):
    """
    Si una orden vacía se elimina, libera la mesa.
    """
    table_id = payload.get("table_id")
    if table_id:
        async with async_session_maker() as session:
            try:
                await vacate_table_service(session, table_id)
                logger.info(f"📍 Mesa {table_id} LIBERADA por eliminación de orden")
                
                from pos_core.events.service import trigger_broadcast
                await trigger_broadcast("tables", db=session)
            except Exception as e:
                logger.error(f"❌ Error al liberar mesa {table_id} por eliminación: {e}")

@on_event("sales.payment_received")
async def on_payment_received(payload: dict, metadata: dict):
    """
    Si el pago indica 'vacate_table', liberamos la mesa.
    """
    vacate_table = payload.get("vacate_table", False)
    table_id = payload.get("table_id")
    
    if vacate_table and table_id:
        async with async_session_maker() as session:
            try:
                await vacate_table_service(session, table_id)
                logger.info(f"📍 Mesa {table_id} LIBERADA vía evento de pago (vacate_table=True)")
                
                from pos_core.events.service import trigger_broadcast
                await trigger_broadcast("tables", db=session)
            except Exception as e:
                logger.error(f"❌ Error al liberar mesa {table_id} por pago: {e}")

@on_event("sales.order_transferred")
async def on_order_transferred(payload: dict, metadata: dict):
    """
    Maneja el cambio de estado de mesas cuando una orden se transfiere.
    """
    old_table_id = payload.get("from_table_id")
    new_table_id = payload.get("to_table_id")
    
    async with async_session_maker() as session:
        try:
            occupied_at = None
            # 1. Liberar mesa vieja
            if old_table_id:
                old_table = await session.get(Table, old_table_id)
                if old_table:
                    occupied_at = old_table.occupied_at
                    old_table.status = "Free"
                    old_table.occupied_at = None
                    session.add(old_table)
            
            # 2. Ocupar mesa nueva
            if new_table_id:
                new_table = await session.get(Table, new_table_id)
                if new_table:
                    new_table.status = "Occupied"
                    # Preservamos el tiempo de ocupación si venía de otra mesa
                    new_table.occupied_at = occupied_at if occupied_at else datetime.now(timezone.utc)
                    session.add(new_table)
            
            await session.commit()
            logger.info(f"📍 Transferencia de mesa completada: {old_table_id} -> {new_table_id}")
            
            from pos_core.events.service import trigger_broadcast
            await trigger_broadcast("tables", db=session)
        except Exception as e:
            logger.error(f"❌ Error en transferencia de mesa vía evento: {e}")
