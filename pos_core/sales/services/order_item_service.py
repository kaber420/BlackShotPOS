from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Order, OrderItem, OrderStatus
from ..repository import order_repo, item_repo
from pos_core.accounting.service import get_active_shift
from pos_core.exceptions import InvalidOrderStateError


async def add_item_to_order(
    session: AsyncSession,
    order_id: int,
    product_id: int,
    quantity: int,
    product_variant_id: Optional[int] = None,
    modifier_ids: Optional[List[int]] = None,
) -> OrderItem:
    # 1. Validar que haya un turno abierto para operar
    active_shift = await get_active_shift(session)
    if not active_shift:
        raise InvalidOrderStateError("No se pueden añadir productos a la orden sin un turno abierto.")

    from pos_core.catalog.models import Product, ProductVariant, Modifier, Tax
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select

    # Obtenemos producto con su impuesto relacionado
    statement = select(Product).where(Product.id == product_id).options(selectinload(Product.tax))
    result = await session.execute(statement)
    product = result.scalar_one_or_none()

    if not product:
        raise ValueError(f"Product with id {product_id} not found")

    base_price = product.price
    if product_variant_id:
        variant = await session.get(ProductVariant, product_variant_id)
        if variant:
            base_price = variant.price
        else:
            raise ValueError(f"Variant with id {product_variant_id} not found")

    extra_price = 0.0
    modifiers = []
    if modifier_ids:
        for m_id in modifier_ids:
            mod = await session.get(Modifier, m_id)
            if mod:
                extra_price += mod.extra_price
                modifiers.append(mod)

    unit_price = base_price + extra_price
    tax_rate = product.tax.rate if product.tax else 0.0
    tax_amount = (unit_price * quantity) * (tax_rate / 100.0)

    order_item = OrderItem(
        order_id=order_id,
        product_id=product_id,
        product_variant_id=product_variant_id,
        quantity=quantity,
        unit_price=unit_price,
        tax_rate=tax_rate,
        tax_amount=tax_amount,
        modifiers=modifiers,
    )
    session.add(order_item)
    await session.commit()
    
    # Recalculamos la orden completa para asegurar integridad
    from .order_lifecycle_service import recalculate_order_totals
    await recalculate_order_totals(session, order_id)
    
    # Recargamos el item con sus relaciones para el evento y el retorno
    order_item = await item_repo.get_by_id(session, order_id, order_item.id)
    if not order_item:
        raise ValueError(f"Error reloading order item {order_item.id}")

    # Emitir evento para que otros módulos (como Cocina) reaccionen
    order = await session.get(Order, order_id)
    from pos_core.events.bus import event_bus
    await event_bus.publish("sales.items_added", {
        "order_id": order_id,
        "table_id": order.table_id if order else None,
        "order_type": order.type if order else "DINE_IN",
        "waiter_name": order.waiter_name if order else None,
        "external_reference": order.external_reference if order else None,
        "items": [
            {
                "id": order_item.id,
                "product_id": order_item.product_id,
                "quantity": order_item.quantity,
                "modifiers": [{"id": m.id, "name": m.name} for m in order_item.modifiers]
            }
        ]
    })

    return order_item


async def update_order_item_status(
    session: AsyncSession,
    order_id: int,
    item_id: int,
    new_status: OrderStatus,
    actor_uuid: Optional[str] = None,
    actor_name: Optional[str] = None,
) -> Optional[OrderItem]:
    """
    Actualiza el estado comercial de un ítem de orden.
    El inventario se descuenta si el ítem pasa de PENDING a un estado operativo.
    Emite un evento para que Cocina u otros módulos reaccionen.
    """
    item = await item_repo.get_by_id(session, order_id, item_id)
    if not item:
        return None

    old_status = item.status
    if old_status == new_status:
        return item

    item.status = new_status
    await item_repo.save(session, item)
    await session.commit()
    # Emitir evento para que Cocina u otros módulos reaccionen
    from pos_core.events.bus import event_bus
    await event_bus.publish("sales.item_status_changed", {
        "order_id": order_id,
        "item_id": item_id,
        "old_status": old_status,
        "new_status": new_status,
        "actor_name": actor_name
    }, actor_uuid=actor_uuid)

    # Recargamos con relaciones para asegurar serialización correcta en el router
    item = await item_repo.get_by_id(session, order_id, item.id)

    # Lógica de Autocierre: si todos los ítems están entregados, marcar orden como entregada
    if new_status == OrderStatus.DELIVERED:
        items = await item_repo.get_items_for_order(session, order_id)
        if all(i.status == OrderStatus.DELIVERED or i.status == OrderStatus.CANCELLED for i in items):
            from .order_lifecycle_service import update_order_status
            await update_order_status(session, order_id, OrderStatus.DELIVERED, actor_uuid=actor_uuid, actor_name=actor_name)

    return item
