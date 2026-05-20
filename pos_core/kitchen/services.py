import logging
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .models import KitchenTicket, KitchenStatus
from .repository import kitchen_repo

logger = logging.getLogger(__name__)

async def create_tickets_for_order(
    session: AsyncSession, 
    order_id: int, 
    items_data: List[dict],
    **extra_metadata
):
    """
    Crea los tickets de cocina correspondientes para los ítems de una orden.
    Optimizado para evitar consultas N+1 en la obtención de productos del catálogo.
    """
    from pos_core.catalog.models import Product
    
    # Metadata opcional de la orden (snapshot)
    table_id = extra_metadata.get("table_id")
    order_type = extra_metadata.get("order_type", "DINE_IN")
    waiter_name = extra_metadata.get("waiter_name")
    external_reference = extra_metadata.get("external_reference")
    
    # Pre-cargar todos los productos involucrados de una sola vez
    product_ids = {item.get("product_id") for item in items_data if item.get("product_id") is not None}
    products_map = {}
    if product_ids:
        stmt = (
            select(Product)
            .where(Product.id.in_(product_ids))
            .options(selectinload(Product.category))
        )
        result = await session.execute(stmt)
        products_map = {p.id: p for p in result.scalars().all()}
        
    tickets_created = 0
    for item in items_data:
        item_id = item.get("id")
        product_id = item.get("product_id")
        
        product = products_map.get(product_id)
        
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

        # Determinar estado inicial: Si no requiere preparación, nace como READY
        initial_status = KitchenStatus.PENDING
        if product and not getattr(product, "requires_preparation", True):
            initial_status = KitchenStatus.READY

        ticket = KitchenTicket(
            order_id=order_id,
            item_id=item_id,
            table_id=table_id,
            order_type=order_type,
            waiter_name=waiter_name,
            external_reference=external_reference,
            product_name=product.name if product else f"Producto #{product_id}",
            variant_name=item.get("variant_name"),
            modifiers_text=modifiers_text,
            production_area_id=production_area_id,
            status=initial_status,
            received_at=datetime.now(timezone.utc).replace(tzinfo=None)
        )
        await kitchen_repo.save(session, ticket)
        tickets_created += 1
    
    if tickets_created > 0:
        await session.commit()
        logger.info(f"👨‍🍳 {tickets_created} tickets creados para la orden {order_id}")
        
        # Notificar a la UI del KDS y Meseros
        from pos_core.events.service import trigger_standard_broadcasts
        await trigger_standard_broadcasts()


async def _apply_ticket_status_change(
    ticket: KitchenTicket,
    new_status: KitchenStatus,
    now: datetime,
    cook_uuid: Optional[str] = None,
    cook_name: Optional[str] = None
) -> bool:
    """
    Aplica el cambio de estado en memoria al ticket y publica eventos en el Event Bus.
    No realiza transacciones de base de datos de forma directa.
    Retorna True si el estado cambió, False de lo contrario.
    """
    if ticket.status == new_status:
        return False
        
    ticket.status = new_status
    
    if new_status == KitchenStatus.PREPARING:
        ticket.started_at = now
        ticket.cook_uuid = cook_uuid
        ticket.cook_name = cook_name
        
        from pos_core.events.bus import event_bus
        await event_bus.publish("kitchen.item_preparing", {
            "ticket_id": ticket.id,
            "order_id": ticket.order_id,
            "item_id": ticket.item_id,
            "table_id": ticket.table_id,
            "cook_name": cook_name
        }, actor_uuid=cook_uuid)
        
    elif new_status == KitchenStatus.READY:
        ticket.finished_at = now
        
        from pos_core.events.bus import event_bus
        await event_bus.publish("kitchen.item_ready", {
            "ticket_id": ticket.id,
            "order_id": ticket.order_id,
            "item_id": ticket.item_id,
            "table_id": ticket.table_id,
            "product_name": ticket.product_name
        })
        
    elif new_status == KitchenStatus.DELIVERED:
        ticket.delivered_at = now
        
        from pos_core.events.bus import event_bus
        await event_bus.publish("kitchen.item_delivered", {
            "ticket_id": ticket.id,
            "order_id": ticket.order_id,
            "item_id": ticket.item_id,
            "product_name": ticket.product_name
        })
        
    return True


async def update_ticket_status(
    session: AsyncSession, 
    ticket_id: int, 
    new_status: KitchenStatus,
    cook_uuid: Optional[str] = None,
    cook_name: Optional[str] = None
) -> Optional[KitchenTicket]:
    """Actualiza el estado de un ticket individual."""
    ticket = await kitchen_repo.get_ticket_by_id(session, ticket_id)
    if not ticket:
        return None
    
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    changed = await _apply_ticket_status_change(ticket, new_status, now, cook_uuid, cook_name)
    
    if changed:
        await kitchen_repo.save(session, ticket)
        await session.commit()
        
        # Notificar a la UI del KDS y del Dashboard (Cocina y Stats)
        from pos_core.events.service import trigger_broadcast
        await trigger_broadcast("kitchen_orders")
        await trigger_broadcast("dashboard_stats")
        
    return ticket


async def update_ticket_status_by_item_id(
    session: AsyncSession,
    item_id: int,
    new_status: KitchenStatus,
    cook_uuid: Optional[str] = None,
    cook_name: Optional[str] = None
) -> Optional[KitchenTicket]:
    """Busca el ticket por item_id y lo actualiza."""
    ticket = await kitchen_repo.get_ticket_by_item_id(session, item_id)
    if not ticket:
        return None
    return await update_ticket_status(session, ticket.id, new_status, cook_uuid, cook_name)


async def update_order_tickets_status(
    session: AsyncSession,
    order_id: int,
    new_status: KitchenStatus,
    cook_uuid: Optional[str] = None,
    cook_name: Optional[str] = None
) -> List[KitchenTicket]:
    """
    Actualiza todos los tickets asociados a una orden.
    Optimizado: realiza un único commit de BD y un único broadcast de red al final.
    """
    tickets = await kitchen_repo.get_tickets_by_order(session, order_id)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    updated = []
    
    any_changed = False
    for t in tickets:
        changed = await _apply_ticket_status_change(t, new_status, now, cook_uuid, cook_name)
        if changed:
            await kitchen_repo.save(session, t)
            updated.append(t)
            any_changed = True
            
    if any_changed:
        await session.commit()
        
        # Notificar a la UI del KDS y del Dashboard (Cocina y Stats)
        from pos_core.events.service import trigger_broadcast
        await trigger_broadcast("kitchen_orders")
        await trigger_broadcast("dashboard_stats")
        
    return updated

