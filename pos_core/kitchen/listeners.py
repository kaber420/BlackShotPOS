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
