from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import selectinload
from sqlmodel import select
from fastapi import HTTPException
from datetime import datetime, timezone
from uuid import UUID

from .models import Shift, ShiftStatus, CashRegister, CashMovement, CashMovementType
from pos_core.sales.models import Order, Payment, PaymentMethod, OrderStatus

# --- CASH REGISTER MANAGEMENT ---

async def get_cash_registers(session: AsyncSession) -> List[CashRegister]:
    stmt = select(CashRegister).where(CashRegister.is_active == True)
    result = await session.execute(stmt)
    return result.scalars().all()

async def create_cash_register(session: AsyncSession, name: str) -> CashRegister:
    register = CashRegister(name=name)
    session.add(register)
    await session.commit()
    await session.refresh(register)
    return register

# --- SHIFT MANAGEMENT ---

async def get_active_shift(session: AsyncSession, user_id: Optional[UUID] = None) -> Optional[Shift]:
    statement = select(Shift).where(Shift.status == ShiftStatus.OPEN)
    if user_id:
        statement = statement.where(Shift.user_id == user_id)
    
    result = await session.execute(statement)
    return result.scalars().first()

async def enrich_shift_data(session: AsyncSession, shift: Shift) -> dict:
    """Calcula y rellena los totales en tiempo real para un turno abierto."""
    totals = await calculate_shift_totals(session, shift.id)
    data = shift.model_dump()
    data["expected_cash"] = round(shift.initial_cash + totals["cash_sales"] + totals["incomes"] - totals["expenses"] - totals["withdrawals"], 2)
    data["expected_card"] = round(totals["card_sales"], 2)
    data["expected_transfer"] = round(totals["transfer_sales"], 2)
    data["withdrawals"] = round(totals["withdrawals"], 2)
    data["expenses"] = round(totals["expenses"], 2)
    data["incomes"] = round(totals["incomes"], 2)
    return data

async def get_all_active_shifts(session: AsyncSession) -> List[dict]:
    statement = select(Shift).where(Shift.status == ShiftStatus.OPEN)
    result = await session.execute(statement)
    shifts = result.scalars().all()
    
    return [await enrich_shift_data(session, s) for s in shifts]

async def open_shift(session: AsyncSession, initial_cash: float, register_id: int, user_id: UUID) -> Shift:
    # Verificar si el usuario ya tiene un turno abierto
    active_user = await get_active_shift(session, user_id=user_id)
    if active_user:
        raise HTTPException(status_code=400, detail="User already has an open shift.")

    # Verificar si la caja ya tiene un turno abierto por alguien más
    stmt = select(Shift).where(Shift.register_id == register_id).where(Shift.status == ShiftStatus.OPEN)
    active_reg = await session.execute(stmt)
    if active_reg.scalars().first():
        raise HTTPException(status_code=400, detail="This register is already in use by another shift.")

    # Verificar que la caja exista
    register = await session.get(CashRegister, register_id)
    if not register:
        raise HTTPException(status_code=404, detail="Cash register not found")

    shift = Shift(
        initial_cash=initial_cash,
        register_id=register_id,
        user_id=user_id
    )
    session.add(shift)
    await session.commit()
    await session.refresh(shift)
    return shift

async def calculate_shift_totals(session: AsyncSession, shift_id: int):
    """Calcula los totales esperados para un turno."""
    # Pagos por método
    pay_stmt = select(Payment).join(Order).where(Order.shift_id == shift_id)
    pay_res = await session.execute(pay_stmt)
    payments = pay_res.scalars().all()

    cash_sales     = sum(p.amount for p in payments if p.method == PaymentMethod.CASH)
    card_sales     = sum(p.amount for p in payments if p.method == PaymentMethod.CARD)
    transfer_sales = sum(p.amount for p in payments if p.method == PaymentMethod.TRANSFER)

    # Movimientos de caja
    mov_stmt = select(CashMovement).where(CashMovement.shift_id == shift_id)
    mov_res = await session.execute(mov_stmt)
    movements = mov_res.scalars().all()

    incomes  = sum(m.amount for m in movements if m.type == CashMovementType.INCOME)
    expenses = sum(m.amount for m in movements if m.type == CashMovementType.EXPENSE)
    withdrawals = sum(m.amount for m in movements if m.type == CashMovementType.WITHDRAWAL)

    return {
        "cash_sales": cash_sales,
        "card_sales": card_sales,
        "transfer_sales": transfer_sales,
        "incomes": incomes,
        "expenses": expenses,
        "withdrawals": withdrawals,
    }

async def add_cash_movement(
    session: AsyncSession, 
    shift_id: int, 
    amount: float, 
    type: CashMovementType, 
    reason: str, 
    user_id: UUID
) -> CashMovement:
    shift = await session.get(Shift, shift_id)
    if not shift or shift.status == ShiftStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Active shift required for movements")

    movement = CashMovement(
        shift_id=shift_id,
        amount=amount,
        type=type,
        reason=reason,
        user_id=user_id
    )
    session.add(movement)
    await session.commit()
    await session.refresh(movement)
    return movement

async def close_shift(
    session: AsyncSession, 
    shift_id: int, 
    actual_cash: float, 
    actual_card: float = 0.0, 
    actual_transfer: float = 0.0, 
    notes: str = None
) -> Shift:
    shift = await session.get(Shift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    if shift.status == ShiftStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Shift is already closed")

    totals = await calculate_shift_totals(session, shift_id)

    # El efectivo esperado es: fondo inicial + ventas efectivo + entradas - gastos - retiros
    shift.expected_cash = shift.initial_cash + totals["cash_sales"] + totals["incomes"] - totals["expenses"] - totals["withdrawals"]
    shift.expected_card = totals["card_sales"]
    shift.expected_transfer = totals["transfer_sales"]

    shift.actual_cash = actual_cash
    shift.actual_card = actual_card
    shift.actual_transfer = actual_transfer
    
    shift.difference_cash = actual_cash - shift.expected_cash
    shift.notes = notes
    shift.status = ShiftStatus.CLOSED
    shift.end_time = datetime.now(timezone.utc)

    await session.commit()
    await session.refresh(shift)
    return shift

async def list_shifts(session: AsyncSession) -> list:
    stmt = select(Shift).order_by(Shift.start_time.desc())
    result = await session.execute(stmt)
    shifts = result.scalars().all()

    out = []
    for shift in shifts:
        totals = await calculate_shift_totals(session, shift.id)
        
        # Cálculo de Propinas (para reporte resumido)
        pay_stmt = select(Payment).join(Order).where(Order.shift_id == shift.id)
        pay_res = await session.execute(pay_stmt)
        payments = pay_res.scalars().all()
        tips_total = sum(p.tip_amount for p in payments)

        # Duración
        duration_minutes: Optional[int] = None
        if shift.end_time and shift.start_time:
            start = shift.start_time.replace(tzinfo=timezone.utc) if shift.start_time.tzinfo is None else shift.start_time
            end = shift.end_time.replace(tzinfo=timezone.utc) if shift.end_time.tzinfo is None else shift.end_time
            duration_minutes = int((end - start).total_seconds() // 60)

        out.append({
            "id": shift.id,
            "register_id": shift.register_id,
            "status": shift.status,
            "start_time": shift.start_time.isoformat() if shift.start_time else None,
            "end_time": shift.end_time.isoformat() if shift.end_time else None,
            "duration_minutes": duration_minutes,
            "initial_cash": shift.initial_cash,
            "expected_cash": shift.expected_cash,
            "actual_cash": shift.actual_cash,
            "difference_cash": shift.difference_cash,
            "sales": {
                "cash": round(totals["cash_sales"], 2),
                "card": round(totals["card_sales"], 2),
                "transfer": round(totals["transfer_sales"], 2),
                "total": round(totals["cash_sales"] + totals["card_sales"] + totals["transfer_sales"], 2),
            },
            "tips_total": round(tips_total, 2),
        })

    return out

async def get_shift_report(session: AsyncSession, shift_id: int) -> dict:
    shift = await session.get(Shift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    totals = await calculate_shift_totals(session, shift_id)
    
    # Movimientos detallados
    mov_stmt = select(CashMovement).where(CashMovement.shift_id == shift_id)
    mov_res = await session.execute(mov_stmt)
    movements = mov_res.scalars().all()
    movements_data = [
        {
            "id": m.id,
            "amount": m.amount,
            "type": m.type,
            "reason": m.reason,
            "timestamp": m.timestamp.isoformat()
        } for m in movements
    ]

    # Órdenes del turno - Detalladas para la tabla del frontend
    orders_stmt = (
        select(Order)
        .where(Order.shift_id == shift_id)
        .options(
            selectinload(Order.payments),
            selectinload(Order.items)
        )
        .order_by(Order.created_at.desc())
    )
    orders_res = await session.execute(orders_stmt)
    orders = orders_res.scalars().all()
    
    orders_list = []
    for o in orders:
        orders_list.append({
            "id": o.id,
            "total": round(o.total_amount, 2),
            "status": o.status.value if hasattr(o.status, 'value') else o.status,
            "created_at": o.created_at.isoformat(),
            "type": o.type.value if hasattr(o.type, 'value') else o.type,
            "waiter_name": o.waiter_name,
            "items_count": len(o.items) if hasattr(o, 'items') else 0
        })
    
    # Re-calculamos items_count de forma segura si no está cargado
    if orders and not hasattr(orders[0], 'items'):
        for i, o in enumerate(orders):
            from pos_core.sales.models import OrderItem
            item_count_stmt = select(sqlfunc.count(OrderItem.id)).where(OrderItem.order_id == o.id)
            item_count_res = await session.execute(item_count_stmt)
            orders_list[i]["items_count"] = item_count_res.scalar() or 0

    # Construir respuesta estructurada como espera el frontend
    return {
        "shift": {
            "id": shift.id,
            "status": shift.status,
            "start_time": shift.start_time.isoformat(),
            "end_time": shift.end_time.isoformat() if shift.end_time else None,
            "initial_cash": shift.initial_cash,
            "expected_cash": round(shift.initial_cash + totals["cash_sales"] + totals["incomes"] - totals["expenses"] - totals["withdrawals"], 2),
            "expected_card": round(totals["card_sales"], 2),
            "expected_transfer": round(totals["transfer_sales"], 2),
            "total_withdrawals": round(totals["withdrawals"], 2),
            "total_expenses": round(totals["expenses"], 2),
            "actual_cash": shift.actual_cash,
            "actual_card": shift.actual_card,
            "actual_transfer": shift.actual_transfer,
            "difference": round(shift.difference_cash or 0.0, 2),
            "notes": shift.notes
        },
        "sales": {
            "cash": round(totals["cash_sales"], 2),
            "card": round(totals["card_sales"], 2),
            "transfer": round(totals["transfer_sales"], 2),
            "total": round(totals["cash_sales"] + totals["card_sales"] + totals["transfer_sales"], 2)
        },
        "orders": orders_list,
        "movements": movements_data
    }
