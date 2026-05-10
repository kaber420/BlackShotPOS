from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.events import topic_provider
from .service import get_all_active_shifts
from typing import List, Dict, Any

@topic_provider("accounting")
async def provide_accounting_data(db: AsyncSession) -> List[Dict[str, Any]]:
    """
    Proveedor para el tópico 'accounting'.
    Retorna la información de todos los turnos activos (enriquecida con totales).
    Esto permite que el dashboard administrativo se actualice en tiempo real.
    """
    return await get_all_active_shifts(db)
