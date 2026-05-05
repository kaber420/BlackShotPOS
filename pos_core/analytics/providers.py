from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.analytics.service import get_dashboard_stats

from pos_core.events import topic_provider

@topic_provider("dashboard_stats")
async def provide_dashboard_stats(db: AsyncSession):
    """Proveedor para el tópico 'dashboard_stats'."""
    return await get_dashboard_stats(db)
