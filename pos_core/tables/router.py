from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.database import get_session
from .models import Table
from . import service
from typing import List, Optional
from pos_core.events.service import trigger_standard_broadcasts
import asyncio

router = APIRouter()

@router.get("/tables", response_model=List[Table])
async def list_tables(include_inactive: bool = False, db: AsyncSession = Depends(get_session)):
    """Estado actual de todas las mesas."""
    return await service.get_tables(db, include_inactive)

@router.post("/tables", response_model=Table)
async def create_table(number: int, capacity: int = 4, location: str = None, db: AsyncSession = Depends(get_session)):
    """Añade una mesa al sistema."""

    table = await service.create_table(db, number, capacity, location)
    asyncio.create_task(trigger_standard_broadcasts())
    return table

@router.patch("/tables/{table_id}/status", response_model=Table)
async def update_table_status(table_id: int, status: str, db: AsyncSession = Depends(get_session)):
    """Cambia el estado de una mesa (Libre, Ocupada, Reservada)."""

    table = await service.update_table_status(db, table_id, status)
    if not table:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    asyncio.create_task(trigger_standard_broadcasts())
    return table

@router.patch("/tables/{table_id}", response_model=Table)
async def update_table(table_id: int, number: Optional[int] = None, capacity: Optional[int] = None, location: Optional[str] = None, is_active: Optional[bool] = None, db: AsyncSession = Depends(get_session)):
    """Actualiza propiedades de una mesa."""

    update_data = {}
    if number is not None: update_data["number"] = number
    if capacity is not None: update_data["capacity"] = capacity
    if location is not None: update_data["location"] = location
    if is_active is not None: update_data["is_active"] = is_active
    
    table = await service.update_table(db, table_id, **update_data)
    if not table:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    asyncio.create_task(trigger_standard_broadcasts())
    return table

@router.delete("/tables/{table_id}")
async def delete_table(table_id: int, db: AsyncSession = Depends(get_session)):
    """Desactiva una mesa."""

    success = await service.delete_table(db, table_id)
    if not success:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    asyncio.create_task(trigger_standard_broadcasts())
    return {"detail": "Mesa desactivada"}

@router.post("/tables/{table_id}/vacate")
async def vacate_table(table_id: int, db: AsyncSession = Depends(get_session)):
    """Libera una mesa manualmente."""
    from pos_core.tables.service import vacate_table_service
    res = await vacate_table_service(db, table_id)
    if not res:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    asyncio.create_task(trigger_standard_broadcasts())
    return res
