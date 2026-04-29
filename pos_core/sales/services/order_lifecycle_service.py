from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Order, OrderItem, OrderStatus, OrderType
from ..repository import order_repo, item_repo
from pos_core.inventory.services.stock_service import process_inventory_depletion
from pos_core.sales.shifts_service import get_active_shift
from pos_core.events.service import trigger_iot_broadcast
from pos_core.exceptions import OrderNotFoundError, InvalidOrderStateError


async def create_order(
    session: AsyncSession,
    order_type: OrderType,
    table_id: Optional[int] = None,
    external_reference: Optional[str] = None,
    waiter_uuid: Optional[str] = None,
    waiter_name: Optional[str] = None,
) -> Order:
    active_shift = await get_active_shift(session)
    shift_id = active_shift.id if active_shift else None

    db_order = Order(
        type=order_type,
        table_id=table_id,
        shift_id=shift_id,
        external_reference=external_reference,
        status=OrderStatus.PENDING,
        waiter_uuid=waiter_uuid,
        waiter_name=waiter_name,
    )
    session.add(db_order)

    # Marcar mesa como ocupada si se asigna una
    if table_id:
        from pos_core.tables.models import Table
        db_table = await session.get(Table, table_id)
        if db_table and db_table.status != "Occupied":
            db_table.status = "Occupied"
            db_table.occupied_at = datetime.now(timezone.utc)
            session.add(db_table)

    await session.commit()
    await session.refresh(db_order)
    return db_order


async def get_order_by_id(session: AsyncSession, order_id: int) -> Optional[Order]:
    return await order_repo.get_by_id(session, order_id)


async def get_orders(
    session: AsyncSession, status: Optional[OrderStatus] = None
) -> List[Order]:
    return await order_repo.get_all(session, status)


async def get_kitchen_orders(session: AsyncSession) -> List[Order]:
    """Retorna las órdenes PENDING y PREPARING para la pantalla KDS."""
    return await order_repo.get_active_for_kitchen(session)


async def get_order_with_relations(
    session: AsyncSession, order_id: int
) -> Optional[Order]:
    """Obtiene una orden con todas sus relaciones cargadas (para serialización Pydantic)."""
    return await order_repo.get_with_relations(session, order_id)


async def update_order_status(
    session: AsyncSession,
    order_id: int,
    new_status: OrderStatus,
    cook_uuid: Optional[str] = None,
    cook_name: Optional[str] = None,
    delivered_by_uuid: Optional[str] = None,
    delivered_by_name: Optional[str] = None,
) -> Optional[Order]:
    order = await order_repo.get_by_id(session, order_id)
    if not order:
        raise OrderNotFoundError(order_id)

    old_status = order.status
    order.status = new_status
    now = datetime.now(timezone.utc)

    if new_status == OrderStatus.PREPARING and order.preparing_at is None:
        order.preparing_at = now
        if cook_uuid and order.cook_uuid is None:
            order.cook_uuid = cook_uuid
            order.cook_name = cook_name

    elif new_status == OrderStatus.READY and order.ready_at is None:
        order.ready_at = now
        if cook_uuid and order.cook_uuid is None:
            order.cook_uuid = cook_uuid
            order.cook_name = cook_name
        if order.table_id:
            await trigger_iot_broadcast(
                order.table_id, "order_update", "",
                data={"order_id": order.id, "status": "LISTO", "progress": 100},
            )

    elif new_status == OrderStatus.DELIVERED and order.delivered_at is None:
        order.delivered_at = now

    await order_repo.save(session, order)

    # Cancelación: delegar liberación de mesa al table_service (sin acoplamiento directo)
    if new_status == OrderStatus.CANCELLED and order.table_id:
        from pos_core.tables import service as table_service
        await table_service.vacate_table_service(session, order.table_id)

    await session.commit()
    await session.refresh(order)

    # Propagar estado a los ítems
    order_items = await item_repo.get_items_for_order(session, order_id)

    if new_status in (OrderStatus.READY, OrderStatus.DELIVERED):
        items_to_advance = [
            i for i in order_items
            if i.status in (OrderStatus.PENDING, OrderStatus.PREPARING, OrderStatus.READY)
        ]
        items_to_deplete = [i for i in order_items if i.status == OrderStatus.PENDING]
        for i in items_to_advance:
            i.status = new_status
            if new_status == OrderStatus.READY and i.ready_at is None:
                i.ready_at = now
                if cook_uuid and i.cook_uuid is None:
                    i.cook_uuid = cook_uuid
                    i.cook_name = cook_name
            elif new_status == OrderStatus.DELIVERED and i.delivered_at is None:
                i.delivered_at = now
                if delivered_by_uuid and i.delivered_by_uuid is None:
                    i.delivered_by_uuid = delivered_by_uuid
                    i.delivered_by_name = delivered_by_name
            await item_repo.save(session, i)
        if items_to_deplete:
            await process_inventory_depletion(session, items_to_deplete)
        if items_to_advance:
            await session.commit()

    elif old_status == OrderStatus.PENDING and new_status == OrderStatus.PREPARING:
        items_to_deplete = [i for i in order_items if i.status == OrderStatus.PENDING]
        for i in items_to_deplete:
            i.status = OrderStatus.PREPARING
            if i.preparing_at is None:
                i.preparing_at = now
            if cook_uuid and i.cook_uuid is None:
                i.cook_uuid = cook_uuid
                i.cook_name = cook_name
            await item_repo.save(session, i)
        if items_to_deplete:
            await process_inventory_depletion(session, items_to_deplete)
            await session.commit()

    return order


async def delete_order(session: AsyncSession, order_id: int) -> bool:
    """
    Elimina físicamente una orden VACÍA.
    Si tiene artículos, lanza error para proteger la auditoría.
    """
    order = await order_repo.get_with_relations(session, order_id)
    if not order:
        return False

    if len(order.items) > 0:
        raise InvalidOrderStateError(
            "No se puede eliminar una orden que ya contiene artículos. "
            "Use Cancelar para mantener auditoría."
        )

    if order.table_id:
        from pos_core.tables import service as table_service
        await table_service.vacate_table_service(session, order.table_id)

    await order_repo.delete(session, order)
    await session.commit()
    return True
