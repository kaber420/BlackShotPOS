from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Table
from typing import List, Optional

async def create_table(session: AsyncSession, number: int, capacity: int = 4, location: Optional[str] = None) -> Table:
    """Registra una nueva mesa."""
    db_table = Table(number=number, capacity=capacity, location=location)
    session.add(db_table)
    await session.commit()
    await session.refresh(db_table)
    return db_table

async def get_tables(session: AsyncSession, include_inactive: bool = False) -> List[Table]:
    """Obtiene el listado de todas las mesas activas."""
    statement = select(Table)
    if not include_inactive:
        statement = statement.where(Table.is_active == True)
    result = await session.execute(statement)
    return result.scalars().all()

async def update_table_status(session: AsyncSession, table_id: int, status: str) -> Optional[Table]:
    """Actualiza solo el estado de la mesa (Libre, Ocupada, Reservada)."""
    db_table = await session.get(Table, table_id)
    if not db_table:
        return None
    db_table.status = status
    session.add(db_table)
    await session.commit()
    await session.refresh(db_table)
    return db_table

async def update_table(session: AsyncSession, table_id: int, **kwargs) -> Optional[Table]:
    """Actualiza propiedades de una mesa."""
    db_table = await session.get(Table, table_id)
    if not db_table:
        return None
    for key, value in kwargs.items():
        if hasattr(db_table, key):
            setattr(db_table, key, value)
    session.add(db_table)
    await session.commit()
    await session.refresh(db_table)
    return db_table

async def delete_table(session: AsyncSession, table_id: int) -> bool:
    """Eliminación lógica de una mesa."""
    db_table = await session.get(Table, table_id)
    if not db_table:
        return False
    db_table.is_active = False
    session.add(db_table)
    await session.commit()
    return True

async def get_table_by_id(session: AsyncSession, table_id: int) -> Optional[Table]:
    """Obtiene una mesa específica por su ID."""
    return await session.get(Table, table_id)

async def vacate_table_service(
    session: AsyncSession, table_id: int
) -> Optional[dict]:
    """
    Libera una mesa, calcula el tiempo de ocupación y retorna estadísticas.
    Puede ser llamada por el Router al pagar, o por order_service al cancelar.
    """
    from datetime import datetime, timezone

    db_table = await session.get(Table, table_id)
    if not db_table:
        return None

    occupied_at = db_table.occupied_at
    if occupied_at and occupied_at.tzinfo is None:
        occupied_at = occupied_at.replace(tzinfo=timezone.utc)

    res = {
        "table_id":        table_id,
        "number":          db_table.number,
        "occupied_at":     occupied_at.isoformat() if occupied_at else None,
        "vacated_at":      datetime.now(timezone.utc).isoformat(),
        "duration_minutes": 0,
    }

    if occupied_at:
        delta = datetime.now(timezone.utc) - occupied_at
        res["duration_minutes"] = round(delta.total_seconds() / 60, 2)

    db_table.status = "Free"
    db_table.occupied_at = None
    session.add(db_table)
    await session.commit()

    return res
