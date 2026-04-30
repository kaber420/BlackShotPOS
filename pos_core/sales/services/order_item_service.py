from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import OrderItem, OrderStatus
from ..repository import order_repo, item_repo
from pos_core.inventory.services.stock_service import process_inventory_depletion
from pos_core.events.service import trigger_iot_broadcast


async def add_item_to_order(
    session: AsyncSession,
    order_id: int,
    product_id: int,
    quantity: int,
    product_variant_id: Optional[int] = None,
    modifier_ids: Optional[List[int]] = None,
) -> OrderItem:
    from pos_core.inventory.models import Product, ProductVariant, Modifier, Tax
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
    
    await session.refresh(order_item)
    return order_item


async def update_order_item_status(
    session: AsyncSession,
    order_id: int,
    item_id: int,
    new_status: OrderStatus,
    cook_uuid: Optional[str] = None,
    cook_name: Optional[str] = None,
    delivered_by_uuid: Optional[str] = None,
    delivered_by_name: Optional[str] = None,
) -> Optional[OrderItem]:
    item = await item_repo.get_by_id(session, order_id, item_id)
    if not item:
        return None

    old_status = item.status
    if old_status == new_status:
        return item

    item.status = new_status
    now = datetime.now(timezone.utc)

    if new_status == OrderStatus.PREPARING and item.preparing_at is None:
        item.preparing_at = now
        if cook_uuid and item.cook_uuid is None:
            item.cook_uuid = cook_uuid
            item.cook_name = cook_name
    elif new_status == OrderStatus.READY and item.ready_at is None:
        item.ready_at = now
        if cook_uuid and item.cook_uuid is None:
            item.cook_uuid = cook_uuid
            item.cook_name = cook_name
    elif new_status == OrderStatus.DELIVERED and item.delivered_at is None:
        item.delivered_at = now
        if delivered_by_uuid and item.delivered_by_uuid is None:
            item.delivered_by_uuid = delivered_by_uuid
            item.delivered_by_name = delivered_by_name

    await item_repo.save(session, item)

    if old_status == OrderStatus.PENDING and new_status in (
        OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.DELIVERED
    ):
        await process_inventory_depletion(session, [item])

    # Recalcular estado de la orden padre
    order_items = await item_repo.get_items_for_order(session, order_id)
    order = await order_repo.get_by_id(session, order_id)

    if order:
        all_completed = True
        all_delivered = True
        all_cancelled = True
        any_preparing = False
        any_pending = False

        for i in order_items:
            status = new_status if i.id == item_id else i.status
            if status == OrderStatus.PREPARING:
                any_preparing = True
            if status == OrderStatus.PENDING:
                any_pending = True
            if status not in (OrderStatus.READY, OrderStatus.DELIVERED, OrderStatus.CANCELLED):
                all_completed = False
            if status not in (OrderStatus.DELIVERED, OrderStatus.CANCELLED):
                all_delivered = False
            if status != OrderStatus.CANCELLED:
                all_cancelled = False

        new_order_status = None
        if all_cancelled and len(order_items) > 0:
            new_order_status = OrderStatus.CANCELLED
            if order.table_id:
                from pos_core.tables import service as table_service
                await table_service.vacate_table_service(session, order.table_id)
        elif all_delivered and len(order_items) > 0:
            new_order_status = OrderStatus.DELIVERED
        elif all_completed and len(order_items) > 0:
            new_order_status = OrderStatus.READY
        elif any_preparing:
            new_order_status = OrderStatus.PREPARING
        elif any_pending:
            new_order_status = OrderStatus.PENDING

        if new_order_status and new_order_status != order.status:
            if cook_uuid and order.cook_uuid is None:
                order.cook_uuid = cook_uuid
                order.cook_name = cook_name

            is_becoming_ready = (
                new_order_status == OrderStatus.READY
                and order.status != OrderStatus.READY
            )
            
            order.status = new_order_status
            await order_repo.save(session, order)

            if is_becoming_ready and order.table_id:
                await trigger_iot_broadcast(
                    order.table_id, "order_update", "",
                    data={"order_id": order.id, "status": "LISTO", "progress": 100},
                )

    await session.commit()
    await session.refresh(item)
    return item
