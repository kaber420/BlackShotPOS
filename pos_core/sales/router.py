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

@router.websocket("/ws/pos")
async def pos_websocket(websocket: WebSocket):
    """
    WebSocket unificado para la aplicación POS.
    Utiliza un patrón de suscripción basado en el comando 'subscribe'.
    """
    await websocket.accept()
    
    # 1. Autenticación (vía query param 'token' en el handshake)
    token = websocket.query_params.get("token")
    user_info = _auth_manager.verify_token(token) if token else None
    
    if not user_info:
        await websocket.send_json({"error": "Unauthorized", "detail": "Token inválido o faltante"})
        await websocket.close(code=1008)
        return

    print(f"🔌 WebSocket POS Iniciado: Usuario {user_info.get('username')}")
    topic = None

    try:
        # Esperamos el comando de suscripción: {"action": "subscribe", "topic": "lo_que_sea"}
        data = await websocket.receive_json()
        if data.get("action") == "subscribe" and data.get("topic"):
            topic = data.get("topic")
            broadcaster.connect(websocket, topic)
            
            # Enviar el estado inicial inmediatamente para que la UI no parpadee
            async for db in get_session():
                if topic == "kitchen_orders":
                    initial_data = await service.get_kitchen_orders(db)
                    await websocket.send_json(initial_data)
                elif topic == "dashboard_stats":
                    initial_data = await service.get_dashboard_stats(db)
                    await websocket.send_json(initial_data)
                elif topic == "recent_orders":
                    # Las órdenes pueden venir ordenadas, esto lo maneja el cliente o lo podemos hacer desde BD
                    initial_data = await service.get_orders_json(db)
                    # Sort desc by date roughly
                    initial_data = sorted(initial_data, key=lambda x: x["created_at"], reverse=True)
                    await websocket.send_json(initial_data)
                break

        # Bucle de escucha para mantener la conexión viva y por si mandan más cosas
        while True:
            msg = await websocket.receive_text()
            # Podríamos soportar cambiar de topics aquí si fuera necesario
                
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"❌ Error en WebSocket POS: {e}")
    finally:
        broadcaster.disconnect(websocket, topic)
        print(f"🔌 WebSocket POS: Desconectado")


async def broadcast_updates():
    """Calcula y despacha el estado fresco a todos los suscriptores activos."""
    async for db in get_session():
        # Si hay clientes en cocina, empujamos
        if "kitchen_orders" in broadcaster.active_connections:
            kitchen_orders = await service.get_kitchen_orders(db)
            await broadcaster.broadcast("kitchen_orders", kitchen_orders)
            
        # Si hay clientes en dashboard, empujamos
        if "dashboard_stats" in broadcaster.active_connections:
            dashboard_stats = await service.get_dashboard_stats(db)
            await broadcaster.broadcast("dashboard_stats", dashboard_stats)
            
        # Si hay clientes en recent_orders, empujamos
        if "recent_orders" in broadcaster.active_connections:
            recent_orders = await service.get_orders_json(db)
            recent_orders = sorted(recent_orders, key=lambda x: x["created_at"], reverse=True)
            await broadcaster.broadcast("recent_orders", recent_orders)
        break


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
    # Background push
    asyncio.create_task(broadcast_updates())
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
        asyncio.create_task(broadcast_updates())
        return item
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/orders/{order_id}/status", response_model=Order)
async def update_status(
    order_id: int,
    status: OrderStatus,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role(["kitchen", "waiter", "cashier"])),
):
    """Actualiza el estado de una orden y notifica a todos los listeners."""
    order = await service.update_order_status(db, order_id, status)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    asyncio.create_task(broadcast_updates())
    return order

@router.delete("/orders/{order_id}")
async def delete_order(
    order_id: int,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role(["waiter", "cashier", "admin"]))
):
    """
    Elimina físicamente una orden vacía. 
    Lanza error 400 si tiene artículos para proteger auditoría.
    """
    try:
        success = await service.delete_order(db, order_id)
        if not success:
            raise HTTPException(status_code=404, detail="Order not found")
        
        asyncio.create_task(broadcast_updates())
        return {"status": "success", "message": "Orden eliminada y mesa liberada"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

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
    asyncio.create_task(broadcast_updates())
    return payment
