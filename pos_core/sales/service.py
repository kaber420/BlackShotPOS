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
    external_reference: Optional[str] = None
) -> Order:
    active_shift = await get_active_shift(session)
    shift_id = active_shift.id if active_shift else None
    
    db_order = Order(
        type=order_type,
        table_id=table_id,
        shift_id=shift_id,
        external_reference=external_reference,
        status=OrderStatus.PENDING
    )
    session.add(db_order)
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
    amount: float
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
        
    await session.commit()
    await session.refresh(payment)
    return payment

def format_order_json(order: Order) -> dict:
    """Format an order object into a serializable dict with full nested details."""
    items_data = []
    for item in (order.items or []):
        items_data.append({
            "id": item.id,
            "product_id": item.product_id,
            "product": {"id": item.product.id, "name": item.product.name} if item.product else None,
            "variant": {
                "id": item.variant.id, 
                "measure": {"id": item.variant.measure.id, "name": item.variant.measure.name} if item.variant and item.variant.measure else (item.variant.measure if item.variant else None),
                "price": item.variant.price
            } if item.variant else None,
            "quantity": item.quantity,
            "unit_price": item.unit_price,
            "modifiers": [{"id": m.id, "name": m.name, "extra_price": m.extra_price} for m in (item.modifiers or [])],
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
    new_status: OrderStatus
) -> Optional[Order]:
    # We need to eager load items to use them for depletion, or just query them
    statement = select(Order).where(Order.id == order_id)
    result = await session.execute(statement)
    order = result.scalar_one_or_none()
    
    if order:
        old_status = order.status
        order.status = new_status
        await session.commit()
        await session.refresh(order)
        
        # Deplete inventory when transitioning from PENDING to PREPARING
        # O si movemos a READY/DELIVERED directamente (casos especiales)
        if old_status == OrderStatus.PENDING and new_status in (OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.DELIVERED):
            # Fetch order items WITH modifiers explicitly
            from sqlalchemy.orm import selectinload
            items_statement = select(OrderItem).where(OrderItem.order_id == order_id).options(selectinload(OrderItem.modifiers))
            items_result = await session.execute(items_statement)
            order_items = items_result.scalars().all()
            
            await process_inventory_depletion(session, order_items)
            
    return order


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
