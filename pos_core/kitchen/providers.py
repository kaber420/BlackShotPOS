from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from .models import KitchenTicket, KitchenStatus, KitchenTicketRead
from pos_core.events import topic_provider
from pos_core.events.iot_registry import iot_mapper
from typing import List, Dict, Any

# Mapeos de estados amigables para dispositivos IoT (TablePads)
IOT_STATUS_STRINGS = {
    KitchenStatus.PENDING: "EN COLA",
    KitchenStatus.PREPARING: "PREPARANDO",
    KitchenStatus.READY: "LISTO",
    KitchenStatus.DELIVERED: "ENTREGADO",
    KitchenStatus.CANCELLED: "CANCELADO",
}

IOT_STATUS_PROGRESS = {
    KitchenStatus.PENDING: 0,
    KitchenStatus.PREPARING: 50,
    KitchenStatus.READY: 100,
    KitchenStatus.DELIVERED: 100,
    KitchenStatus.CANCELLED: 0,
}

@topic_provider("kitchen_orders")
async def provide_kitchen_orders(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Proveedor para el tópico 'kitchen_orders'.
    AHORA TOTALMENTE DESACOPLADO: Obtiene la información ÚNICAMENTE de KitchenTicket.
    Agrupa los tickets por order_id para mantener la compatibilidad con la UI del KDS.
    """
    statement = (
        select(KitchenTicket)
        .where(KitchenTicket.status.in_([KitchenStatus.PENDING, KitchenStatus.PREPARING]))
        .order_by(KitchenTicket.received_at)
        .options(selectinload(KitchenTicket.production_area))
    )
    result = await db.execute(statement)
    tickets = result.scalars().all()
    
    # Agrupamos por order_id
    orders_map: Dict[int, Dict[str, Any]] = {}
    
    for t in tickets:
        if t.order_id not in orders_map:
            # Reconstruimos el "esqueleto" de la orden desde el snapshot del ticket
            orders_map[t.order_id] = {
                "id": t.order_id,
                "table_id": t.table_id,
                "type": t.order_type,
                "waiter_name": t.waiter_name,
                "external_reference": t.external_reference,
                "status": "PREPARING", # Estado sintético para la UI
                "created_at": t.received_at.isoformat(),
                "items": []
            }
        
        # Añadimos el item (ticket)
        orders_map[t.order_id]["items"].append({
            "id": t.item_id,
            "kitchen_ticket_id": t.id,
            "product": {
                "name": t.product_name
            },
            "variant": {"measure": {"name": t.variant_name}} if t.variant_name else None,
            "modifiers": [{"name": m.strip()} for m in t.modifiers_text.split(",")] if t.modifiers_text else [],
            "status": t.status,
            "quantity": 1, # El KDS trata cada ticket como una unidad
            "unit_price": 0 # No relevante para cocina
        })
        
    # Retornamos como lista ordenada por la fecha del primer ticket de cada orden
    sorted_orders = sorted(orders_map.values(), key=lambda x: x["created_at"])
    return sorted_orders

@iot_mapper("kitchen_orders")
async def map_kitchen_to_iot(topic: str, data: Any):
    """Mapea actualizaciones de cocina a dispositivos IoT."""
    from pos_core.events.service import trigger_iot_broadcast
    
    if topic == "kitchen_orders":
        for order in data:
            table_id = order.get("table_id")
            if not table_id:
                continue
            
            # El KDS sintético ya tiene el progreso calculado o el estado directo
            status_raw = order.get("items", [{}])[0].get("status") # Usamos el primer item como referencia
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
