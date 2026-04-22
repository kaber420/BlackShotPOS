"""
pos_core/sales/service.py
=========================
Capa de Servicio: contiene las reglas de negocio del módulo de ventas.

RESPONSABILIDADES:
  - Validar reglas de negocio antes de persistir.
  - Coordinar llamadas al Repositorio.
  - Controlar los límites transaccionales (session.commit).
  - NO contiene sentencias SQL/ORM directas (eso es responsabilidad del Repository).
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .models import Order, OrderItem, Payment, OrderStatus, OrderType, PaymentMethod
from pos_core.inventory.service import process_inventory_depletion
from pos_core.sales.shifts_service import get_active_shift
from pos_core.events.service import trigger_iot_broadcast
from pos_core.exceptions import OrderNotFoundError, InvalidOrderStateError
from pos_core.sales.repository import order_repo, item_repo


# ── Creación de Órdenes ────────────────────────────────────────────────────────

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

    if table_id:
        from pos_core.tables.models import Table
        db_table = await session.get(Table, table_id)
        if db_table:
            if db_table.status != "Occupied":
                db_table.status = "Occupied"
                db_table.occupied_at = datetime.now(timezone.utc)
            session.add(db_table)

    await session.commit()
    await session.refresh(db_order)
    return db_order


# ── Lectura de Órdenes ─────────────────────────────────────────────────────────

async def get_order_by_id(session: AsyncSession, order_id: int) -> Optional[Order]:
    return await order_repo.get_by_id(session, order_id)


async def get_orders(
    session: AsyncSession, status: Optional[OrderStatus] = None
) -> List[Order]:
    return await order_repo.get_all(session, status)


async def get_kitchen_orders(session: AsyncSession) -> List[Order]:
    """Retorna las órdenes PENDING y PREPARING para la pantalla KDS."""
    return await order_repo.get_active_for_kitchen(session)


async def get_orders_json(
    session: AsyncSession, status: Optional[OrderStatus] = None
) -> List[Order]:
    """Lista órdenes con todas sus relaciones cargadas (para serialización Pydantic)."""
    return await order_repo.get_all(session, status)


async def get_order_json(
    session: AsyncSession, order_id: int
) -> Optional[Order]:
    """Obtiene una orden específica con todas sus relaciones cargadas."""
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

    # 1. Obtener el producto base
    product = await session.get(Product, product_id)
    if not product:
        raise ValueError(f"Product with id {product_id} not found")

    # 2. Determinar precio base (producto o variante)
    base_price = product.price
    if product_variant_id:
        variant = await session.get(ProductVariant, product_variant_id)
        if variant:
            base_price = variant.price
        else:
            raise ValueError(f"Variant with id {product_variant_id} not found")

    # 3. Calcular extras por modificadores
    extra_price = 0.0
    modifiers = []
    if modifier_ids:
        for m_id in modifier_ids:
            mod = await session.get(Modifier, m_id)
            if mod:
                extra_price += mod.extra_price
                modifiers.append(mod)

    # 4. Crear el ítem
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


# ── Pagos ──────────────────────────────────────────────────────────────────────

async def add_payment(
    session: AsyncSession,
    order_id: int,
    method: PaymentMethod,
    amount: float,
) -> Payment:
    """
    Registra un pago y marca la orden como pagada.

    RESPONSABILIDAD ÚNICA: Solo gestiona la transacción financiera.
    La liberación de mesa es responsabilidad del Router, que llama a
    table_service.vacate_table_service() por separado si es necesario.
    """
    order = await order_repo.get_by_id(session, order_id)
    if not order:
        raise OrderNotFoundError(order_id)
    if order.is_paid:
        raise InvalidOrderStateError("Esta orden ya fue pagada.")

    payment = await order_repo.create_payment(session, order_id, method, amount)
    order.is_paid = True
    order.status = OrderStatus.PAID
    await order_repo.save(session, order)

    # El Servicio controla el único commit de la transacción
    await session.commit()
    await session.refresh(payment)
    return payment


# ── Liberación de Mesas ────────────────────────────────────────────────────────

async def vacate_table_service(
    session: AsyncSession, table_id: int
) -> Optional[dict]:
    """
    Libera una mesa, calcula el tiempo de ocupación y retorna estadísticas.
    Puede ser llamada directamente por el Router o por update_order_status al cancelar.
    """
    from pos_core.tables.models import Table

    db_table = await session.get(Table, table_id)
    if not db_table:
        return None

    res = {
        "table_id": table_id,
        "number": db_table.number,
        "occupied_at": (
            db_table.occupied_at.replace(tzinfo=timezone.utc)
            if db_table.occupied_at and db_table.occupied_at.tzinfo is None
            else db_table.occupied_at
        ).isoformat() if db_table.occupied_at else None,
        "vacated_at": datetime.now(timezone.utc).isoformat(),
        "duration_minutes": 0,
    }

    if db_table.occupied_at:
        occupied_at = db_table.occupied_at
        if occupied_at.tzinfo is None:
            occupied_at = occupied_at.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - occupied_at
        res["duration_minutes"] = round(delta.total_seconds() / 60, 2)

    db_table.status = "Free"
    db_table.occupied_at = None
    session.add(db_table)
    await session.commit()

    return res


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

    # ── Timestamps de ciclo de vida ────────────────────────────────────────────
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

    # ── Cancelación: liberar la mesa via table_service ─────────────────────────
    if new_status == OrderStatus.CANCELLED and order.table_id:
        from pos_core.tables import service as table_service
        await table_service.vacate_table_service(session, order.table_id)

    await session.commit()
    await session.refresh(order)

    # ── Propagar estado a los ítems ────────────────────────────────────────────
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

    # ── Timestamps y rastreo por ítem ─────────────────────────────────────────
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

    # ── Recalcular estado de la orden padre ────────────────────────────────────
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

            if order.status != OrderStatus.PAID:
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


# ── Eliminación de Orden ───────────────────────────────────────────────────────

async def delete_order(session: AsyncSession, order_id: int) -> bool:
    """
    Elimina físicamente una orden si NO tiene artículos.
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


# ── Dashboard ──────────────────────────────────────────────────────────────────

async def get_dashboard_stats(session: AsyncSession) -> dict:
    """Calcula estadísticas para el Dashboard de POS."""
    from datetime import timedelta
    from pos_core.sales.schemas import OrderRead

    orders_db = await get_orders_json(session)
    orders = [OrderRead.model_validate(o).model_dump(mode="json") for o in orders_db]

    preparing_count = len([
        o for o in orders
        if o["status"] in (OrderStatus.PREPARING.value, OrderStatus.PENDING.value)
    ])
    ready_count = len([o for o in orders if o["status"] == OrderStatus.READY.value])

    now = datetime.now(timezone.utc)
    start_of_today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    start_of_week = start_of_today - timedelta(days=now.weekday())

    def find_best_product(filtered_orders):
        product_counts = {}
        for o in filtered_orders:
            for item in o.get("items", []):
                name = (
                    item.get("product", {}).get("name", "Producto")
                    if item.get("product")
                    else "Producto"
                )
                product_counts[name] = product_counts.get(name, 0) + item.get("quantity", 0)
        if not product_counts:
            return "Ninguno aún"
        return sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[0][0]

    def ensure_utc(dt_str):
        dt = datetime.fromisoformat(dt_str)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

    today_orders = [o for o in orders if ensure_utc(o["created_at"]) >= start_of_today]
    week_orders = [o for o in orders if ensure_utc(o["created_at"]) >= start_of_week]

    return {
        "preparingCount": preparing_count,
        "readyCount": ready_count,
        "starProductToday": find_best_product(today_orders),
        "starProductWeek": find_best_product(week_orders),
    }
