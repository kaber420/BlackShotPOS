from fastapi import APIRouter, Depends, HTTPException, Request, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select
from pos_core.database import get_session
from .models import Order, OrderItem, Payment, OrderType, OrderStatus, PaymentMethod
from . import service
from .broadcaster import broadcaster
from omni_auth.security import require_role
from typing import List, Optional
from pydantic import BaseModel
import asyncio
from omni_auth.manager import OmniAuthManager

_auth_manager = OmniAuthManager()

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

@router.websocket("/ws/kitchen")
async def kitchen_websocket(websocket: WebSocket):
    """
    WebSocket para la cocina.
    En lugar de SSE, usamos una conexión persistente bidireccional.
    """
    await websocket.accept()
    
    # 1. Autenticación (vía query param 'token' en el handshake)
    token = websocket.query_params.get("token")
    user_info = _auth_manager.verify_token(token) if token else None
    
    if not user_info or (user_info.get("role") != "kitchen" and user_info.get("role") != "admin"):
        await websocket.send_json({"error": "Unauthorized", "detail": "Token inválido o rol insuficiente"})
        await websocket.close(code=1008)
        return

    print(f"🔌 WebSocket Cocina: Conectado usuario {user_info.get('username')}")

    try:
        # 2. Enviar estado inicial
        async for db in get_session():
            orders = await service.get_kitchen_orders(db)
            await websocket.send_json(orders)
            break

        # 3. Bucle de escucha
        while True:
            # Esperar notificación del Broadcaster
            await broadcaster.wait_for_update()
            
            # Obtener datos frescos
            async for db in get_session():
                orders = await service.get_kitchen_orders(db)
                await websocket.send_json(orders)
                break
                
    except WebSocketDisconnect:
        print("🔌 WebSocket Cocina: Desconectado")
    except Exception as e:
        print(f"❌ Error en WebSocket Cocina: {e}")
        await websocket.close(code=1011)


@router.post("/orders", response_model=Order)
async def create_new_order(
    order_in: OrderCreate,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role("waiter")),
):
    """Crea una nueva orden y notifica a la cocina en tiempo real."""
    order = await service.create_order(
        db, order_in.type, order_in.table_id, order_in.external_reference
    )
    await broadcaster.notify()
    return order

@router.get("/orders")
async def list_orders(
    status: Optional[OrderStatus] = None,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role("kitchen")) 
):
    """Lista las órdenes serializadas con ítems."""
    return await service.get_orders_json(db, status)

@router.get("/orders/{order_id}")
async def get_order(
    order_id: int,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role("kitchen"))
):
    """Obtiene el detalle completo de una orden serializada."""
    order = await service.get_order_json(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order

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
        item = await service.add_item_to_order(
            db, 
            order_id, 
            item_in.product_id, 
            item_in.quantity,
            product_variant_id=item_in.product_variant_id,
            modifier_ids=item_in.modifier_ids
        )
        await broadcaster.notify()
        return item
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/orders/{order_id}/status", response_model=Order)
async def update_status(
    order_id: int,
    status: OrderStatus,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role("kitchen")),
):
    """Actualiza el estado de una orden y notifica a todos los listeners SSE."""
    order = await service.update_order_status(db, order_id, status)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    await broadcaster.notify()
    return order

@router.post("/orders/{order_id}/payments", response_model=Payment)
async def pay_order(
    order_id: int,
    payment_in: PaymentCreate,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role("cashier")),
):
    """Registra un pago y notifica a la cocina (la orden pasa a PAID)."""
    order = await service.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    payment = await service.add_payment(db, order_id, payment_in.method, payment_in.amount)
    await broadcaster.notify()
    return payment
