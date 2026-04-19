from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import selectinload
from sqlmodel import select
from fastapi import HTTPException
from datetime import datetime

from .models import Shift, ShiftStatus, Order, Payment, PaymentMethod


async def get_active_shift(session: AsyncSession) -> Optional[Shift]:
    statement = select(Shift).where(Shift.status == ShiftStatus.OPEN)
    result = await session.execute(statement)
    return result.scalars().first()


async def open_shift(session: AsyncSession, initial_cash: float) -> Shift:
    active = await get_active_shift(session)
    if active:
        raise HTTPException(status_code=400, detail="There is already an open shift.")

    shift = Shift(initial_cash=initial_cash)
    session.add(shift)
    await session.commit()
    await session.refresh(shift)
    return shift


async def close_shift(session: AsyncSession, shift_id: int, actual_cash: float) -> Shift:
    shift = await session.get(Shift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    if shift.status == ShiftStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Shift is already closed")

    # Calcular expected_cash sumando initial_cash + total de pagos en efectivo
    statement = select(Payment).join(Order).where(
        Order.shift_id == shift_id,
        Payment.method == PaymentMethod.CASH,
    )
    result = await session.execute(statement)
    cash_payments = result.scalars().all()

    total_cash_sales = sum(p.amount for p in cash_payments)

    shift.expected_cash = shift.initial_cash + total_cash_sales
    shift.actual_cash = actual_cash
    shift.difference = actual_cash - shift.expected_cash
    shift.status = ShiftStatus.CLOSED
    shift.end_time = datetime.utcnow()

    await session.commit()
    await session.refresh(shift)
    return shift


async def list_shifts(session: AsyncSession) -> list:
    """
    Lista todos los turnos (activos y cerrados) con totales pre-calculados.
    Ordenados por fecha de inicio descendente (el más reciente primero).
    """
    stmt = select(Shift).order_by(Shift.start_time.desc())
    result = await session.execute(stmt)
    shifts = result.scalars().all()

    out = []
    for shift in shifts:
        # Totales de pagos de este turno
        pay_stmt = select(Payment).join(Order).where(Order.shift_id == shift.id)
        pay_res = await session.execute(pay_stmt)
        payments = pay_res.scalars().all()

        cash     = sum(p.amount for p in payments if p.method == PaymentMethod.CASH)
        card     = sum(p.amount for p in payments if p.method == PaymentMethod.CARD)
        transfer = sum(p.amount for p in payments if p.method == PaymentMethod.TRANSFER)
        total    = cash + card + transfer

        # Conteo de órdenes del turno
        order_count_stmt = select(sqlfunc.count(Order.id)).where(Order.shift_id == shift.id)
        order_count_res  = await session.execute(order_count_stmt)
        orders_count     = order_count_res.scalar() or 0

        # Duración del turno en minutos (None si aún está abierto)
        duration_minutes: Optional[int] = None
        if shift.end_time and shift.start_time:
            delta = shift.end_time - shift.start_time
            duration_minutes = int(delta.total_seconds() // 60)

        out.append({
            "id": shift.id,
            "status": shift.status,
            "start_time": shift.start_time.isoformat() if shift.start_time else None,
            "end_time": shift.end_time.isoformat() if shift.end_time else None,
            "duration_minutes": duration_minutes,
            "initial_cash": shift.initial_cash,
            "expected_cash": shift.expected_cash,
            "actual_cash": shift.actual_cash,
            "difference": shift.difference,
            "sales": {
                "cash": round(cash, 2),
                "card": round(card, 2),
                "transfer": round(transfer, 2),
                "total": round(total, 2),
            },
            "orders_count": orders_count,
        })

    return out


async def get_shift_report(session: AsyncSession, shift_id: int) -> dict:
    """
    Reporte completo de un turno.
    Incluye totales financieros y la lista completa de órdenes procesadas
    durante el turno (para auditabilidad histórica).
    """
    shift = await session.get(Shift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    # Pagos del turno para calcular totales
    pay_stmt = select(Payment).join(Order).where(Order.shift_id == shift_id)
    pay_res = await session.execute(pay_stmt)
    payments = pay_res.scalars().all()

    cash     = sum(p.amount for p in payments if p.method == PaymentMethod.CASH)
    card     = sum(p.amount for p in payments if p.method == PaymentMethod.CARD)
    transfer = sum(p.amount for p in payments if p.method == PaymentMethod.TRANSFER)

    # Órdenes del turno con sus pagos e ítems (para auditoría)
    orders_stmt = (
        select(Order)
        .where(Order.shift_id == shift_id)
        .options(
            selectinload(Order.payments),
            selectinload(Order.items),
        )
        .order_by(Order.created_at)
    )
    orders_res = await session.execute(orders_stmt)
    orders_in_shift = orders_res.scalars().all()

    orders_data = [
        {
            "id": o.id,
            "type": o.type,
            "status": o.status,
            "is_paid": o.is_paid,
            "table_id": o.table_id,
            "external_reference": o.external_reference,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "items_count": len(o.items),
            "total": round(sum(p.amount for p in o.payments), 2),
        }
        for o in orders_in_shift
    ]

    # Duración del turno
    duration_minutes: Optional[int] = None
    if shift.end_time and shift.start_time:
        delta = shift.end_time - shift.start_time
        duration_minutes = int(delta.total_seconds() // 60)

    return {
        "shift_id": shift.id,
        "status": shift.status,
        "start_time": shift.start_time.isoformat() if shift.start_time else None,
        "end_time": shift.end_time.isoformat() if shift.end_time else None,
        "duration_minutes": duration_minutes,
        "initial_cash": shift.initial_cash,
        "expected_cash": shift.expected_cash,
        "actual_cash": shift.actual_cash,
        "difference": shift.difference,
        "sales": {
            "cash": round(cash, 2),
            "card": round(card, 2),
            "transfer": round(transfer, 2),
            "total": round(cash + card + transfer, 2),
        },
        "orders": orders_data,
        "orders_count": len(orders_data),
    }
