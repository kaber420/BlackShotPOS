from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.tables.service import get_tables
from typing import Any

from pos_core.events import topic_provider
from pos_core.events.iot_registry import iot_mapper

@topic_provider("tables")
async def provide_tables(db: AsyncSession):
    """Proveedor para el tópico 'tables'."""
    tables = await get_tables(db, include_inactive=True)
    return [t.model_dump(mode="json") for t in tables]

@iot_mapper("tables")
async def map_tables_to_iot(topic: str, data: Any):
    """Mapea actualizaciones de mesas a dispositivos IoT."""
    from pos_core.events.service import trigger_iot_broadcast
    
    if topic == "tables":
        for table in data:
            table_id = table.get("id")
            if not table_id:
                continue
            
            # Si la mesa está libre, limpiamos el TablePad
            if not table.get("is_occupied"):
                await trigger_iot_broadcast(table_id, "clear_table", "", data={})
