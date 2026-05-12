from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.tables.service import get_tables
from pos_core.events import topic_provider

@topic_provider("tables")
async def provide_tables(db: AsyncSession):
    """Proveedor para el tópico 'tables'."""
    tables = await get_tables(db, include_inactive=True)
    return [t.model_dump(mode="json") for t in tables]
