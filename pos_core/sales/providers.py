from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.sales.services.order_lifecycle_service import get_orders
from pos_core.sales.schemas import OrderRead
from pos_core.sales.models import OrderStatus
from typing import Any

from pos_core.events import topic_provider
from pos_core.events.iot_registry import iot_mapper

from pos_core.kitchen.models import KitchenTicket
from typing import Any, Dict

@topic_provider("recent_orders")
async def provide_recent_orders(db: AsyncSession):
    """
    Proveedor para el tópico 'recent_orders'.
    Agrega información de Cocina en tiempo real para que el mesero vea el progreso.
    """
    from sqlalchemy import select
    
    orders = await get_orders(db)
    order_ids = [o.id for o in orders]
    
    if not order_ids:
        return []
        
    # Obtener estados de cocina para estas órdenes (Agregación en el borde)
    stmt = select(KitchenTicket).where(KitchenTicket.order_id.in_(order_ids))
    result = await db.execute(stmt)
    tickets = result.scalars().all()
    
    # Mapeo de item_id -> status de cocina
    kitchen_status_map: Dict[int, str] = {t.item_id: t.status for t in tickets}
    
    # Validar y transformar órdenes
    data = []
    for o in orders:
        order_dict = OrderRead.model_validate(o).model_dump(mode="json")
        
        # Enriquecer cada item con su estado real de cocina
        for item in order_dict.get("items", []):
            item_id = item.get("id")
            if item_id in kitchen_status_map:
                # El estado comercial del item se "pisa" con el operativo de cocina
                # para que el mesero vea "PREPARING" o "READY"
                item["status"] = kitchen_status_map[item_id]
        
        data.append(order_dict)
        
    return sorted(data, key=lambda x: x["created_at"], reverse=True)

