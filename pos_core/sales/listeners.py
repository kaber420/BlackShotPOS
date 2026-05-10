import logging
from pos_core.events.bus import on_event
from pos_core.database import async_session_maker
from .models import OrderStatus
from .repository import item_repo, order_repo

logger = logging.getLogger(__name__)

@on_event("kitchen.item_preparing")
async def on_kitchen_item_preparing(payload: dict, metadata: dict):
    """
    Cuando la cocina empieza a preparar un ítem, actualizamos el estado en Ventas.
    """
    order_id = payload.get("order_id")
    item_id = payload.get("item_id")
    
    async with async_session_maker() as session:
        try:
            item = await item_repo.get_by_id(session, order_id, item_id)
            if item and item.status != OrderStatus.PREPARING:
                item.status = OrderStatus.PREPARING
                await session.commit()
                logger.debug(f"👨‍🍳 Item {item_id} marcado como PREPARING en Sales (desde Cocina)")
        except Exception as e:
            logger.error(f"❌ Error en listener de Sales para kitchen.item_preparing: {e}")

@on_event("kitchen.item_ready")
async def on_kitchen_item_ready(payload: dict, metadata: dict):
    """
    Cuando la cocina marca un ítem como listo, actualizamos el estado comercial en Ventas.
    """
    order_id = payload.get("order_id")
    item_id = payload.get("item_id")
    
    async with async_session_maker() as session:
        try:
            item = await item_repo.get_by_id(session, order_id, item_id)
            if not item:
                logger.error(f"❌ Item {item_id} no encontrado en Sales para orden {order_id}")
                return
                
            item.status = OrderStatus.READY
            await session.commit()
            logger.info(f"✅ Item {item_id} marcado como READY en Sales (desde Cocina)")
            
            # Verificar si toda la orden está lista
            order_items = await item_repo.get_items_for_order(session, order_id)
            all_ready = all(i.status in (OrderStatus.READY, OrderStatus.DELIVERED, OrderStatus.CANCELLED) for i in order_items)
            
            if all_ready:
                order = await order_repo.get_by_id(session, order_id)
                if order and order.status != OrderStatus.READY:
                    order.status = OrderStatus.READY
                    await session.commit()
                    logger.info(f"🎉 Orden {order_id} marcada como READY (Todos los ítems listos)")
                    
                    # Notificar via IoT/WS
                    from pos_core.events.service import trigger_iot_broadcast
                    if order.table_id:
                        await trigger_iot_broadcast(
                            order.table_id, "order_update", "",
                            data={"order_id": order.id, "status": "LISTO", "progress": 100},
                        )
        except Exception as e:
            logger.error(f"❌ Error en listener de Sales para kitchen.item_ready: {e}")
