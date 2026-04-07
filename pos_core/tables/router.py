from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.database import get_session
from .models import Table
from . import service
from typing import List

router = APIRouter()

@router.get("/tables", response_model=List[Table])
async def list_tables(db: AsyncSession = Depends(get_session)):
    """Estado actual de todas las mesas."""
    return await service.get_tables(db)

@router.post("/tables", response_model=Table)
async def create_table(number: int, capacity: int = 4, location: str = None, db: AsyncSession = Depends(get_session)):
    """Añade una mesa al sistema."""
    return await service.create_table(db, number, capacity, location)

@router.patch("/tables/{table_id}/status", response_model=Table)
async def update_table_status(table_id: int, status: str, db: AsyncSession = Depends(get_session)):
    """Cambia el estado de una mesa (Libre, Ocupada, Reservada)."""
    table = await service.update_table_status(db, table_id, status)
    if not table:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    return table
