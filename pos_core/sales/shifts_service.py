from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
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
    statement = select(Payment).join(Order).where(Order.shift_id == shift_id, Payment.method == PaymentMethod.CASH)
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

async def get_shift_report(session: AsyncSession, shift_id: int) -> dict:
    shift = await session.get(Shift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")
        
    statement = select(Payment).join(Order).where(Order.shift_id == shift_id)
    result = await session.execute(statement)
    payments = result.scalars().all()
    
    cash = sum(p.amount for p in payments if p.method == PaymentMethod.CASH)
    card = sum(p.amount for p in payments if p.method == PaymentMethod.CARD)
    transfer = sum(p.amount for p in payments if p.method == PaymentMethod.TRANSFER)
    
    return {
        "shift_id": shift.id,
        "start_time": shift.start_time.isoformat() if shift.start_time else None,
        "end_time": shift.end_time.isoformat() if shift.end_time else None,
        "status": shift.status,
        "initial_cash": shift.initial_cash,
        "expected_cash": shift.expected_cash,
        "actual_cash": shift.actual_cash,
        "difference": shift.difference,
        "sales": {
            "cash": cash,
            "card": card,
            "transfer": transfer,
            "total": cash + card + transfer
        }
    }
