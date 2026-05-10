import logging
from pos_core.events.bus import on_event
from pos_core.database import async_session_maker
from .services import create_tickets_for_order
from .repository import kitchen_repo
from .models import KitchenStatus

logger = logging.getLogger(__name__)

@on_event("sales.order_created")
async def on_order_created(payload: dict, metadata: dict):
    """
    Cuando se crea una orden, verificamos si ya viene con items (poco probable en el POS actual)
    o simplemente registramos el interés.
    """
    order_id = payload.get("order_id")
    logger.debug(f"🔔 Orden {order_id} creada. Cocina a la espera de items.")

@on_event("sales.items_added")
async def on_items_added(payload: dict, metadata: dict):
    """
    Reacciona cuando se añaden items a una orden.
    Payload esperado: {"order_id": int, "items": [{"id": int, "product_id": int, ...}]}
    """
    order_id = payload.get("order_id")
    items = payload.get("items", [])
    
    if not items:
        return
        
    async with async_session_maker() as session:
        try:
            # Filtramos el payload para evitar colisión con argumentos ya pasados
            extra_metadata = {k: v for k, v in payload.items() if k not in ["order_id", "items"]}
            await create_tickets_for_order(session, order_id, items, **extra_metadata)
            logger.info(f"👨‍🍳 Tickets de cocina generados para orden {order_id}")
        except Exception as e:
            logger.error(f"❌ Error al crear tickets de cocina para orden {order_id}: {e}", exc_info=True)

@on_event("sales.order_cancelled")
async def on_order_cancelled(payload: dict, metadata: dict):
    """
    Cancela todos los tickets asociados a una orden si esta se cancela.
    """
    order_id = payload.get("order_id")
    async with async_session_maker() as session:
        try:
            tickets = await kitchen_repo.get_tickets_by_order(session, order_id)
            for t in tickets:
                if t.status not in (KitchenStatus.READY, KitchenStatus.DELIVERED):
                    t.status = KitchenStatus.CANCELLED
            await session.commit()
            logger.info(f"🚫 Tickets de cocina cancelados para orden {order_id}")
        except Exception as e:
            logger.error(f"❌ Error al cancelar tickets de cocina: {e}")


@on_event("sales.item_cancelled")
async def on_item_cancelled(payload: dict, metadata: dict):
    """
    Cancela el ticket de cocina asociado a un item si este se cancela en ventas.
    """
    item_id = payload.get("item_id")
    async with async_session_maker() as session:
        try:
            ticket = await kitchen_repo.get_ticket_by_item_id(session, item_id)
            if ticket and ticket.status not in (KitchenStatus.READY, KitchenStatus.DELIVERED):
                ticket.status = KitchenStatus.CANCELLED
                await session.commit()
                logger.info(f"🚫 Ticket de cocina cancelado para ítem {item_id}")
                
                # Notificar UI
                from pos_core.events.service import trigger_standard_broadcasts
                await trigger_standard_broadcasts()
        except Exception as e:
            logger.error(f"❌ Error al cancelar ticket de item {item_id}: {e}")

@on_event("sales.order_transferred")
async def on_order_transferred(payload: dict, metadata: dict):
    """
    Actualiza la mesa en todos los tickets de una orden cuando esta se transfiere.
    """
    order_id = payload.get("order_id")
    new_table_id = payload.get("to_table_id")
    
    async with async_session_maker() as session:
        try:
            tickets = await kitchen_repo.get_tickets_by_order(session, order_id)
            for t in tickets:
                t.table_id = new_table_id
            
            await session.commit()
            logger.info(f"📍 Mesa actualizada en {len(tickets)} tickets para orden {order_id}")
            
            # Notificar UI
            from pos_core.events.service import trigger_standard_broadcasts
            await trigger_standard_broadcasts()
        except Exception as e:
            logger.error(f"❌ Error al transferir tickets de cocina: {e}")

@on_event("sales.order_split")
async def on_order_split(payload: dict, metadata: dict):
    """
    Actualiza el order_id en los tickets de cocina cuando se divide una orden.
    """
    new_order_id = payload.get("new_order_id")
    items_split = payload.get("items_split", []) # [{"item_id": int, ...}]
    
    async with async_session_maker() as session:
        try:
            count = 0
            for split_info in items_split:
                item_id = split_info.get("item_id")
                ticket = await kitchen_repo.get_ticket_by_item_id(session, item_id)
                if ticket:
                    ticket.order_id = new_order_id
                    count += 1
            
            await session.commit()
            logger.info(f"🔀 {count} tickets de cocina movidos a la nueva orden {new_order_id}")
            
            # Notificar UI
            from pos_core.events.service import trigger_standard_broadcasts
            await trigger_standard_broadcasts()
        except Exception as e:
            logger.error(f"❌ Error al procesar split en cocina: {e}")

@on_event("sales.item_status_changed")
async def on_item_status_changed(payload: dict, metadata: dict):
    """
    Sincroniza estados comerciales con estados de cocina.
    Especialmente útil para marcar como DELIVERED si se hace desde ventas.
    """
    item_id = payload.get("item_id")
    new_status = payload.get("new_status")
    
    if new_status == "DELIVERED":
        async with async_session_maker() as session:
            try:
                ticket = await kitchen_repo.get_ticket_by_item_id(session, item_id)
                if ticket and ticket.status != KitchenStatus.DELIVERED:
                    ticket.status = KitchenStatus.DELIVERED
                    await session.commit()
                    logger.info(f"🚚 Ticket de cocina marcado como ENTREGADO para ítem {item_id}")
                    
                    # Notificar UI
                    from pos_core.events.service import trigger_standard_broadcasts
                    await trigger_standard_broadcasts()
            except Exception as e:
                logger.error(f"❌ Error al sincronizar entrega en cocina: {e}")

