"""
pos_core/sales/order_service.py
================================
Servicio de Órdenes: gestiona el ciclo de vida completo de una orden.

RESPONSABILIDADES:
  - Crear, leer, actualizar y eliminar órdenes.
  - Gestionar ítems de orden (agregar, actualizar estado).
  - Coordinar con inventory_service para el descuento de stock.
  - Coordinar con table_service al cancelar (vía import local para evitar circulares).
  - Controlar límites transaccionales (session.commit).
  - NO contiene lógica financiera (eso es payment_service).
  - NO contiene cálculos de analíticas (eso es analytics_service).
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .models import Order, OrderItem, OrderStatus, OrderType, AuditCategory
from .repository import order_repo, item_repo
from . import audit_service
from pos_core.inventory.service import process_inventory_depletion
from pos_core.sales.shifts_service import get_active_shift
from pos_core.events.service import trigger_iot_broadcast
from pos_core.exceptions import OrderNotFoundError, InvalidOrderStateError


# ── Creación ───────────────────────────────────────────────────────────────────

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


# ── Lectura ────────────────────────────────────────────────────────────────────

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


# ── Ítems de Orden ─────────────────────────────────────────────────────────────

async def add_item_to_order(
    session: AsyncSession,
    order_id: int,
    product_id: int,
    quantity: int,
    product_variant_id: Optional[int] = None,
    modifier_ids: Optional[List[int]] = None,
) -> OrderItem:
    from pos_core.inventory.models import Product, ProductVariant, Modifier

    product = await session.get(Product, product_id)
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

    order_item = OrderItem(
        order_id=order_id,
        product_id=product_id,
        product_variant_id=product_variant_id,
        quantity=quantity,
        unit_price=base_price + extra_price,
        modifiers=modifiers,
    )
    session.add(order_item)
    await session.commit()
    await session.refresh(order_item)
    return order_item


# ── Actualización de Estado de Orden ──────────────────────────────────────────

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
        # 3. La orden mantiene su status operativo (PENDING/PREPARING/READY/DELIVERED)
        # No la movemos a un estado terminal 'PAID' para no perder el contexto de servicio.
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


# ── Actualización de Estado de Ítem Individual ────────────────────────────────

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

            # Permitimos que la orden siga su flujo operativo normal (READY -> DELIVERED)
            # sin importar si ya fue pagada.
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


# ── Eliminación ────────────────────────────────────────────────────────────────

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
# ── Cancelación y Auditoría ────────────────────────────────────────────────────

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
    import json
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
    # Reutilizamos la lógica existente en update_order_item_status si fuera necesario, 
    # pero aquí lo hacemos explícito para mayor claridad.
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

    await session.commit()
    await session.refresh(item)
    return item
