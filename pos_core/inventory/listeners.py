import logging
from pos_core.events.bus import on_event
from pos_core.database import async_session_maker
from pos_core.inventory.services.stock_service import process_inventory_depletion

logger = logging.getLogger(__name__)

@on_event("sales.payment_received")
async def on_payment_received(payload: dict, metadata: dict):
    """
    Cuando se recibe un pago, el inventario revisa si hay items que deban
    ser descontados (aquellos que aún están PENDING y son de venta directa).
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

            # Identificar items que están PENDING y que NO van a cocina (ej. productos empaquetados)
            # Los items de cocina se descuentan en el evento 'kitchen.item_preparing'
            items_to_deplete = []
            for i in order.items:
                if i.status == OrderStatus.PENDING:
                    # Verificamos si el producto tiene área de producción
                    if not i.product or not i.product.category or not i.product.category.production_area_id:
                        i.status = OrderStatus.READY
                        items_to_deplete.append(i)
            
            if not items_to_deplete:
                logger.info(f"ℹ️ No hay items de venta directa para descontar en orden {order_id}. Los de cocina se procesarán al iniciar preparación.")
                return 

            logger.info(f"📦 Procesando descarga de inventario para {len(items_to_deplete)} items de la orden {order_id}")
            
            # 1. Descontar stock
            await process_inventory_depletion(session, items_to_deplete)
            
            await session.commit()
            logger.info(f"✅ Inventario descontado para orden {order_id}")
            
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

@on_event("kitchen.item_preparing")
async def on_kitchen_item_preparing(payload: dict, metadata: dict):
    """
    Cuando la cocina empieza a preparar un ítem, el inventario descuenta los insumos.
    Este es el punto de verdad para el consumo de stock en ítems de producción.
    """
    order_id = payload.get("order_id")
    item_id = payload.get("item_id")
    
    async with async_session_maker() as session:
        try:
            from pos_core.sales.repository import item_repo
            
            # Obtenemos el item para tener acceso a su product_id y modificadores
            item = await item_repo.get_by_id(session, order_id, item_id)
            if not item:
                logger.error(f"❌ Item {item_id} no encontrado en Sales para descarga de inventario")
                return

            logger.info(f"📦 Descontando inventario por inicio de cocina: Item {item_id} (Orden {order_id})")
            await process_inventory_depletion(session, [item])
            await session.commit()
            
            from pos_core.events.service import trigger_broadcast
            await trigger_broadcast("inventory", db=session)
        except Exception as e:
            logger.error(f"❌ Error en inventario al procesar kitchen.item_preparing: {e}")
