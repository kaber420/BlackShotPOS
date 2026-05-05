from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.sales.services.order_lifecycle_service import get_kitchen_orders, get_orders
from pos_core.sales.schemas import OrderRead
from pos_core.sales.models import OrderStatus
from typing import Any

# Mapeos de estados amigables para dispositivos IoT (TablePads)
IOT_STATUS_STRINGS = {
    OrderStatus.PENDING: "EN COLA",
    OrderStatus.PREPARING: "PREPARANDO",
    OrderStatus.READY: "LISTO",
    OrderStatus.DELIVERED: "ENTREGADO",
    OrderStatus.PAID: "PAGADO",
    OrderStatus.CANCELLED: "CANCELADO",
}

IOT_STATUS_PROGRESS = {
    OrderStatus.PENDING: 0,
    OrderStatus.PREPARING: 50,
    OrderStatus.READY: 100,
    OrderStatus.DELIVERED: 100,
    OrderStatus.PAID: 100,
    OrderStatus.CANCELLED: 0,
}

from pos_core.events import topic_provider
from pos_core.events.iot_registry import iot_mapper

@topic_provider("kitchen_orders")
async def provide_kitchen_orders(db: AsyncSession):
    """Proveedor para el tópico 'kitchen_orders'."""
    orders = await get_kitchen_orders(db)
    return [OrderRead.model_validate(o).model_dump(mode="json") for o in orders]

@topic_provider("recent_orders")
async def provide_recent_orders(db: AsyncSession):
    """Proveedor para el tópico 'recent_orders'."""
    orders = await get_orders(db)
    data = [OrderRead.model_validate(o).model_dump(mode="json") for o in orders]
    return sorted(data, key=lambda x: x["created_at"], reverse=True)

@iot_mapper("kitchen_orders")
async def map_sales_to_iot(topic: str, data: Any):
    """Mapea actualizaciones de órdenes de cocina a dispositivos IoT."""
    from pos_core.events.service import trigger_iot_broadcast
    
    if topic == "kitchen_orders":
        for order in data:
            table_id = order.get("table_id")
            if not table_id:
                continue
            
            status_raw = order.get("status")
            status_str = IOT_STATUS_STRINGS.get(status_raw, str(status_raw))
            progress = IOT_STATUS_PROGRESS.get(status_raw, 0)
            
            await trigger_iot_broadcast(
                table_id, 
                "order_update", 
                "", 
                data={
                    "order_id": order.get("id"),
                    "status": status_str,
                    "progress": progress
                }
            )
