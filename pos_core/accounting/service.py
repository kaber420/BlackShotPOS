from typing import Optional, List
from collections import defaultdict
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func as sqlfunc
from sqlalchemy.orm import selectinload
from sqlmodel import select
from fastapi import HTTPException
from datetime import datetime, timezone
from uuid import UUID

from .models import Shift, ShiftStatus, CashRegister, CashMovement, CashMovementType, CashMovementCategory
from pos_core.auth.models import User
from pos_core.sales.models import Order, Payment, PaymentMethod, OrderStatus, OrderItem
from pos_core.catalog.models import ProductVariant

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
    """Utiliza los totales pre-calculados en tiempo real."""
    data = shift.model_dump()
    data["expected_cash"] = round(shift.expected_cash, 2)
    data["expected_card"] = round(shift.expected_card, 2)
    data["expected_transfer"] = round(shift.expected_transfer, 2)
    
    totals = await calculate_shift_totals(session, shift.id)
    data["withdrawals"] = round(totals["withdrawals"], 2)
    data["expenses"] = round(totals["expenses"], 2)
    data["incomes"] = round(totals["incomes"], 2)

    # Cargar movimientos del turno para la tabla del frontend
    mov_stmt = (
        select(CashMovement)
        .where(CashMovement.shift_id == shift.id)
        .order_by(CashMovement.timestamp.desc())
    )
    mov_res = await session.execute(mov_stmt)
    movements = mov_res.scalars().all()

    # Resolver nombres de categorías en batch
    cat_ids = {m.category_id for m in movements if m.category_id}
    cat_map: dict[int, str] = {}
    if cat_ids:
        cat_stmt = select(CashMovementCategory).where(CashMovementCategory.id.in_(cat_ids))
        cat_res = await session.execute(cat_stmt)
        cat_map = {c.id: c.name for c in cat_res.scalars().all()}

    # Resolver nombres de actores en batch
    user_ids = {m.user_id for m in movements if m.user_id}
    user_map: dict[UUID, str] = {}
    if user_ids:
        user_stmt = select(User).where(User.id.in_(user_ids))
        user_res = await session.execute(user_stmt)
        user_map = {u.id: u.username for u in user_res.scalars().all()}

    data["movements"] = [
        {
            "id": m.id,
            "amount": m.amount,
            "type": m.type,
            "reason": m.reason,
            "category_id": m.category_id,
            "category_name": cat_map.get(m.category_id) if m.category_id else None,
            "actor_name": user_map.get(m.user_id, "Sistema"),
            "timestamp": m.timestamp.isoformat()
        } for m in movements
    ]

    return data

async def get_all_active_shifts(session: AsyncSession) -> List[dict]:
    statement = select(Shift).where(Shift.status == ShiftStatus.OPEN)
    result = await session.execute(statement)
    shifts = result.scalars().all()
    
    return [await enrich_shift_data(session, s) for s in shifts]

async def open_shift(session: AsyncSession, initial_cash: float, user_id: UUID, register_id: Optional[int] = None) -> Shift:
    # Verificar si el usuario ya tiene un turno abierto
    active_user = await get_active_shift(session, user_id=user_id)
    if active_user:
        raise HTTPException(status_code=400, detail="User already has an open shift.")

    # Si se proporciona una caja física, verificar que no esté ocupada
    if register_id:
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
        expected_cash=initial_cash, # Inicializamos con el fondo de caja
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
    user_id: UUID,
    category_id: Optional[int] = None
) -> CashMovement:
    if amount <= 0:
        raise HTTPException(status_code=422, detail="Amount must be greater than zero")

    shift = await session.get(Shift, shift_id)
    if not shift or shift.status == ShiftStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Active shift required for movements")

    # Validar que la categoría exista si se proporciona
    if category_id is not None:
        cat = await session.get(CashMovementCategory, category_id)
        if not cat:
            raise HTTPException(status_code=404, detail="Movement category not found")

    movement = CashMovement(
        shift_id=shift_id,
        amount=amount,
        type=type,
        reason=reason,
        user_id=user_id,
        category_id=category_id
    )
    session.add(movement)
    
    # Actualizar el total esperado en el turno (Atomic Update)
    from sqlalchemy import update
    stmt = update(Shift).where(Shift.id == shift_id)
    if type == CashMovementType.INCOME:
        stmt = stmt.values(expected_cash=Shift.expected_cash + amount)
    else:
        stmt = stmt.values(expected_cash=Shift.expected_cash - amount)
    
    await session.execute(stmt)
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

    # Ya no recalculamos desde cero, usamos los totales acumulados en tiempo real
    # No obstante, se mantienen los campos del modelo actualizados para el cierre final.
    # shift.expected_cash ya está actualizado por los movimientos y pagos.
    # shift.expected_card y shift.expected_transfer también.
    
    # (Opcional) Podríamos dejar el cálculo de auditoría aquí si se desea doble verificación
    # totals = await calculate_shift_totals(session, shift_id)

    shift.actual_cash = actual_cash
    shift.actual_card = actual_card
    shift.actual_transfer = actual_transfer
    
    shift.difference_cash = actual_cash - shift.expected_cash
    shift.notes = notes
    shift.status = ShiftStatus.CLOSED
    shift.end_time = datetime.now()

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
    mov_stmt = select(CashMovement).where(CashMovement.shift_id == shift_id).order_by(CashMovement.timestamp.desc())
    mov_res = await session.execute(mov_stmt)
    movements = mov_res.scalars().all()

    # Resolver categorías y actores en batch
    cat_ids = {m.category_id for m in movements if m.category_id}
    cat_map: dict[int, str] = {}
    if cat_ids:
        cat_stmt = select(CashMovementCategory).where(CashMovementCategory.id.in_(cat_ids))
        cat_res = await session.execute(cat_stmt)
        cat_map = {c.id: c.name for c in cat_res.scalars().all()}

    user_ids = {m.user_id for m in movements if m.user_id}
    user_map: dict[UUID, str] = {}
    if user_ids:
        user_stmt = select(User).where(User.id.in_(user_ids))
        user_res = await session.execute(user_stmt)
        user_map = {u.id: u.username for u in user_res.scalars().all()}

    movements_data = [
        {
            "id": m.id,
            "amount": m.amount,
            "type": m.type,
            "reason": m.reason,
            "category_id": m.category_id,
            "category_name": cat_map.get(m.category_id) if m.category_id else None,
            "actor_name": user_map.get(m.user_id, "Sistema"),
            "timestamp": m.timestamp.isoformat()
        } for m in movements
    ]

    # Desglose de gastos por categoría
    expense_by_category: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "count": 0})
    for m in movements:
        if m.type in (CashMovementType.EXPENSE, CashMovementType.WITHDRAWAL):
            cat_name = cat_map.get(m.category_id, "Sin categoría") if m.category_id else "Sin categoría"
            expense_by_category[cat_name]["total"] += m.amount
            expense_by_category[cat_name]["count"] += 1

    expense_summary = [
        {"category": k, "total": round(v["total"], 2), "count": v["count"]}
        for k, v in sorted(expense_by_category.items(), key=lambda x: -x[1]["total"])
    ]

    # Órdenes del turno - Detalladas para la tabla del frontend
    orders_stmt = (
        select(Order)
        .where(Order.shift_id == shift_id)
        .options(
            selectinload(Order.payments),
            selectinload(Order.items).selectinload(OrderItem.product),
            selectinload(Order.items).selectinload(OrderItem.variant).selectinload(ProductVariant.measure),
            selectinload(Order.items).selectinload(OrderItem.modifiers)
        )
        .order_by(Order.created_at.desc())
    )
    orders_res = await session.execute(orders_stmt)
    orders = orders_res.scalars().all()
    
    orders_list = []
    for o in orders:
        # Detalle de ítems para expansión en frontend
        items_detail = []
        for item in o.items:
            items_detail.append({
                "id": item.id,
                "name": item.product.name,
                "variant": item.variant.measure.name if item.variant and item.variant.measure else None,
                "quantity": item.quantity,
                "price": round(item.unit_price, 2),
                "modifiers": [m.name for m in item.modifiers]
            })

        orders_list.append({
            "id": o.id,
            "total": round(o.total_amount, 2),
            "status": o.status.value if hasattr(o.status, 'value') else o.status,
            "created_at": o.created_at.isoformat(),
            "type": o.type.value if hasattr(o.type, 'value') else o.type,
            "waiter_name": o.waiter_name,
            "items_count": len(o.items),
            "items": items_detail
        })

    # Totales adicionales: Impuestos y Propinas
    total_tax = sum(o.tax_amount for o in orders if o.status != OrderStatus.CANCELLED)
    
    pay_stmt = select(Payment).join(Order).where(Order.shift_id == shift_id)
    pay_res = await session.execute(pay_stmt)
    all_payments = pay_res.scalars().all()
    total_tips = sum(p.tip_amount for p in all_payments)

    # Construir respuesta estructurada como espera el frontend
    return {
        "shift": {
            "id": shift.id,
            "status": shift.status,
            "start_time": shift.start_time.isoformat(),
            "end_time": shift.end_time.isoformat() if shift.end_time else None,
            "initial_cash": shift.initial_cash,
            "expected_cash": round(shift.expected_cash, 2),
            "expected_card": round(shift.expected_card, 2),
            "expected_transfer": round(shift.expected_transfer, 2),
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
            "total": round(totals["cash_sales"] + totals["card_sales"] + totals["transfer_sales"], 2),
            "tax_total": round(total_tax, 2),
            "tips_total": round(total_tips, 2)
        },
        "orders": orders_list,
        "movements": movements_data,
        "expense_summary": expense_summary
    }

# --- MOVEMENT CATEGORIES ---

async def get_movement_categories(session: AsyncSession) -> List[CashMovementCategory]:
    """Lista todas las categorías de movimiento ordenadas por tipo y nombre."""
    stmt = select(CashMovementCategory).order_by(CashMovementCategory.type, CashMovementCategory.name)
    result = await session.execute(stmt)
    return result.scalars().all()

async def create_movement_category(
    session: AsyncSession, 
    name: str, 
    type: CashMovementType, 
    description: Optional[str] = None
) -> CashMovementCategory:
    """Crea una nueva categoría de movimiento."""
    # Verificar unicidad del nombre
    existing = await session.execute(
        select(CashMovementCategory).where(CashMovementCategory.name == name)
    )
    if existing.scalars().first():
        raise HTTPException(status_code=409, detail=f"Category '{name}' already exists")

    cat = CashMovementCategory(name=name, type=type, description=description)
    session.add(cat)
    await session.commit()
    await session.refresh(cat)
    return cat
