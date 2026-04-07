from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from .models import Order, OrderItem, Payment, OrderStatus, OrderType, PaymentMethod
from pos_core.inventory.models import Product, Modifier
from pos_core.inventory.service import process_inventory_depletion

async def create_order(
    session: AsyncSession, 
    order_type: OrderType, 
    table_id: Optional[int] = None, 
    external_reference: Optional[str] = None
) -> Order:
    db_order = Order(
        type=order_type,
        table_id=table_id,
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
    modifier_ids: Optional[List[int]] = None
) -> OrderItem:
    # First, get the product to find its current price
    product = await session.get(Product, product_id)
    if not product:
        raise ValueError(f"Product with id {product_id} not found")

    # Calculate extra price from modifiers
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
        quantity=quantity,
        unit_price=product.price + extra_price,
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
    await session.commit()
    await session.refresh(payment)
    return payment

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
        
        # Deplete inventory when transitioning from PENDING to PREPARING or PAID
        if old_status == OrderStatus.PENDING and new_status in (OrderStatus.PREPARING, OrderStatus.PAID):
            # Fetch order items WITH modifiers explicitly
            from sqlalchemy.orm import selectinload
            items_statement = select(OrderItem).where(OrderItem.order_id == order_id).options(selectinload(OrderItem.modifiers))
            items_result = await session.execute(items_statement)
            order_items = items_result.scalars().all()
            
            await process_inventory_depletion(session, order_items)
            
    return order
