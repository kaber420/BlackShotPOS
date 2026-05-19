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

    # Cargar movimientos del turno junto con categoría y actor en un único JOIN optimizado
    mov_stmt = (
        select(CashMovement, CashMovementCategory.name.label("category_name"), User.username.label("actor_name"))
        .outerjoin(CashMovementCategory, CashMovement.category_id == CashMovementCategory.id)
        .outerjoin(User, CashMovement.user_id == User.id)
        .where(CashMovement.shift_id == shift.id)
        .order_by(CashMovement.timestamp.desc())
    )
    mov_res = await session.execute(mov_stmt)
    results = mov_res.all()

    data["movements"] = [
        {
            "id": m.id,
            "amount": m.amount,
            "type": m.type,
            "reason": m.reason,
            "category_id": m.category_id,
            "category_name": category_name,
            "actor_name": actor_name or "Sistema",
            "timestamp": m.timestamp.isoformat()
        } for m, category_name, actor_name in results
    ]

    return data

async def get_all_active_shifts(session: AsyncSession) -> List[dict]:
    statement = select(Shift).where(Shift.status == ShiftStatus.OPEN)
    result = await session.execute(statement)
    shifts = result.scalars().all()
    
    return [await enrich_shift_data(session, s) for s in shifts]

async def open_shift(session: AsyncSession, initial_cash: float, user_id: UUID, register_id: Optional[int] = None) -> Shift:
    if initial_cash < 0:
        raise HTTPException(status_code=422, detail="Initial cash cannot be negative")

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
    """Calcula los totales esperados para un turno utilizando agregaciones SQL eficientes."""
    # Agregación de pagos agrupando por método
    pay_stmt = (
        select(
            Payment.method,
            sqlfunc.coalesce(sqlfunc.sum(Payment.amount), 0.0).label("amount_sum")
        )
        .join(Order)
        .where(Order.shift_id == shift_id)
        .group_by(Payment.method)
    )
    pay_res = await session.execute(pay_stmt)
    pay_map = {method: float(amt) for method, amt in pay_res.all()}

    cash_sales = pay_map.get(PaymentMethod.CASH, 0.0)
    card_sales = pay_map.get(PaymentMethod.CARD, 0.0)
    transfer_sales = pay_map.get(PaymentMethod.TRANSFER, 0.0)

    # Agregación de movimientos de caja agrupando por tipo (excluyendo cortesías)
    mov_stmt = (
        select(
            CashMovement.type,
            sqlfunc.coalesce(sqlfunc.sum(CashMovement.amount), 0.0).label("amount_sum")
        )
        .outerjoin(CashMovementCategory, CashMovement.category_id == CashMovementCategory.id)
        .where(CashMovement.shift_id == shift_id)
        .where(
            (CashMovementCategory.name != "Gastos por Cortesías / Mermas") |
            (CashMovementCategory.name == None)
        )
        .group_by(CashMovement.type)
    )
    mov_res = await session.execute(mov_stmt)
    mov_map = {mtype: float(amt) for mtype, amt in mov_res.all()}

    incomes = mov_map.get(CashMovementType.INCOME, 0.0)
    expenses = mov_map.get(CashMovementType.EXPENSE, 0.0)
    withdrawals = mov_map.get(CashMovementType.WITHDRAWAL, 0.0)

    # Agregación separada de cortesías
    courtesy_stmt = (
        select(
            sqlfunc.coalesce(sqlfunc.sum(CashMovement.amount), 0.0)
        )
        .join(CashMovementCategory, CashMovement.category_id == CashMovementCategory.id)
        .where(CashMovement.shift_id == shift_id)
        .where(CashMovementCategory.name == "Gastos por Cortesías / Mermas")
    )
    courtesy_res = await session.execute(courtesy_stmt)
    courtesies_total = float(courtesy_res.scalar_one() or 0.0)

    return {
        "cash_sales": cash_sales,
        "card_sales": card_sales,
        "transfer_sales": transfer_sales,
        "incomes": incomes,
        "expenses": expenses,
        "withdrawals": withdrawals,
        "courtesies_total": courtesies_total
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
    
    # Actualizar el total esperado en el turno (Atomic Update) si no es una cortesía/gasto virtual
    is_courtesy = False
    if category_id:
        cat_obj = await session.get(CashMovementCategory, category_id)
        if cat_obj and cat_obj.name == "Gastos por Cortesías / Mermas":
            is_courtesy = True

    if not is_courtesy:
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
    if actual_cash < 0 or actual_card < 0 or actual_transfer < 0:
        raise HTTPException(status_code=422, detail="Actual amounts cannot be negative")

    shift = await session.get(Shift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    if shift.status == ShiftStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Shift is already closed")

    # Doble auditoría matemática al cerrar turno recalculando los totales desde la fuente de verdad en base de datos
    totals = await calculate_shift_totals(session, shift_id)
    shift.expected_cash = round(shift.initial_cash + totals["cash_sales"] + totals["incomes"] - totals["expenses"] - totals["withdrawals"], 2)
    shift.expected_card = round(totals["card_sales"], 2)
    shift.expected_transfer = round(totals["transfer_sales"], 2)

    shift.actual_cash = actual_cash
    shift.actual_card = actual_card
    shift.actual_transfer = actual_transfer
    
    shift.difference_cash = round(actual_cash - shift.expected_cash, 2)
    shift.notes = notes
    shift.status = ShiftStatus.CLOSED
    shift.end_time = datetime.now(timezone.utc).replace(tzinfo=None)

    await session.commit()
    await session.refresh(shift)
    return shift

async def list_shifts(session: AsyncSession, limit: int = 50, offset: int = 0) -> list:
    # 1. Obtener la lista base de turnos
    stmt = select(Shift).order_by(Shift.start_time.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    shifts = result.scalars().all()

    shift_ids = [s.id for s in shifts]
    if not shift_ids:
        return []

    # 2. ÚNICA CONSULTA: Obtener ventas y propinas agrupadas por shift_id y método de pago
    pay_stmt = (
        select(
            Order.shift_id,
            Payment.method,
            sqlfunc.coalesce(sqlfunc.sum(Payment.amount), 0.0).label("amount_sum"),
            sqlfunc.coalesce(sqlfunc.sum(Payment.tip_amount), 0.0).label("tip_sum")
        )
        .join(Payment, Payment.order_id == Order.id)
        .where(Order.shift_id.in_(shift_ids))
        .group_by(Order.shift_id, Payment.method)
    )
    pay_res = await session.execute(pay_stmt)

    # 3. Mapear resultados en memoria
    sales_map = {sid: {PaymentMethod.CASH: 0.0, PaymentMethod.CARD: 0.0, PaymentMethod.TRANSFER: 0.0} for sid in shift_ids}
    tips_map = {sid: 0.0 for sid in shift_ids}

    for shift_id, method, amount_sum, tip_sum in pay_res.all():
        if shift_id in sales_map:
            sales_map[shift_id][method] = float(amount_sum or 0.0)
        if shift_id in tips_map:
            tips_map[shift_id] += float(tip_sum or 0.0)

    # 4. Construir respuesta mapeada sin consultas adicionales (0 consultas adicionales en bucle)
    out = []
    for shift in shifts:
        duration_minutes: Optional[int] = None
        if shift.end_time and shift.start_time:
            start = shift.start_time.replace(tzinfo=timezone.utc) if shift.start_time.tzinfo is None else shift.start_time
            end = shift.end_time.replace(tzinfo=timezone.utc) if shift.end_time.tzinfo is None else shift.end_time
            duration_minutes = int((end - start).total_seconds() // 60)

        s_totals = sales_map.get(shift.id, {PaymentMethod.CASH: 0.0, PaymentMethod.CARD: 0.0, PaymentMethod.TRANSFER: 0.0})
        cash_sales = s_totals.get(PaymentMethod.CASH, 0.0)
        card_sales = s_totals.get(PaymentMethod.CARD, 0.0)
        transfer_sales = s_totals.get(PaymentMethod.TRANSFER, 0.0)
        tips_total = tips_map.get(shift.id, 0.0)

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
                "cash": round(cash_sales, 2),
                "card": round(card_sales, 2),
                "transfer": round(transfer_sales, 2),
                "total": round(cash_sales + card_sales + transfer_sales, 2),
            },
            "tips_total": round(tips_total, 2),
        })

    return out
async def get_shift_report(session: AsyncSession, shift_id: int) -> dict:
    shift = await session.get(Shift, shift_id)
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    totals = await calculate_shift_totals(session, shift_id)
    
    # Cargar movimientos detallados junto con categoría y actor en un único JOIN optimizado
    mov_stmt = (
        select(CashMovement, CashMovementCategory.name.label("category_name"), User.username.label("actor_name"))
        .outerjoin(CashMovementCategory, CashMovement.category_id == CashMovementCategory.id)
        .outerjoin(User, CashMovement.user_id == User.id)
        .where(CashMovement.shift_id == shift_id)
        .order_by(CashMovement.timestamp.desc())
    )
    mov_res = await session.execute(mov_stmt)
    mov_results = mov_res.all()

    movements_data = []
    expense_by_category: dict[str, dict] = defaultdict(lambda: {"total": 0.0, "count": 0})

    for m, category_name, actor_name in mov_results:
        movements_data.append({
            "id": m.id,
            "amount": m.amount,
            "type": m.type,
            "reason": m.reason,
            "category_id": m.category_id,
            "category_name": category_name,
            "actor_name": actor_name or "Sistema",
            "timestamp": m.timestamp.isoformat()
        })
        
        if m.type in (CashMovementType.EXPENSE, CashMovementType.WITHDRAWAL):
            cat_name = category_name or "Sin categoría"
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

    # Totales adicionales optimizados (evita cargar todos los pagos en memoria)
    total_tax = sum(o.tax_amount for o in orders if o.status != OrderStatus.CANCELLED)
    
    tips_stmt = select(sqlfunc.coalesce(sqlfunc.sum(Payment.tip_amount), 0.0)).join(Order).where(Order.shift_id == shift_id)
    tips_res = await session.execute(tips_stmt)
    total_tips = float(tips_res.scalar_one() or 0.0)

    # Calcular los montos esperados en tiempo real (evita valores estáticos en turnos abiertos)
    expected_cash_dyn = shift.initial_cash + totals["cash_sales"] + totals["incomes"] - totals["expenses"] - totals["withdrawals"]

    # Construir respuesta estructurada como espera el frontend
    return {
        "shift": {
            "id": shift.id,
            "status": shift.status,
            "start_time": shift.start_time.isoformat(),
            "end_time": shift.end_time.isoformat() if shift.end_time else None,
            "initial_cash": shift.initial_cash,
            "expected_cash": round(expected_cash_dyn, 2),
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
            "total": round(totals["cash_sales"] + totals["card_sales"] + totals["transfer_sales"], 2),
            "tax_total": round(total_tax, 2),
            "tips_total": round(total_tips, 2),
            "courtesies_total": round(totals.get("courtesies_total", 0.0), 2)
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
