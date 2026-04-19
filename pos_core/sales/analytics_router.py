from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func
from datetime import datetime, timedelta, date
from typing import Optional

from pos_core.database import get_session
from .models import Order, Payment, PaymentMethod, OrderStatus, OrderItem, Shift, ShiftStatus
from omni_auth.security import require_role

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_session),
):
    """Estadísticas básicas del día para el widget del POS (sin autenticación estricta de rol)."""
    today_start = datetime.combine(date.today(), datetime.min.time())

    # Total ventas hoy
    stmt_sales = (
        select(func.sum(Payment.amount))
        .join(Order)
        .where(Payment.timestamp >= today_start, Order.status == OrderStatus.PAID)
    )
    result_sales = await db.execute(stmt_sales)
    sales_today = result_sales.scalar() or 0.0

    # Conteo de órdenes
    stmt_orders = select(func.count(Order.id)).where(Order.created_at >= today_start)
    result_orders = await db.execute(stmt_orders)
    orders_count = result_orders.scalar() or 0

    # Órdenes canceladas
    stmt_cancelled = select(func.count(Order.id)).where(
        Order.created_at >= today_start,
        Order.status == OrderStatus.CANCELLED,
    )
    result_cancelled = await db.execute(stmt_cancelled)
    cancelled_count = result_cancelled.scalar() or 0

    # Ventas por método de pago
    stmt_methods = (
        select(Payment.method, func.sum(Payment.amount))
        .where(Payment.timestamp >= today_start)
        .group_by(Payment.method)
    )
    res_methods = await db.execute(stmt_methods)
    payment_methods = [{"method": row[0].value, "total": row[1]} for row in res_methods.all()]

    return {
        "sales_today": sales_today,
        "orders_count": orders_count,
        "cancelled_count": cancelled_count,
        "payments_by_method": payment_methods,
    }


@router.get("/business-summary")
async def get_business_summary(
    period: str = Query(
        "today",
        description="Período de análisis: 'today', 'week', 'month', o 'custom'.",
    ),
    from_date: Optional[date] = Query(
        None,
        description="Fecha de inicio (solo con period='custom'). Formato: YYYY-MM-DD.",
    ),
    to_date: Optional[date] = Query(
        None,
        description="Fecha de fin (solo con period='custom'). Formato: YYYY-MM-DD.",
    ),
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role(["admin", "manager"])),
):
    """
    Resumen de negocio filtrable por período.

    - **today**: desde medianoche hasta ahora.
    - **week**: desde el lunes de la semana actual hasta ahora.
    - **month**: desde el primer día del mes actual hasta ahora.
    - **custom**: requiere `from_date` y `to_date`.

    Retorna: ventas totales, órdenes por estado, desglose por método de pago
    y number de cortes cerrados en el período.
    """
    now = datetime.utcnow()

    if period == "today":
        start = datetime.combine(now.date(), datetime.min.time())
        end = now
    elif period == "week":
        # Lunes de la semana actual
        start = datetime.combine(now.date() - timedelta(days=now.weekday()), datetime.min.time())
        end = now
    elif period == "month":
        start = datetime.combine(now.date().replace(day=1), datetime.min.time())
        end = now
    elif period == "custom":
        if not from_date or not to_date:
            raise HTTPException(
                status_code=400,
                detail="Para period='custom' se requieren from_date y to_date.",
            )
        if from_date > to_date:
            raise HTTPException(status_code=400, detail="from_date no puede ser posterior a to_date.")
        start = datetime.combine(from_date, datetime.min.time())
        end   = datetime.combine(to_date, datetime.max.time())
    else:
        raise HTTPException(
            status_code=400,
            detail="Período inválido. Opciones: today, week, month, custom.",
        )

    # ── Ventas totales ───────────────────────────────────────────────────────
    stmt_sales = (
        select(func.sum(Payment.amount), func.count(Payment.id))
        .join(Order)
        .where(Payment.timestamp >= start, Payment.timestamp <= end)
    )
    res_sales = await db.execute(stmt_sales)
    row = res_sales.one()
    total_sales    = round(row[0] or 0.0, 2)
    total_payments = row[1] or 0

    # ── Órdenes por estado ───────────────────────────────────────────────────
    stmt_orders = (
        select(Order.status, func.count(Order.id))
        .where(Order.created_at >= start, Order.created_at <= end)
        .group_by(Order.status)
    )
    res_orders = await db.execute(stmt_orders)
    orders_by_status = {row[0].value: row[1] for row in res_orders.all()}

    total_orders = sum(orders_by_status.values())

    # ── Ventas por método de pago ────────────────────────────────────────────
    stmt_methods = (
        select(Payment.method, func.sum(Payment.amount))
        .where(Payment.timestamp >= start, Payment.timestamp <= end)
        .group_by(Payment.method)
    )
    res_methods = await db.execute(stmt_methods)
    by_method = {row[0].value: round(row[1] or 0.0, 2) for row in res_methods.all()}

    # ── Cortes de caja cerrados en el período ────────────────────────────────
    stmt_shifts = (
        select(func.count(Shift.id))
        .where(Shift.start_time >= start, Shift.status == ShiftStatus.CLOSED)
    )
    res_shifts = await db.execute(stmt_shifts)
    closed_shifts_count = res_shifts.scalar() or 0

    # ── Producto más vendido (top 1 por cantidad) ────────────────────────────
    stmt_top = (
        select(
            OrderItem.product_id,
            func.sum(OrderItem.quantity).label("qty"),
        )
        .join(Order)
        .where(Order.created_at >= start, Order.created_at <= end)
        .group_by(OrderItem.product_id)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
    )
    res_top = await db.execute(stmt_top)
    top_rows = res_top.all()

    # Resolver nombres de los productos top
    top_products = []
    for row in top_rows:
        from pos_core.inventory.models import Product
        product = await db.get(Product, row.product_id)
        top_products.append({
            "product_id": row.product_id,
            "name": product.name if product else "Desconocido",
            "quantity": int(row.qty),
        })

    return {
        "period": period,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "total_sales": total_sales,
        "total_orders": total_orders,
        "total_payments": total_payments,
        "orders_by_status": orders_by_status,
        "by_payment_method": by_method,
        "closed_shifts_count": closed_shifts_count,
        "top_products": top_products,
    }
