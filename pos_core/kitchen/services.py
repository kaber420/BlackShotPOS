import logging
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .models import KitchenTicket, KitchenStatus
from .repository import kitchen_repo
from pos_core.sales.models import OrderItem

logger = logging.getLogger(__name__)

async def create_tickets_for_order(session: AsyncSession, order_id: int, items_data: List[dict]):
    """
    Crea tickets de cocina para una lista de items de una orden.
    Se espera que items_data contenga info mínima para crear el ticket o que se consulten de la DB.
    """
    from pos_core.catalog.models import Product, Category
    
    for item in items_data:
        item_id = item.get("id")
        product_id = item.get("product_id")
        quantity = item.get("quantity", 1)
        
        # Obtener el área de producción desde el catálogo
        stmt = (
            select(Product)
            .where(Product.id == product_id)
            .options(selectinload(Product.category))
        )
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()
        
        production_area_id = None
        if product and product.category:
            production_area_id = product.category.production_area_id
            
        # Si no tiene área de producción, quizás no va a cocina (ej: un dulce empaquetado)
        if not production_area_id:
            logger.debug(f"ℹ️ Item {item_id} (Producto {product_id}) no tiene área de producción. Saltando ticket.")
            continue

        # Construir snapshot de modificadores
        modifiers_text = ""
        if "modifiers" in item:
            mods = item["modifiers"]
            modifiers_text = ", ".join([f"+ {m.get('name', 'Mod')}" for m in mods])

        ticket = KitchenTicket(
            order_id=order_id,
            item_id=item_id,
            product_name=product.name if product else f"Producto #{product_id}",
            variant_name=item.get("variant_name"),
            modifiers_text=modifiers_text,
            production_area_id=production_area_id,
            status=KitchenStatus.PENDING,
            received_at=datetime.now(timezone.utc)
        )
        await kitchen_repo.save(session, ticket)
    
    await session.commit()
    logger.info(f"👨‍🍳 Tickets creados para la orden {order_id}")

async def update_ticket_status(
    session: AsyncSession, 
    ticket_id: int, 
    new_status: KitchenStatus,
    cook_uuid: Optional[str] = None,
    cook_name: Optional[str] = None
) -> Optional[KitchenTicket]:
    ticket = await kitchen_repo.get_ticket_by_id(session, ticket_id)
    if not ticket:
        return None
    
    ticket.status = new_status
    now = datetime.now(timezone.utc)
    
    if new_status == KitchenStatus.PREPARING:
        ticket.started_at = now
        ticket.cook_uuid = cook_uuid
        ticket.cook_name = cook_name
        # Emitir evento kitchen.item_preparing para que Ventas se entere del inicio
        from pos_core.events.bus import event_bus
        await event_bus.publish("kitchen.item_preparing", {
            "ticket_id": ticket.id,
            "order_id": ticket.order_id,
            "item_id": ticket.item_id,
            "cook_name": cook_name
        }, actor_uuid=cook_uuid)
    elif new_status == KitchenStatus.READY:
        ticket.finished_at = now
        # Emitir evento kitchen.item_ready
        from pos_core.events.bus import event_bus
        await event_bus.publish("kitchen.item_ready", {
            "ticket_id": ticket.id,
            "order_id": ticket.order_id,
            "item_id": ticket.item_id,
            "product_name": ticket.product_name
        })
    elif new_status == KitchenStatus.DELIVERED:
        ticket.delivered_at = now

    await kitchen_repo.save(session, ticket)
    await session.commit()
    return ticket
