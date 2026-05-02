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

async def split_order_items(
    session: AsyncSession,
    original_order_id: int,
    items_to_split: list, # List of SplitItemCreate
    actor_uuid: str,
    actor_name: str,
) -> Order:
    """
    Divide una orden transfiriendo los ítems especificados a una nueva orden
    en la misma mesa.
    """
    from pos_core.sales.schemas import SplitItemCreate
    
    original_order = await order_repo.get_with_relations(session, original_order_id)
    if not original_order:
        raise OrderNotFoundError(original_order_id)
        
    if not items_to_split:
        raise ValueError("No se especificaron ítems para dividir.")
        
    # Crear nueva orden
    new_order = Order(
        type=original_order.type,
        status=original_order.status,
        table_id=original_order.table_id,
        shift_id=original_order.shift_id,
        customer_id=original_order.customer_id,
        waiter_uuid=actor_uuid,
        waiter_name=actor_name,
    )
    session.add(new_order)
    await session.flush() # Para obtener new_order.id
    
    for split_item in items_to_split:
        item_id = split_item.item_id
        qty_to_split = split_item.quantity
        
        if qty_to_split <= 0:
            continue
            
        # Buscar el item en la orden original
        orig_item = next((i for i in original_order.items if i.id == item_id), None)
        if not orig_item:
            raise ValueError(f"El ítem {item_id} no pertenece a la orden {original_order_id}.")
            
        if orig_item.status == OrderStatus.CANCELLED:
            raise ValueError(f"El ítem {item_id} está cancelado y no se puede dividir.")
            
        if qty_to_split > orig_item.quantity:
            raise ValueError(f"Cantidad a dividir ({qty_to_split}) mayor que la existente ({orig_item.quantity}) para el ítem {item_id}.")
            
        if qty_to_split == orig_item.quantity:
            # Transferir el ítem completo
            orig_item.order_id = new_order.id
        else:
            # Transferencia parcial: clonar ítem y reducir cantidad original
            orig_item.quantity -= qty_to_split
            
            new_item = OrderItem(
                order_id=new_order.id,
                product_id=orig_item.product_id,
                product_variant_id=orig_item.product_variant_id,
                quantity=qty_to_split,
                unit_price=orig_item.unit_price,
                tax_rate=orig_item.tax_rate,
                tax_amount=0.0, # se recalcula luego
                status=orig_item.status,
                cook_uuid=orig_item.cook_uuid,
                cook_name=orig_item.cook_name,
                delivered_by_uuid=orig_item.delivered_by_uuid,
                delivered_by_name=orig_item.delivered_by_name,
                preparing_at=orig_item.preparing_at,
                ready_at=orig_item.ready_at,
                delivered_at=orig_item.delivered_at
            )
            session.add(new_item)
            await session.flush()
            
            # Clonar modificadores si existen
            if orig_item.modifiers:
                for mod in orig_item.modifiers:
                    new_item.modifiers.append(mod)

    # Recalcular totales para ambas órdenes
    from .order_lifecycle_service import recalculate_order_totals
    await recalculate_order_totals(session, original_order.id)
    await recalculate_order_totals(session, new_order.id)
    
    # Registrar auditoría
    items_log = [{"item_id": i.item_id, "quantity": i.quantity} for i in items_to_split]
    await audit_service.log_action(
        session,
        category=AuditCategory.SALES,
        action="ORDER_SPLIT",
        reason="División de cuenta por productos",
        actor_uuid=actor_uuid,
        actor_name=actor_name,
        target_id=str(original_order.id),
        target_type="order",
        changes_json=json.dumps({
            "new_order_id": new_order.id,
            "items_split": items_log
        })
    )
    
    await session.commit()
    await session.refresh(new_order)
    return new_order
