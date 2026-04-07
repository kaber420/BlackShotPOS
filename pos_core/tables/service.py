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

async def get_tables(session: AsyncSession) -> List[Table]:
    """Obtiene el listado de todas las mesas activas."""
    statement = select(Table).where(Table.is_active == True)
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

async def get_table_by_id(session: AsyncSession, table_id: int) -> Optional[Table]:
    """Obtiene una mesa específica por su ID."""
    return await session.get(Table, table_id)
