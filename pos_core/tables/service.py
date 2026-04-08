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
