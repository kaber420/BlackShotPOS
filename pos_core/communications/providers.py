from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.communications.service import get_intercom_history
from pos_core.events import topic_provider

@topic_provider("intercom")
async def provide_intercom_history(db: AsyncSession):
    """Proveedor para el tópico 'intercom' (rehidratación de mensajes recientes)."""
    return await get_intercom_history(db, limit=20)
