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

@topic_provider("recent_orders")
async def provide_recent_orders(db: AsyncSession):
    """
    Proveedor para el tópico 'recent_orders'.
    AHORA EN COCURA: Agrega información de Cocina en tiempo real para que el mesero vea el progreso.
    """
    from pos_core.sales.services.order_lifecycle_service import get_orders
    from pos_core.sales.schemas import OrderRead
    from pos_core.sales.models import OrderStatus
    
    orders = await get_orders(db)
    order_ids = [o.id for o in orders]
    
    if not order_ids:
        return []
        
    # Obtener estados de cocina para estas órdenes
    stmt = select(KitchenTicket).where(KitchenTicket.order_id.in_(order_ids))
    result = await db.execute(stmt)
    tickets = result.scalars().all()
    
    # Mapeo de item_id -> status de cocina
    kitchen_status_map: Dict[int, str] = {t.item_id: t.status for t in tickets}
    
    data = []
    for o in orders:
        order_dict = OrderRead.model_validate(o).model_dump(mode="json")
        item_statuses = []
        
        # Enriquecer cada item con su estado real de cocina
        for item in order_dict.get("items", []):
            item_id = item.get("id")
            if item_id in kitchen_status_map:
                k_status = kitchen_status_map[item_id]
                status_str = k_status.value if hasattr(k_status, "value") else str(k_status)
                item["status"] = status_str
                item_statuses.append(status_str)
            else:
                s = item.get("status")
                status_str = s.value if hasattr(s, "value") else str(s)
                item_statuses.append(status_str)
        
        # SINTESIS DE ESTADO DE LA ORDEN PARA LA UI
        if any(s == "PREPARING" for s in item_statuses):
            order_dict["status"] = "PREPARING"
        elif all(s in ["READY", "DELIVERED", "PAID"] for s in item_statuses) and item_statuses:
            if any(s == "READY" for s in item_statuses):
                order_dict["status"] = "READY"
            elif all(s == "DELIVERED" for s in item_statuses):
                order_dict["status"] = "DELIVERED"
        
        # FILTRO DE VISIBILIDAD: Desaparece si está PAGADA y ENTREGADA
        is_paid = o.status == OrderStatus.PAID
        is_all_delivered = all(s == "DELIVERED" for s in item_statuses) if item_statuses else True
        
        if not (is_paid and is_all_delivered):
            data.append(order_dict)
            
    return sorted(data, key=lambda x: x["created_at"], reverse=True)

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
