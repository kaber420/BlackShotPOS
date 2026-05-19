from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.database import get_session
from .models import Table, Reservation, ReservationStatus
from . import service
from typing import List, Optional
from pos_core.events.service import trigger_standard_broadcasts
import asyncio
from datetime import datetime
from uuid import UUID
from pydantic import BaseModel

router = APIRouter()

class ReservationCreate(BaseModel):
    customer_name: str
    reservation_time: datetime
    table_id: Optional[int] = None
    pax: int = 2
    customer_phone: Optional[str] = None
    customer_id: Optional[UUID] = None
    notes: Optional[str] = None

@router.get("/", response_model=List[Table])
async def list_tables(include_inactive: bool = False, db: AsyncSession = Depends(get_session)):
    """Estado actual de todas las mesas."""
    # Actualizar estados basados en reservaciones próximas
    await service.check_upcoming_reservations(db)
    return await service.get_tables(db, include_inactive)

@router.post("/", response_model=Table)
async def create_table(number: int, capacity: int = 4, location: str = None, db: AsyncSession = Depends(get_session)):
    """Añade una mesa al sistema."""

    table = await service.create_table(db, number, capacity, location)
    asyncio.create_task(trigger_standard_broadcasts())
    return table

@router.patch("/{table_id}/status", response_model=Table)
async def update_table_status(table_id: int, status: str, db: AsyncSession = Depends(get_session)):
    """Cambia el estado de una mesa (Libre, Ocupada, Reservada)."""

    table = await service.update_table_status(db, table_id, status)
    if not table:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    asyncio.create_task(trigger_standard_broadcasts())
    return table

@router.patch("/{table_id}", response_model=Table)
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

@router.delete("/{table_id}")
async def delete_table(table_id: int, db: AsyncSession = Depends(get_session)):
    """Desactiva una mesa."""

    success = await service.delete_table(db, table_id)
    if not success:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    asyncio.create_task(trigger_standard_broadcasts())
    return {"detail": "Mesa desactivada"}

@router.post("/{table_id}/vacate")
async def vacate_table(table_id: int, db: AsyncSession = Depends(get_session)):
    """Libera una mesa manualmente."""
    from pos_core.tables.service import vacate_table_service
    res = await vacate_table_service(db, table_id)
    if not res:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    asyncio.create_task(trigger_standard_broadcasts())
    return res

@router.post("/{table_id}/clear-requests", response_model=Table)
async def clear_table_requests(table_id: int, db: AsyncSession = Depends(get_session)):
    """Limpia las solicitudes de mesero y cuenta de una mesa y notifica al hardware."""
    table = await service.get_table_by_id(db, table_id)
    if not table:
        raise HTTPException(status_code=404, detail="Mesa no encontrada")
    table.waiter_requested = False
    table.bill_requested = False
    db.add(table)
    await db.commit()
    await db.refresh(table)
    
    # Notificar a la UI Web
    from pos_core.events.service import trigger_broadcast
    await trigger_broadcast("tables")
    
    # Notificar al hardware IoT (TablePad)
    from pos_core.events.service import trigger_iot_broadcast
    await trigger_iot_broadcast(table_id, "clear_requests", "Solicitud atendida", data={})
    
    return table

# --- Reservations ---

@router.get("/reservations", response_model=List[Reservation])
async def list_reservations(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[ReservationStatus] = None,
    db: AsyncSession = Depends(get_session)
):
    """Lista las reservaciones filtradas por fecha y estado."""
    return await service.get_reservations(db, start_date, end_date, status)

@router.post("/reservations", response_model=Reservation)
async def create_reservation(
    data: ReservationCreate,
    db: AsyncSession = Depends(get_session)
):
    """Crea una nueva reservación."""
    try:
        res = await service.create_reservation(
            db,
            customer_name=data.customer_name,
            reservation_time=data.reservation_time,
            table_id=data.table_id,
            pax=data.pax,
            customer_phone=data.customer_phone,
            customer_id=data.customer_id,
            notes=data.notes
        )
        asyncio.create_task(trigger_standard_broadcasts())
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/reservations/{reservation_id}/status", response_model=Reservation)
async def update_reservation_status(
    reservation_id: int,
    status: ReservationStatus,
    db: AsyncSession = Depends(get_session)
):
    """Actualiza el estado de una reservación."""
    res = await service.update_reservation_status(db, reservation_id, status)
    if not res:
        raise HTTPException(status_code=404, detail="Reservación no encontrada")
    asyncio.create_task(trigger_standard_broadcasts())
    return res

@router.post("/reservations/{reservation_id}/check-in")
async def check_in_reservation(
    reservation_id: int,
    waiter_uuid: Optional[str] = None,
    waiter_name: Optional[str] = None,
    db: AsyncSession = Depends(get_session)
):
    """Realiza el check-in de una reservación."""
    res = await service.check_in_reservation(db, reservation_id, waiter_uuid, waiter_name)
    if not res:
        raise HTTPException(status_code=404, detail="Reservación no encontrada o ya procesada")
    asyncio.create_task(trigger_standard_broadcasts())
    return res
