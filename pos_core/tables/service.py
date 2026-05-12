from sqlmodel import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from .models import Table, Reservation, ReservationStatus
from typing import List, Optional
from pos_core.events.bus import event_bus
from datetime import datetime, timezone, timedelta
from uuid import UUID

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
    
    # Emitir evento de cambio de estado
    await event_bus.publish("tables.status_changed", {
        "table_id": table_id,
        "number": db_table.number,
        "new_status": status
    })
    
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

    # Emitir evento de mesa liberada
    await event_bus.publish("tables.vacated", res)

    return res

# --- Reservation Services ---

async def create_reservation(
    session: AsyncSession,
    customer_name: str,
    reservation_time: datetime,
    table_id: Optional[int] = None,
    pax: int = 2,
    customer_phone: Optional[str] = None,
    customer_id: Optional[UUID] = None,
    notes: Optional[str] = None,
    organization_id: str = "default"
) -> Reservation:
    """Registra una nueva reservación verificando conflictos."""
    
    # Validar conflictos (2 horas de margen)
    if table_id:
        # Normalizar reservation_time a naive UTC
        if reservation_time.tzinfo:
            reservation_time = reservation_time.astimezone(timezone.utc).replace(tzinfo=None)

        start_buffer = reservation_time - timedelta(hours=2)
        end_buffer = reservation_time + timedelta(hours=2)
        
        statement = select(Reservation).where(
            and_(
                Reservation.table_id == table_id,
                Reservation.status.in_([ReservationStatus.PENDING, ReservationStatus.CONFIRMED]),
                Reservation.reservation_time > start_buffer,
                Reservation.reservation_time < end_buffer
            )
        )
        conflicts = await session.execute(statement)
        if conflicts.scalars().first():
            raise ValueError("Existe un conflicto de horario para esta mesa en el rango de 2 horas.")

    db_reservation = Reservation(
        customer_name=customer_name,
        customer_phone=customer_phone,
        customer_id=customer_id,
        table_id=table_id,
        pax=pax,
        reservation_time=reservation_time,
        notes=notes,
        organization_id=organization_id
    )
    session.add(db_reservation)
    await session.commit()
    await session.refresh(db_reservation)
    
    # Emitir evento
    await event_bus.publish("tables.reservation_created", {
        "reservation_id": db_reservation.id,
        "table_id": table_id,
        "time": reservation_time.isoformat()
    })
    
    return db_reservation

async def get_reservations(
    session: AsyncSession,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[ReservationStatus] = None
) -> List[Reservation]:
    """Obtiene el listado de reservaciones con filtros."""
    statement = select(Reservation)
    if start_date:
        if start_date.tzinfo:
            start_date = start_date.astimezone(timezone.utc).replace(tzinfo=None)
        statement = statement.where(Reservation.reservation_time >= start_date)
    if end_date:
        if end_date.tzinfo:
            end_date = end_date.astimezone(timezone.utc).replace(tzinfo=None)
        statement = statement.where(Reservation.reservation_time <= end_date)
    if status:
        statement = statement.where(Reservation.status == status)
    
    statement = statement.order_by(Reservation.reservation_time)
    result = await session.execute(statement)
    return result.scalars().all()

async def update_reservation_status(
    session: AsyncSession,
    reservation_id: int,
    status: ReservationStatus
) -> Optional[Reservation]:
    """Actualiza el estado de una reservación."""
    db_res = await session.get(Reservation, reservation_id)
    if not db_res:
        return None
    
    db_res.status = status
    session.add(db_res)
    await session.commit()
    await session.refresh(db_res)
    
    return db_res

async def check_in_reservation(
    session: AsyncSession,
    reservation_id: int,
    waiter_uuid: Optional[str] = None,
    waiter_name: Optional[str] = None
) -> Optional[dict]:
    """Procesa la llegada del cliente reservado."""
    from pos_core.sales.services.order_lifecycle_service import create_order
    from pos_core.sales.models import OrderType

    db_res = await session.get(Reservation, reservation_id)
    if not db_res or db_res.status in [ReservationStatus.COMPLETED, ReservationStatus.CANCELLED]:
        return None

    # 1. Marcar reserva como completada
    db_res.status = ReservationStatus.COMPLETED
    session.add(db_res)
    
    # 2. Actualizar mesa si aplica
    if db_res.table_id:
        await update_table_status(session, db_res.table_id, "Occupied")
        # Actualizar occupied_at
        table = await session.get(Table, db_res.table_id)
        if table:
            table.occupied_at = datetime.now(timezone.utc).replace(tzinfo=None)
            session.add(table)
        
        # 3. Abrir orden
        order = await create_order(
            session=session,
            order_type=OrderType.DINE_IN,
            table_id=db_res.table_id,
            waiter_uuid=waiter_uuid,
            waiter_name=waiter_name
        )
        # Vincular cliente si existe
        if db_res.customer_id:
            order.customer_id = db_res.customer_id
            session.add(order)
            
        await session.commit()
        
        return {
            "reservation_id": reservation_id,
            "order_id": order.id,
            "table_id": db_res.table_id
        }
    
    await session.commit()
    return {"reservation_id": reservation_id}

async def check_upcoming_reservations(session: AsyncSession):
    """
    Tarea periódica para marcar mesas como 'Reserved' si tienen una reserva pronta.
    Margen sugerido: 30 minutos antes.
    """
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    limit = now + timedelta(minutes=30)
    
    statement = select(Reservation).where(
        and_(
            Reservation.status == ReservationStatus.CONFIRMED,
            Reservation.reservation_time <= limit,
            Reservation.reservation_time >= now,
            Reservation.table_id != None
        )
    )
    result = await session.execute(statement)
    upcoming = result.scalars().all()
    
    for res in upcoming:
        table = await session.get(Table, res.table_id)
        if table and table.status == "Free":
            await update_table_status(session, res.table_id, "Reserved")
