from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from .models import KitchenTicket, KitchenStatus, KitchenTicketRead
from pos_core.events import topic_provider
from typing import List, Dict, Any



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
                "status": "PENDING", # Se actualizará abajo
                "created_at": t.received_at.isoformat(),
                "items": []
            }
        
        # Añadimos el item (ticket)
        orders_map[t.order_id]["items"].append({
            "id": t.item_id,
            "kitchen_ticket_id": t.id,
            "production_area_id": t.production_area_id,
            "product": {
                "name": t.product_name
            },
            "variant": {"measure": {"name": t.variant_name}} if t.variant_name else None,
            "modifiers": [{"name": m.strip()} for m in t.modifiers_text.split(",")] if t.modifiers_text else [],
            "status": t.status,
            "quantity": 1, # El KDS trata cada ticket como una unidad
        })
        
        # SINTESIS DE ESTADO DE LA ORDEN: Si algún item de esta área está PREPARING, la orden está PREPARING.
        # Si no, se queda como PENDING (o lo que tuviera).
        if t.status == KitchenStatus.PREPARING:
            orders_map[t.order_id]["status"] = "PREPARING"
        elif orders_map[t.order_id]["status"] != "PREPARING" and t.status == KitchenStatus.READY:
             # Si no hay nada preparando pero hay algo listo, podríamos decir READY? 
             # No, mejor PENDING hasta que TODO esté listo. 
             # Pero en el KDS, lo normal es ver PENDING (gris/amarillo) y PREPARING (azul).
             pass
        
    # Retornamos como lista ordenada por la fecha del primer ticket de cada orden
    sorted_orders = sorted(orders_map.values(), key=lambda x: x["created_at"])
    return sorted_orders

@topic_provider("recent_orders")
async def provide_recent_orders(db: AsyncSession):
    """
    Proveedor para el tópico 'recent_orders'.
    Optimizada y Desacoplada: Lee el estado físico real de Ventas,
    aprovechando la sincronización en tiempo real provista por EDA.
    """
    from pos_core.sales.services.order_lifecycle_service import get_orders
    from pos_core.sales.schemas import OrderRead
    
    orders = await get_orders(db)
    data = []
    
    for o in orders:
        order_dict = OrderRead.model_validate(o).model_dump(mode="json")
        item_statuses = []
        
        # Leemos el estado del producto directamente de la base de datos de ventas
        for item in order_dict.get("items", []):
            s = item.get("status")
            status_str = s.value if hasattr(s, "value") else str(s)
            item_statuses.append(status_str)
        
        # Síntesis rápida de estado de la orden para la UI (Meseros)
        if any(s == "PREPARING" for s in item_statuses):
            order_dict["status"] = "PREPARING"
        elif all(s in ["READY", "DELIVERED", "PAID", "CANCELLED"] for s in item_statuses) and item_statuses:
            if any(s == "READY" for s in item_statuses):
                order_dict["status"] = "READY"
            elif all(s in ["DELIVERED", "CANCELLED"] for s in item_statuses):
                order_dict["status"] = "DELIVERED"
        else:
            order_dict["status"] = "PENDING"
        
        data.append(order_dict)
            
    return sorted(data, key=lambda x: x["created_at"], reverse=True)



