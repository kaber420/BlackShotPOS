from fastapi import APIRouter, Depends, HTTPException, Request, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.database import get_session
from .models import Order, OrderItem, Payment, OrderType, OrderStatus, PaymentMethod
from pos_core.sales import order_service, payment_service, analytics_service
from pos_core.tables import service as table_service
from pos_core.events.service import trigger_broadcast, trigger_iot_broadcast
from omni_auth.security import require_role, require_permission
from pos_core.roles import Permission
from typing import List, Optional
from pydantic import BaseModel
import asyncio
from pos_core.sales.schemas import OrderRead
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
        waiter_uuid=user.get("user_uuid"),
        waiter_name=user.get("username"),
    )
    asyncio.create_task(trigger_broadcast("kitchen_orders"))
    asyncio.create_task(trigger_broadcast("recent_orders"))
    asyncio.create_task(trigger_broadcast("dashboard_stats"))
    asyncio.create_task(trigger_broadcast("tables"))
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
        item = await order_service.add_item_to_order(
            db,
            order_id,
            item_in.product_id,
            item_in.quantity,
            product_variant_id=item_in.product_variant_id,
            modifier_ids=item_in.modifier_ids
        )
        asyncio.create_task(trigger_broadcast("kitchen_orders"))
        asyncio.create_task(trigger_broadcast("recent_orders"))
        asyncio.create_task(trigger_broadcast("dashboard_stats"))
        asyncio.create_task(trigger_broadcast("tables"))
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
    """Actualiza el estado de una orden. Registra cocinero o mesero según la transición."""
    is_kitchen = status in (OrderStatus.PREPARING, OrderStatus.READY)
    is_delivery = status == OrderStatus.DELIVERED
    order = await order_service.update_order_status(
        db,
        order_id,
        status,
        cook_uuid=user.get("user_uuid") if is_kitchen else None,
        cook_name=user.get("username") if is_kitchen else None,
        delivered_by_uuid=user.get("user_uuid") if is_delivery else None,
        delivered_by_name=user.get("username") if is_delivery else None,
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    asyncio.create_task(trigger_broadcast("kitchen_orders"))
    asyncio.create_task(trigger_broadcast("recent_orders"))
    asyncio.create_task(trigger_broadcast("dashboard_stats"))
    asyncio.create_task(trigger_broadcast("tables"))

    # Notificar a IoT si la orden tiene mesa
    if order.table_id:
        # Mapeo de estados locales para IoT
        status_map = {
            OrderStatus.PENDING: ("EN COLA", 0),
            OrderStatus.PREPARING: ("PREPARANDO", 50),
            OrderStatus.READY: ("LISTO", 100),
            OrderStatus.DELIVERED: ("ENTREGADO", 100),
        }
        
        status_str, prog = status_map.get(status, (status.value, 0))
        
        asyncio.create_task(trigger_iot_broadcast(
            order.table_id, 
            "order_update", 
            "", 
            data={
                "order_id": order.id, 
                "status": status_str, 
                "progress": prog
            }
        ))

    return order

@router.patch("/orders/{order_id}/items/{item_id}/status", response_model=OrderItem)
async def update_item_status(
    order_id: int,
    item_id: int,
    status: OrderStatus,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.VIEW_ORDERS)),
):
    """Actualiza el estado de un ítem individual. Registra cocinero o mesero según la transición."""
    is_kitchen = status in (OrderStatus.PREPARING, OrderStatus.READY)
    is_delivery = status == OrderStatus.DELIVERED
    item = await order_service.update_order_item_status(
        db,
        order_id,
        item_id,
        status,
        cook_uuid=user.get("user_uuid") if is_kitchen else None,
        cook_name=user.get("username") if is_kitchen else None,
        delivered_by_uuid=user.get("user_uuid") if is_delivery else None,
        delivered_by_name=user.get("username") if is_delivery else None,
    )
    if not item:
        raise HTTPException(status_code=404, detail="OrderItem not found")
    asyncio.create_task(trigger_broadcast("kitchen_orders"))
    asyncio.create_task(trigger_broadcast("recent_orders"))
    asyncio.create_task(trigger_broadcast("dashboard_stats"))
    asyncio.create_task(trigger_broadcast("tables"))

    # Notificar a IoT si el ítem tiene mesa asociada vía la orden
    if item and status in (OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.DELIVERED):
        # Necesitamos el table_id y el nombre del producto para una mejor experiencia IoT
        async def notify_iot_item():
            from pos_core.inventory.models import Product
            async for db_session in get_session():
                # Recargar ítem con producto para el nombre
                db_item = await db_session.get(OrderItem, item_id)
                if db_item:
                    db_order = await db_session.get(Order, order_id)
                    db_product = await db_session.get(Product, db_item.product_id)
                    if db_order and db_order.table_id and db_product:
                        ev = "order_update"
                        
                        # Mapeo de estados locales para IoT
                        status_map = {
                            OrderStatus.PREPARING: ("PREPARANDO", 50),
                            OrderStatus.READY: ("LISTO", 100),
                            OrderStatus.DELIVERED: ("ENTREGADO", 100),
                        }
                        
                        status_str, prog = status_map.get(status, (status.value, 0))
                        
                        # Mapeo del estado general de la orden
                        order_status_map = {
                            OrderStatus.PENDING: "EN COLA",
                            OrderStatus.PREPARING: "PREPARANDO",
                            OrderStatus.READY: "LISTO",
                            OrderStatus.DELIVERED: "ENTREGADO"
                        }
                        
                        await trigger_iot_broadcast(db_order.table_id, ev, "", data={
                            "order_id": db_order.id, 
                            "status": order_status_map.get(db_order.status, db_order.status),
                            "progress": 100 if db_order.status == OrderStatus.READY else 50 if db_order.status == OrderStatus.PREPARING else 0,
                            "item_id": item_id,
                            "item_status": status_str,
                            "item_name": db_product.name
                        })
                break
        asyncio.create_task(notify_iot_item())

    return item

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
        
        asyncio.create_task(trigger_broadcast("kitchen_orders"))
        asyncio.create_task(trigger_broadcast("recent_orders"))
        asyncio.create_task(trigger_broadcast("dashboard_stats"))
        asyncio.create_task(trigger_broadcast("tables"))
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
    payment = await payment_service.add_payment(db, order_id, payment_in.method, payment_in.amount)

    # 2. Si el cliente se va, liberar la mesa (dominio de mesas, independiente)
    if order.table_id and payment_in.vacate_table:
        await table_service.vacate_table_service(db, order.table_id)

    # 3. Broadcasts
    asyncio.create_task(trigger_broadcast("kitchen_orders"))
    asyncio.create_task(trigger_broadcast("recent_orders"))
    asyncio.create_task(trigger_broadcast("dashboard_stats"))
    asyncio.create_task(trigger_broadcast("tables"))

    # 4. Notificar al TablePad si la mesa fue liberada
    if order.table_id and payment_in.vacate_table:
        asyncio.create_task(trigger_iot_broadcast(order.table_id, "clear_table", "", data={}))

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
        updated_order = await order_service.transfer_order_table(
            db,
            order_id,
            transfer_in.new_table_id,
            actor_uuid=user.get("user_uuid"),
            actor_name=user.get("username"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Broadcasts para actualizar todos los clientes
    asyncio.create_task(trigger_broadcast("tables"))
    asyncio.create_task(trigger_broadcast("recent_orders"))

    # Eventos IoT
    if old_table_id:
        # Limpiar la tablet de la mesa antigua
        asyncio.create_task(trigger_iot_broadcast(old_table_id, "clear_table", "", data={}))
    
    # Enviar estado actual a la nueva mesa (esto asume que la orden tiene ítems, 
    # pero enviamos un refresh general o order_update)
    asyncio.create_task(trigger_iot_broadcast(
        transfer_in.new_table_id, 
        "order_update", 
        "", 
        data={
            "order_id": updated_order.id, 
            "status": updated_order.status.value, 
            "progress": 0 # Podría mejorarse si se calcula el progreso exacto
        }
    ))

    return updated_order
