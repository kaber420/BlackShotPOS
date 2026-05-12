from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Order, OrderItem, OrderStatus, OrderType
from ..repository import order_repo, item_repo
from pos_core.accounting.service import get_active_shift
from pos_core.events.bus import event_bus
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
    if not active_shift:
        raise InvalidOrderStateError("No se puede crear una orden sin un turno abierto.")
    
    shift_id = active_shift.id

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
    await session.commit()
    await session.refresh(db_order)

    # Emitir evento de creación para que otros módulos reaccionen
    await event_bus.publish(
        "sales.order_created", 
        {
            "order_id": db_order.id,
            "table_id": db_order.table_id,
            "type": db_order.type,
            "waiter_uuid": db_order.waiter_uuid
        },
        actor_uuid=waiter_uuid
    )

    return db_order


async def get_order_by_id(session: AsyncSession, order_id: int) -> Optional[Order]:
    return await order_repo.get_by_id(session, order_id)


async def get_orders(
    session: AsyncSession, status: Optional[OrderStatus] = None
) -> List[Order]:
    """Obtiene las órdenes, asegurando carga aislada de relaciones."""
    active_shift = await get_active_shift(session)
    shift_id = active_shift.id if active_shift else None
    
    # Obtenemos solo los esqueletos
    base_orders = await order_repo.get_all(session, status, shift_id=shift_id)
    
    # Cargamos relaciones una por una para evitar el bug de 'mezclado'
    full_orders = []
    for o in base_orders:
        full_o = await get_order_with_relations(session, o.id)
        if full_o:
            full_orders.append(full_o)
            
    return full_orders






async def get_order_with_relations(
    session: AsyncSession, order_id: int
) -> Optional[Order]:
    """Obtiene una orden con todas sus relaciones cargadas (para serialización Pydantic)."""
    return await order_repo.get_with_relations(session, order_id)


async def update_order_status(
    session: AsyncSession,
    order_id: int,
    new_status: OrderStatus,
    actor_uuid: Optional[str] = None,
    actor_name: Optional[str] = None,
) -> Optional[Order]:
    """
    Actualiza el estado comercial de una orden.
    La lógica operativa (cocina) ahora se maneja en el dominio Kitchen.
    """
    order = await order_repo.get_by_id(session, order_id)
    if not order:
        raise OrderNotFoundError(order_id)

    old_status = order.status
    order.status = new_status
    
    if new_status == OrderStatus.DELIVERED:
        # Al entregar la orden, aseguramos que todos los items estén entregados
        items = await item_repo.get_items_for_order(session, order_id)
        for i in items:
            if i.status != OrderStatus.CANCELLED:
                i.status = OrderStatus.DELIVERED
                await item_repo.save(session, i)

    await order_repo.save(session, order)
    await session.commit()
    order = await order_repo.get_with_relations(session, order_id)

    # Emitir cambio de estado para que otros módulos (Kitchen, Tables, IoT) reaccionen
    await event_bus.publish(
        "sales.order_status_changed",
        {
            "order_id": order.id,
            "old_status": old_status,
            "new_status": new_status,
            "table_id": order.table_id,
            "actor_name": actor_name
        },
        actor_uuid=actor_uuid
    )

    if new_status == OrderStatus.CANCELLED:
        await event_bus.publish("sales.order_cancelled", {"order_id": order_id, "table_id": order.table_id}, actor_uuid=actor_uuid)
    elif new_status == OrderStatus.DELIVERED:
        await event_bus.publish("sales.order_delivered", {"order_id": order_id, "table_id": order.table_id}, actor_uuid=actor_uuid)

    return order

    return order


async def recalculate_order_totals(session: AsyncSession, order_id: int) -> Order:
    """
    Recalcula subtotal, impuestos y total de una orden basándose en sus items activos.
    """
    order = await order_repo.get_with_relations(session, order_id)
    if not order:
        raise OrderNotFoundError(order_id)
    
    subtotal = 0.0
    tax_amount = 0.0
    
    for item in order.items:
        if item.status != OrderStatus.CANCELLED:
            item_subtotal = item.unit_price * item.quantity
            # Aseguramos que el tax_amount del item sea consistente
            item.tax_amount = item_subtotal * (item.tax_rate / 100.0)
            
            subtotal += item_subtotal
            tax_amount += item.tax_amount
            
    order.subtotal = subtotal
    order.tax_amount = tax_amount
    order.total_amount = subtotal + tax_amount
    
    await order_repo.save(session, order)
    await session.commit()
    order = await order_repo.get_with_relations(session, order_id)
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

    await order_repo.delete(session, order)
    await session.commit()

    # Emitir evento de eliminación
    await event_bus.publish(
        "sales.order_deleted",
        {
            "order_id": order_id,
            "table_id": order.table_id
        }
    )

    return True
