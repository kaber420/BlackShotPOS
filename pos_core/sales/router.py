from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.database import get_session
from .models import Order, OrderItem, Payment, OrderType, OrderStatus, PaymentMethod
from . import service
from omni_auth.security import require_role
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()

class OrderCreate(BaseModel):
    type: OrderType
    table_id: Optional[int] = None
    external_reference: Optional[str] = None

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = 1

class PaymentCreate(BaseModel):
    method: PaymentMethod
    amount: float

@router.post("/orders", response_model=Order)
async def create_new_order(
    order_in: OrderCreate,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role("waiter")) # Asumiendo que cashier y admin heredan en auth o se maneja aparte
):
    """Crea una nueva orden."""
    # Note: require_role might need adjustment if multiple roles are allowed, but keeping it simple based on the plan.
    order = await service.create_order(
        db, order_in.type, order_in.table_id, order_in.external_reference
    )
    return order

@router.get("/orders", response_model=List[Order])
async def list_orders(
    status: Optional[OrderStatus] = None,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role("kitchen")) 
):
    """Lista las órdenes. Útil para cocina y cajeros."""
    return await service.get_orders(db, status)

@router.post("/orders/{order_id}/items", response_model=OrderItem)
async def add_item(
    order_id: int,
    item_in: OrderItemCreate,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role("waiter"))
):
    """Añade un producto a la orden."""
    order = await service.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    try:
        return await service.add_item_to_order(
            db, order_id, item_in.product_id, item_in.quantity
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/orders/{order_id}/status", response_model=Order)
async def update_status(
    order_id: int,
    status: OrderStatus,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role("kitchen"))
):
    """Actualiza el estado de una orden. (Ej. PENDING -> PREPARING -> READY)"""
    order = await service.update_order_status(db, order_id, status)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.post("/orders/{order_id}/payments", response_model=Payment)
async def pay_order(
    order_id: int,
    payment_in: PaymentCreate,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role("cashier"))
):
    """Registra un pago para una orden."""
    order = await service.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
        
    payment = await service.add_payment(db, order_id, payment_in.method, payment_in.amount)
    # Automatically mark order as PAID if fully paid can be added here
    await service.update_order_status(db, order_id, OrderStatus.PAID)
    return payment
