import logging
from pos_core.events.bus import on_event
from pos_core.database import async_session_maker
from .models import OrderStatus
from .repository import item_repo, order_repo

logger = logging.getLogger(__name__)

@on_event("sales.items_added")
async def on_items_added(payload: dict, metadata: dict):
    """
    Cuando se añaden items, aquellos que no van a cocina se marcan como READY
    automáticamente para que el mesero sepa que puede tomarlos de inmediato.
    """
    order_id = payload.get("order_id")
    items_payload = payload.get("items", [])
    if not items_payload:
        return

    async with async_session_maker() as session:
        try:
            from pos_core.catalog.models import Product
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload

            for item_data in items_payload:
                item_id = item_data.get("id")
                # Obtenemos el item de la base de datos
                item = await item_repo.get_by_id(session, order_id, item_id)
                if not item:
                    continue
                
                # Verificamos si el producto tiene área de producción
                # Si no tiene, se considera "Venta Directa" y se marca como READY.
                stmt = select(Product).where(Product.id == item.product_id).options(selectinload(Product.category))
                res = await session.execute(stmt)
                product = res.scalar_one_or_none()
                
                if not product or not product.category or not product.category.production_area_id or not getattr(product, "requires_preparation", True):
                    item.status = OrderStatus.READY
                    await item_repo.save(session, item)
                    logger.info(f"✨ Item {item_id} (No requiere preparación o Venta Directa) marcado como READY automáticamente.")
            
            await session.commit()
            
            # Notificar a la UI para que se vea el cambio de color de inmediato
            from pos_core.events.service import trigger_standard_broadcasts
            await trigger_standard_broadcasts()
        except Exception as e:
            logger.error(f"❌ Error en on_items_added (Sales): {e}")

@on_event("kitchen.item_preparing")
@on_event("kitchen.item_ready")
@on_event("kitchen.item_delivered")
async def on_kitchen_item_status_change(payload: dict, metadata: dict):
    """Consolida la actualización de estados de cocina a la base de datos física de ventas."""
    topic = metadata.get("topic")
    order_id = payload.get("order_id")
    item_id = payload.get("item_id")
    if not topic or not order_id or not item_id:
        return

    # Mapeo de tópicos de cocina a estados comerciales de ventas
    status_map = {
        "kitchen.item_preparing": OrderStatus.PREPARING,
        "kitchen.item_ready": OrderStatus.READY,
        "kitchen.item_delivered": OrderStatus.DELIVERED
    }
    
    new_status = status_map.get(topic)
    if not new_status:
        return

    async with async_session_maker() as session:
        try:
            item = await item_repo.get_by_id(session, order_id, item_id)
            if item and item.status != new_status:
                item.status = new_status
                await item_repo.save(session, item)
                await session.commit()
                logger.info(f"🔄 OrderItem {item_id} (Orden {order_id}) actualizado a {new_status} en base de datos.")
        except Exception as e:
            logger.error(f"❌ Error en on_kitchen_item_status_change: {e}")
