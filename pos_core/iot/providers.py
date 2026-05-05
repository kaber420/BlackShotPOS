from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.iot.service import get_all_devices

from pos_core.events import topic_provider

@topic_provider("admin_iot")
async def provide_admin_iot(db: AsyncSession):
    """Proveedor para el tópico 'admin_iot'."""
    devices = await get_all_devices(db)
    return [d.model_dump(mode="json") for d in devices]
