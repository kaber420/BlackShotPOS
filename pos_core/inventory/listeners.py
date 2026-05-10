import logging
from pos_core.events.bus import on_event
from pos_core.database import async_session_maker
from pos_core.inventory.services.stock_service import process_inventory_depletion

logger = logging.getLogger(__name__)

@on_event("sales.payment_received")
async def on_payment_received(payload: dict, metadata: dict):
    """
    Cuando se recibe un pago, el inventario revisa si hay items que deban
    ser descontados (aquellos que pasan de PENDING a PREPARING).
    """
    order_id = payload.get("order_id")
    
    async with async_session_maker() as session:
        try:
            from pos_core.sales.repository import order_repo
            from pos_core.sales.models import OrderStatus
            
            # Cargamos la orden con sus items
            order = await order_repo.get_with_relations(session, order_id)
            if not order:
                logger.error(f"❌ Orden {order_id} no encontrada en listener de inventario")
                return

            # Identificar items que están PENDING (intención de despacho tras pago)
            items_to_deplete = [i for i in order.items if i.status == OrderStatus.PENDING]
            
            if not items_to_deplete:
                return # Nada que hacer si ya estaban procesados

            logger.info(f"📦 Procesando descarga de inventario para {len(items_to_deplete)} items de la orden {order_id}")
            
            # 1. Descontar stock
            await process_inventory_depletion(session, items_to_deplete)
            
            # 2. Actualizar estado de los items (Cerebro vs Músculo: el inventario confirma el cambio)
            for item in items_to_deplete:
                item.status = OrderStatus.PREPARING
            
            await session.commit()
            logger.info(f"✅ Inventario descontado y estados actualizados para orden {order_id}")
            
            # 3. Broadcast UI
            from pos_core.events.service import trigger_broadcast
            await trigger_broadcast("inventory", db=session)
            
        except Exception as e:
            logger.error(f"❌ Error en inventario tras pago de orden {order_id}: {e}", exc_info=True)

@on_event("sales.order_delivered")
async def on_order_delivered(payload: dict, metadata: dict):
    """
    Mantiene compatibilidad con disparos manuales de entrega.
    """
    order_id = payload.get("order_id")
    items = payload.get("items")
    
    if not items:
        return

    async with async_session_maker() as session:
        try:
            await process_inventory_depletion(session, items)
            await session.commit()
            
            from pos_core.events.service import trigger_broadcast
            await trigger_broadcast("inventory", db=session)
        except Exception as e:
            logger.error(f"❌ Error en on_order_delivered: {e}")
