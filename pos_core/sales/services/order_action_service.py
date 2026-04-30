import json
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Order, OrderItem, OrderStatus
from pos_core.audit.models import AuditCategory
from ..repository import order_repo, item_repo
from pos_core.audit import service as audit_service
from pos_core.exceptions import OrderNotFoundError


async def cancel_order(
    session: AsyncSession,
    order_id: int,
    reason: str,
    actor_uuid: str,
    actor_name: str,
) -> Order:
    """
    Cancela una orden completa, registra el motivo en auditoría y libera la mesa.
    """
    order = await order_repo.get_by_id(session, order_id)
    if not order:
        raise OrderNotFoundError(order_id)
    
    if order.status == OrderStatus.CANCELLED:
        return order

    # 1. Cambiar estado
    order.status = OrderStatus.CANCELLED
    await order_repo.save(session, order)

    # 2. Cancelar todos los ítems que no estén cancelados
    items = await item_repo.get_items_for_order(session, order_id)
    for item in items:
        if item.status != OrderStatus.CANCELLED:
            item.status = OrderStatus.CANCELLED
            await item_repo.save(session, item)

    # 3. Liberar mesa si aplica
    if order.table_id:
        from pos_core.tables import service as table_service
        await table_service.vacate_table_service(session, order.table_id)

    # 4. Registrar auditoría
    await audit_service.log_action(
        session,
        category=AuditCategory.SALES,
        action="ORDER_CANCELLED",
        reason=reason,
        actor_uuid=actor_uuid,
        actor_name=actor_name,
        target_id=str(order_id),
        target_type="order",
    )

    from .order_lifecycle_service import recalculate_order_totals
    await recalculate_order_totals(session, order_id)

    await session.commit()
    await session.refresh(order)
    return order


async def cancel_order_item(
    session: AsyncSession,
    order_id: int,
    item_id: int,
    reason: str,
    actor_uuid: str,
    actor_name: str,
) -> OrderItem:
    """
    Cancela un ítem individual de una orden y lo registra en auditoría.
    """
    item = await item_repo.get_by_id(session, order_id, item_id)
    if not item:
        raise ValueError(f"OrderItem {item_id} not found in order {order_id}")

    if item.status == OrderStatus.CANCELLED:
        return item

    # 1. Cambiar estado del ítem
    item.status = OrderStatus.CANCELLED
    await item_repo.save(session, item)

    # 2. Registrar auditoría
    await audit_service.log_action(
        session,
        category=AuditCategory.SALES,
        action="ITEM_CANCELLED",
        reason=reason,
        actor_uuid=actor_uuid,
        actor_name=actor_name,
        target_id=str(item_id),
        target_type="order_item",
        changes_json=json.dumps({"order_id": order_id})
    )

    # 3. Recalcular estado de la orden (si todos los ítems están cancelados, cancelar orden)
    items = await item_repo.get_items_for_order(session, order_id)
    all_cancelled = all(i.status == OrderStatus.CANCELLED for i in items)
    
    if all_cancelled:
        order = await order_repo.get_by_id(session, order_id)
        if order and order.status != OrderStatus.CANCELLED:
            order.status = OrderStatus.CANCELLED
            await order_repo.save(session, order)
            if order.table_id:
                from pos_core.tables import service as table_service
                await table_service.vacate_table_service(session, order.table_id)

    from .order_lifecycle_service import recalculate_order_totals
    await recalculate_order_totals(session, order_id)

    await session.commit()
    await session.refresh(item)
    return item


async def transfer_order_table(
    session: AsyncSession,
    order_id: int,
    new_table_id: int,
    actor_uuid: str,
    actor_name: str,
) -> Order:
    """
    Transfiere una orden de una mesa a otra.
    Mantiene el tiempo de ocupación (occupied_at) de la mesa original en la nueva.
    """
    from pos_core.tables.models import Table

    order = await order_repo.get_by_id(session, order_id)
    if not order:
        raise OrderNotFoundError(order_id)
    
    if order.table_id == new_table_id:
        return order

    new_table = await session.get(Table, new_table_id)
    if not new_table:
        raise ValueError(f"Target table {new_table_id} does not exist")
    
    if new_table.status != "Free":
        raise ValueError(f"Target table {new_table_id} is not free (Status: {new_table.status})")

    old_table_id = order.table_id
    occupied_at = None

    if old_table_id:
        old_table = await session.get(Table, old_table_id)
        if old_table:
            occupied_at = old_table.occupied_at
            old_table.status = "Free"
            old_table.occupied_at = None
            session.add(old_table)

    if not occupied_at:
        occupied_at = datetime.now(timezone.utc)

    new_table.status = "Occupied"
    new_table.occupied_at = occupied_at
    session.add(new_table)

    order.table_id = new_table_id
    await order_repo.save(session, order)

    await audit_service.log_action(
        session,
        category=AuditCategory.SALES,
        action="TABLE_TRANSFERRED",
        reason="Cambio de mesa",
        actor_uuid=actor_uuid,
        actor_name=actor_name,
        target_id=str(order_id),
        target_type="order",
        changes_json=json.dumps({"from_table": old_table_id, "to_table": new_table_id})
    )

    await session.commit()
    await session.refresh(order)
    return order
