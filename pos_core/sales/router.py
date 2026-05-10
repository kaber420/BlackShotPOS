from fastapi import APIRouter, Depends, HTTPException, Request, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.database import get_session
from .models import Order, OrderItem, Payment, OrderType, OrderStatus, PaymentMethod
from pos_core.sales.services import (
    order_lifecycle_service as order_service,
    order_item_service,
    order_action_service
)
from pos_core.sales import payment_service
from pos_core.events.service import trigger_broadcast, trigger_standard_broadcasts
from pos_core.auth.dependencies import require_role, require_permission
from pos_core.roles import Permission
from typing import List, Optional
from pydantic import BaseModel
import asyncio
from pos_core.sales.schemas import OrderRead, SplitOrderCreate

router = APIRouter()

class OrderCreate(BaseModel):
    type: OrderType
    table_id: Optional[int] = None
    external_reference: Optional[str] = None

class OrderItemCreate(BaseModel):
    product_id: int
    product_variant_id: Optional[int] = None
    quantity: int = 1
    modifier_ids: List[int] = []

class PaymentCreate(BaseModel):
    method: PaymentMethod
    amount: float
    tip_amount: float = 0.0
    received_amount: Optional[float] = None
    vacate_table: bool = True

class TableTransferCreate(BaseModel):
    new_table_id: int

@router.post("/orders", response_model=Order)
async def create_new_order(
    order_in: OrderCreate,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.TAKE_ORDERS)),
):
    """Crea una nueva orden y registra al mesero creador."""
    order = await order_service.create_order(
        db,
        order_in.type,
        order_in.table_id,
        order_in.external_reference,
        waiter_uuid=str(user.id),
        waiter_name=user.email,
    )
    asyncio.create_task(trigger_standard_broadcasts())
    return order

@router.get("/orders", response_model=List[OrderRead])
async def list_orders(
    status: Optional[OrderStatus] = None,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.VIEW_ORDERS)) 
):
    """Lista las órdenes serializadas con ítems."""
    return await order_service.get_orders(db, status)

@router.get("/orders/{order_id}", response_model=OrderRead)
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.VIEW_ORDERS))
):
    """Obtiene el detalle completo de una orden serializada."""
    order = await order_service.get_order_with_relations(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

@router.post("/orders/{order_id}/items", response_model=OrderItem)
async def add_item(
    order_id: int,
    item_in: OrderItemCreate,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.TAKE_ORDERS))
):
    """Añade un producto a la orden."""
    order = await order_service.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    try:
        item = await order_item_service.add_item_to_order(
            db,
            order_id,
            item_in.product_id,
            item_in.quantity,
            product_variant_id=item_in.product_variant_id,
            modifier_ids=item_in.modifier_ids
        )
        asyncio.create_task(trigger_standard_broadcasts())
        return item
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/orders/{order_id}/status", response_model=Order)
async def update_status(
    order_id: int,
    status: OrderStatus,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.VIEW_ORDERS)),
):
    """Actualiza el estado de una orden. Emite evento para sincronización entre módulos."""
    if status in (OrderStatus.PREPARING, OrderStatus.READY):
        raise HTTPException(
            status_code=400, 
            detail=f"El estado {status} es operativo de Cocina. Use los endpoints de /kitchen para esto."
        )
    order = await order_service.update_order_status(
        db,
        order_id,
        status,
        actor_uuid=str(user.id),
        actor_name=user.email,
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    asyncio.create_task(trigger_standard_broadcasts())

    return order

@router.patch("/orders/{order_id}/items/{item_id}/status", response_model=OrderItem)
async def update_item_status(
    order_id: int,
    item_id: int,
    status: OrderStatus,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.VIEW_ORDERS)),
):
    """Actualiza el estado de un ítem individual. Emite evento para sincronización entre módulos."""
    if status in (OrderStatus.PREPARING, OrderStatus.READY):
        raise HTTPException(
            status_code=400, 
            detail=f"El estado {status} es operativo de Cocina. Use los endpoints de /kitchen para esto."
        )
    item = await order_item_service.update_order_item_status(
        db,
        order_id,
        item_id,
        status,
        actor_uuid=str(user.id),
        actor_name=user.email,
    )
    if not item:
        raise HTTPException(status_code=404, detail="OrderItem not found")
    asyncio.create_task(trigger_standard_broadcasts())

    return item

@router.post("/orders/{order_id}/split", response_model=OrderRead)
async def split_order(
    order_id: int,
    split_in: SplitOrderCreate,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.TAKE_ORDERS))
):
    """
    Divide una orden existente separando los ítems especificados en una nueva orden.
    """
    try:
        new_order = await order_action_service.split_order_items(
            session=db,
            original_order_id=order_id,
            items_to_split=split_in.items,
            actor_uuid=str(user.id),
            actor_name=user.email
        )
        asyncio.create_task(trigger_standard_broadcasts())
        # Cargar relaciones completas para la respuesta
        full_order = await order_service.get_order_with_relations(db, new_order.id)
        return full_order
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/orders/{order_id}")
async def delete_order(
    order_id: int,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.TAKE_ORDERS))
):
    """
    Elimina físicamente una orden vacía. 
    Lanza error 400 si tiene artículos para proteger auditoría.
    """
    try:
        success = await order_service.delete_order(db, order_id)
        if not success:
            raise HTTPException(status_code=404, detail="Order not found")
        
        asyncio.create_task(trigger_standard_broadcasts())
        return {"status": "success", "message": "Orden eliminada y mesa liberada"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/orders/{order_id}/payments", response_model=Payment)
async def pay_order(
    order_id: int,
    payment_in: PaymentCreate,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.CHARGE)),
):
    """
    Registra un pago. Si vacate_table=True, libera la mesa en una operación separada.
    El Router orquesta ambos dominios (pagos + mesas) sin acoplarlos entre sí.
    """
    order = await order_service.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # 1. Registrar el pago (dominio financiero puro)
    # Se pasa el flag vacate_table para que el módulo de Mesas reaccione vía EDA
    payment = await payment_service.add_payment(
        db, 
        order_id, 
        payment_in.method, 
        payment_in.amount,
        tip_amount=payment_in.tip_amount,
        received_amount=payment_in.received_amount,
        vacate_table=payment_in.vacate_table
    )

    # 3. Broadcasts
    asyncio.create_task(trigger_standard_broadcasts())

    return payment

@router.post("/orders/{order_id}/transfer", response_model=Order)
async def transfer_order(
    order_id: int,
    transfer_in: TableTransferCreate,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.TAKE_ORDERS)),
):
    """
    Mueve una orden a una nueva mesa, liberando la actual y preservando el tiempo de ocupación.
    """
    order = await order_service.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    old_table_id = order.table_id

    try:
        updated_order = await order_action_service.transfer_order_table(
            db,
            order_id,
            transfer_in.new_table_id,
            actor_uuid=str(user.id),
            actor_name=user.email,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Broadcasts para actualizar todos los clientes
    asyncio.create_task(trigger_standard_broadcasts())

    return updated_order
