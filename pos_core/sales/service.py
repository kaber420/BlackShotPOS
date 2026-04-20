from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from .models import Order, OrderItem, Payment, OrderStatus, OrderType, PaymentMethod
from pos_core.inventory.models import Product, Modifier, ProductVariant
from pos_core.inventory.service import process_inventory_depletion
from pos_core.sales.shifts_service import get_active_shift

async def create_order(
    session: AsyncSession,
    order_type: OrderType,
    table_id: Optional[int] = None,
    external_reference: Optional[str] = None,
    waiter_uuid: Optional[str] = None,   # UUID del mesero creador
    waiter_name: Optional[str] = None,   # Nombre snapshot para auditoría
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
        from datetime import datetime as _dt
        db_table = await session.get(Table, table_id)
        if db_table:
            if db_table.status != "Occupied":
                db_table.status = "Occupied"
                db_table.occupied_at = _dt.utcnow()
            session.add(db_table)
            
    await session.commit()
    await session.refresh(db_order)
    return db_order

async def get_order_by_id(session: AsyncSession, order_id: int) -> Optional[Order]:
    return await session.get(Order, order_id)

async def get_orders(session: AsyncSession, status: Optional[OrderStatus] = None) -> List[Order]:
    from sqlalchemy.orm import selectinload
    # Eager load items, their nested products and modifiers
    statement = select(Order).options(
        selectinload(Order.items).selectinload(OrderItem.product),
        selectinload(Order.items).selectinload(OrderItem.modifiers)
    )
    if status is not None:
        statement = statement.where(Order.status == status)
    result = await session.execute(statement)
    return result.scalars().all()
    # Note: Product name is tricky if not a relationship. OrderItem has product_id.
    # Let's ensure OrderItem has a Relationship to Product.

async def add_item_to_order(
    session: AsyncSession, 
    order_id: int,
    product_id: int, 
    quantity: int,
    product_variant_id: Optional[int] = None,
    modifier_ids: Optional[List[int]] = None
) -> OrderItem:
    # 1. Obtener el producto base
    product = await session.get(Product, product_id)
    if not product:
        raise ValueError(f"Product with id {product_id} not found")

    # 2. Determinar precio base (desde el producto o la variante)
    base_price = product.price
    variant = None
    if product_variant_id:
        from pos_core.inventory.models import ProductVariant
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

    # 4. Crear el item de la orden
    order_item = OrderItem(
        order_id=order_id,
        product_id=product_id,
        product_variant_id=product_variant_id,
        quantity=quantity,
        unit_price=base_price + extra_price,
        modifiers=modifiers
    )
    session.add(order_item)
    await session.commit()
    await session.refresh(order_item)
    return order_item

async def add_payment(
    session: AsyncSession,
    order_id: int,
    method: PaymentMethod,
    amount: float,
    vacate_table: bool = True
) -> Payment:
    payment = Payment(
        order_id=order_id,
        method=method,
        amount=amount
    )
    session.add(payment)
    
    # Marcamos la orden como pagada
    order = await session.get(Order, order_id)
    if order:
        order.is_paid = True
        
        # Liberamos la mesa si estaba asociada a una Y el usuario lo solicitó
        if order.table_id and vacate_table:
            await vacate_table_service(session, order.table_id)
        
    await session.commit()
    await session.refresh(payment)
    return payment

async def vacate_table_service(session: AsyncSession, table_id: int) -> Optional[dict]:
    """
    Libera una mesa, calcula el tiempo de ocupación y retorna estadísticas.
    """
    from pos_core.tables.models import Table
    from datetime import datetime as _dt
    db_table = await session.get(Table, table_id)
    if not db_table:
        return None
    
    res = {
        "table_id": table_id,
        "number": db_table.number,
        "occupied_at": db_table.occupied_at.isoformat() if db_table.occupied_at else None,
        "vacated_at": _dt.utcnow().isoformat(),
        "duration_minutes": 0
    }
    
    if db_table.occupied_at:
        delta = _dt.utcnow() - db_table.occupied_at
        res["duration_minutes"] = round(delta.total_seconds() / 60, 2)
    
    db_table.status = "Free"
    db_table.occupied_at = None
    session.add(db_table)
    await session.commit()
    
    return res

def format_order_json(order: Order) -> dict:
    """Format an order object into a serializable dict with full nested details."""
    items_data = []
    for item in (order.items or []):
        items_data.append({
            "id": item.id,
            "product_id": item.product_id,
            "product": {
                "id": item.product.id,
                "name": item.product.name,
                "recipe_markdown": item.product.recipe_markdown,
            } if item.product else None,
            "variant": {
                "id": item.variant.id,
                "measure": {"id": item.variant.measure.id, "name": item.variant.measure.name} if item.variant and item.variant.measure else (item.variant.measure if item.variant else None),
                "price": item.variant.price
            } if item.variant else None,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "status": item.status,
            "modifiers": [{"id": m.id, "name": m.name, "extra_price": m.extra_price} for m in (item.modifiers or [])],
            # ── Rastreo de cocina por ítem ────────────────────────────────────
            "cook_uuid": item.cook_uuid,
            "cook_name": item.cook_name,
            # ── Rastreo de entrega por ítem ───────────────────────────────────
            "delivered_by_uuid": item.delivered_by_uuid,
            "delivered_by_name": item.delivered_by_name,
            # ── Timestamps por ítem ───────────────────────────────────────────
            "preparing_at": item.preparing_at.isoformat() if item.preparing_at else None,
            "ready_at": item.ready_at.isoformat() if item.ready_at else None,
            "delivered_at": item.delivered_at.isoformat() if item.delivered_at else None,
        })
    return {
        "id": order.id,
        "type": order.type,
        "status": order.status,
        "is_paid": order.is_paid,
        "table_id": order.table_id,
        "shift_id": order.shift_id,
        "external_reference": order.external_reference,
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat(),
        # ── Rastreo del mesero ────────────────────────────────────────────────
        "waiter_uuid": order.waiter_uuid,
        "waiter_name": order.waiter_name,
        # ── Rastreo del cocinero ──────────────────────────────────────────────
        "cook_uuid": order.cook_uuid,
        "cook_name": order.cook_name,
        # ── Timestamps de la orden ────────────────────────────────────────────
        "preparing_at": order.preparing_at.isoformat() if order.preparing_at else None,
        "ready_at": order.ready_at.isoformat() if order.ready_at else None,
        "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
        "items": items_data,
    }

async def get_kitchen_orders(session: AsyncSession) -> list:
    """
    Retorna las órdenes PENDING y PREPARING como lista de dicts serializables.
    """
    from sqlalchemy.orm import selectinload
    statement = (
        select(Order)
        .where(Order.status.in_([OrderStatus.PENDING, OrderStatus.PREPARING]))
        .order_by(Order.created_at)
        .options(
            selectinload(Order.items),
            selectinload(Order.items, OrderItem.product),
            selectinload(Order.items, OrderItem.modifiers),
            selectinload(Order.items, OrderItem.variant),
            selectinload(Order.items, OrderItem.variant, ProductVariant.measure)
        )
    )
    result = await session.execute(statement)
    orders = result.unique().scalars().all()
    return [format_order_json(o) for o in orders]

async def get_orders_json(session: AsyncSession, status: Optional[OrderStatus] = None) -> List[dict]:
    """Lista órdenes serializadas como JSON."""
    from sqlalchemy.orm import selectinload
    statement = select(Order).options(
        selectinload(Order.items),
        selectinload(Order.items, OrderItem.product),
        selectinload(Order.items, OrderItem.modifiers),
        selectinload(Order.items, OrderItem.variant),
        selectinload(Order.items, OrderItem.variant, ProductVariant.measure)
    )
    if status is not None:
        statement = statement.where(Order.status == status)
    
    result = await session.execute(statement)
    orders = result.unique().scalars().all()
    return [format_order_json(o) for o in orders]

async def get_order_json(session: AsyncSession, order_id: int) -> Optional[dict]:
    """Obtiene una orden específica serializada como JSON."""
    from sqlalchemy.orm import selectinload
    statement = select(Order).where(Order.id == order_id).options(
        selectinload(Order.items),
        selectinload(Order.items, OrderItem.product),
        selectinload(Order.items, OrderItem.modifiers),
        selectinload(Order.items, OrderItem.variant),
        selectinload(Order.items, OrderItem.variant, ProductVariant.measure)
    )
    result = await session.execute(statement)
    order = result.unique().scalar_one_or_none()
    return format_order_json(order) if order else None


async def update_order_status(
    session: AsyncSession,
    order_id: int,
    new_status: OrderStatus,
    cook_uuid: Optional[str] = None,          # Cocinero que marca PREPARING / READY
    cook_name: Optional[str] = None,
    delivered_by_uuid: Optional[str] = None,  # Mesero que marca DELIVERED
    delivered_by_name: Optional[str] = None,
) -> Optional[Order]:
    from datetime import datetime as _dt
    statement = select(Order).where(Order.id == order_id)
    result = await session.execute(statement)
    order = result.scalar_one_or_none()

    if order:
        old_status = order.status
        order.status = new_status

        # ── Timestamps de ciclo de vida ───────────────────────────────────────
        if new_status == OrderStatus.PREPARING and order.preparing_at is None:
            order.preparing_at = _dt.utcnow()
            # Registrar el cocinero que tomó la orden (solo primera vez)
            if cook_uuid and order.cook_uuid is None:
                order.cook_uuid = cook_uuid
                order.cook_name = cook_name

        elif new_status == OrderStatus.READY and order.ready_at is None:
            order.ready_at = _dt.utcnow()
            # Si llegó directo a READY sin pasar por PREPARING, registrar cocinero
            if cook_uuid and order.cook_uuid is None:
                order.cook_uuid = cook_uuid
                order.cook_name = cook_name

        elif new_status == OrderStatus.DELIVERED and order.delivered_at is None:
            order.delivered_at = _dt.utcnow()

        session.add(order)

        # ── Liberar mesa si se cancela ────────────────────────────────────────
        if new_status == OrderStatus.CANCELLED and order.table_id:
            from pos_core.tables.models import Table
            db_table = await session.get(Table, order.table_id)
            if db_table:
                db_table.status = "Free"
                session.add(db_table)

        await session.commit()
        await session.refresh(order)

        # ── Cargar ítems para inventario y avance de estado ───────────────────
        from sqlalchemy.orm import selectinload
        items_statement = select(OrderItem).where(OrderItem.order_id == order_id).options(selectinload(OrderItem.modifiers))
        items_result = await session.execute(items_statement)
        order_items = items_result.scalars().all()

        if new_status in (OrderStatus.READY, OrderStatus.DELIVERED):
            items_to_deplete = [i for i in order_items if i.status == OrderStatus.PENDING]
            items_to_advance = [i for i in order_items if i.status in (OrderStatus.PENDING, OrderStatus.PREPARING, OrderStatus.READY)]
            now = _dt.utcnow()
            for i in items_to_advance:
                i.status = new_status
                # Propagar timestamps a los ítems que aún no los tienen
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
                session.add(i)
            if items_to_deplete:
                await process_inventory_depletion(session, items_to_deplete)
            if items_to_advance:
                await session.commit()

        elif old_status == OrderStatus.PENDING and new_status == OrderStatus.PREPARING:
            items_to_deplete = [i for i in order_items if i.status == OrderStatus.PENDING]
            now = _dt.utcnow()
            for i in items_to_deplete:
                i.status = OrderStatus.PREPARING
                if i.preparing_at is None:
                    i.preparing_at = now
                if cook_uuid and i.cook_uuid is None:
                    i.cook_uuid = cook_uuid
                    i.cook_name = cook_name
                session.add(i)
            if items_to_deplete:
                await process_inventory_depletion(session, items_to_deplete)
                await session.commit()

    return order

async def update_order_item_status(
    session: AsyncSession,
    order_id: int,
    item_id: int,
    new_status: OrderStatus,
    cook_uuid: Optional[str] = None,          # Cocinero que marca PREPARING / READY en el ítem
    cook_name: Optional[str] = None,
    delivered_by_uuid: Optional[str] = None,  # Mesero que entrega el ítem
    delivered_by_name: Optional[str] = None,
) -> Optional[OrderItem]:
    from datetime import datetime as _dt
    from sqlalchemy.orm import selectinload
    statement = select(OrderItem).where(OrderItem.id == item_id, OrderItem.order_id == order_id).options(selectinload(OrderItem.modifiers))
    result = await session.execute(statement)
    item = result.scalar_one_or_none()

    if not item:
        return None

    old_status = item.status
    if old_status == new_status:
        return item

    item.status = new_status

    # ── Timestamps y rastreo por ítem ─────────────────────────────────────────
    now = _dt.utcnow()
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

    session.add(item)
    
    if old_status == OrderStatus.PENDING and new_status in (OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.DELIVERED):
        await process_inventory_depletion(session, [item])
        
    # Recalcular estado de la orden padre
    order_stmt = select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    order_result = await session.execute(order_stmt)
    order = order_result.scalar_one_or_none()
    
    if order:
        all_completed = True # READY, DELIVERED or CANCELLED
        all_delivered = True # DELIVERED or CANCELLED
        all_cancelled = True
        any_preparing = False
        any_pending = False
        
        for i in order.items:
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
        if all_cancelled and len(order.items) > 0:
            new_order_status = OrderStatus.CANCELLED
            if order.table_id:
                from pos_core.tables.models import Table
                db_table = await session.get(Table, order.table_id)
                if db_table:
                    db_table.status = "Free"
                    session.add(db_table)
        elif all_delivered and len(order.items) > 0:
            new_order_status = OrderStatus.DELIVERED
        elif all_completed and len(order.items) > 0:
            new_order_status = OrderStatus.READY
        elif any_preparing:
            new_order_status = OrderStatus.PREPARING
        elif any_pending:
            new_order_status = OrderStatus.PENDING
            
        if new_order_status and new_order_status != order.status:
            # Propagar identidad al padre si el padre aún no tiene responsable
            if cook_uuid and order.cook_uuid is None:
                order.cook_uuid = cook_uuid
                order.cook_name = cook_name

            # Avoid downgrading from PAID if that was the state
            if order.status != OrderStatus.PAID:
                order.status = new_order_status
                session.add(order)
            elif new_order_status == OrderStatus.CANCELLED:
                # Cancelled can override PAID in some scenarios? 
                # Usually not, but for now let's be conservative.
                pass
            
    await session.commit()
    await session.refresh(item)
    return item

async def delete_order(session: AsyncSession, order_id: int) -> bool:
    """
    Elimina físicamente una orden si NO tiene artículos.
    Si tiene artículos, libera la mesa pero no borra por auditoría.
    """
    from sqlalchemy.orm import selectinload
    statement = select(Order).where(Order.id == order_id).options(selectinload(Order.items))
    result = await session.execute(statement)
    order = result.scalar_one_or_none()

    if not order:
        return False
    
    # Protección de auditoría: No borrar si tiene ítems
    if len(order.items) > 0:
        raise ValueError("No se puede eliminar una orden que ya contiene artículos. Use Cancelar para mantener auditoría.")

    # Liberar mesa antes de borrar
    if order.table_id:
        from pos_core.tables.models import Table
        db_table = await session.get(Table, order.table_id)
        if db_table:
            db_table.status = "Free"
            session.add(db_table)

    await session.delete(order)
    await session.commit()
    return True


async def get_dashboard_stats(session: AsyncSession) -> dict:
    """Calcula las estadísticas para el Dashboard de POS centralizando la lógica."""
    import datetime
    
    # Obtener todas las ordenes (igual que el comportamiento original)
    orders = await get_orders_json(session)
    
    preparing_count = len([o for o in orders if o["status"] in (OrderStatus.PREPARING.value, OrderStatus.PENDING.value)])
    ready_count = len([o for o in orders if o["status"] == OrderStatus.READY.value])
    
    now = datetime.datetime.now()
    start_of_today = datetime.datetime(now.year, now.month, now.day)
    
    # Start of week (Monday)
    today = now.weekday() # 0 is Monday
    start_of_week = start_of_today - datetime.timedelta(days=today)
    
    def find_best_product(filtered_orders):
        product_counts = {}
        for o in filtered_orders:
            for item in o.get("items", []):
                name = item.get("product", {}).get("name", "Producto") if item.get("product") else "Producto"
                quantity = item.get("quantity", 0)
                product_counts[name] = product_counts.get(name, 0) + quantity
                
        if not product_counts:
            return "Ninguno aún"
        
        # sort by count descending
        sorted_counts = sorted(product_counts.items(), key=lambda x: x[1], reverse=True)
        return sorted_counts[0][0]
        
    # Date parsing since the json returns isoformat strings
    today_orders = [o for o in orders if datetime.datetime.fromisoformat(o["created_at"]).replace(tzinfo=None) >= start_of_today]
    week_orders = [o for o in orders if datetime.datetime.fromisoformat(o["created_at"]).replace(tzinfo=None) >= start_of_week]

    return {
        "preparingCount": preparing_count,
        "readyCount": ready_count,
        "starProductToday": find_best_product(today_orders),
        "starProductWeek": find_best_product(week_orders)
    }
