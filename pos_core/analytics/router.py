from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func
from datetime import datetime, timedelta, date
from typing import Optional

from pos_core.database import get_session
from pos_core.sales.models import Order, Payment, PaymentMethod, OrderStatus, OrderItem
from pos_core.kitchen.models import KitchenTicket
from pos_core.accounting.models import Shift, ShiftStatus
from pos_core.auth.dependencies import require_permission
from pos_core.roles import Permission

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
    user=Depends(require_permission(Permission.VIEW_REPORTS)),
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
        from pos_core.catalog.models import Product
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


# ═══════════════════════════════════════════════════════════════════════════════
#  ANALYTICS DE EQUIPO
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/waiters/performance")
async def get_waiter_performance(
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.VIEW_REPORTS)),
):
    """
    Estadísticas de desempeño por mesero — órdenes creadas, ventas totales
    y tiempo promedio desde que cocina marca READY hasta que el mesero entrega (DELIVERED).
    Basado en órdenes del día de hoy.
    """
    today_start = datetime.combine(date.today(), datetime.min.time())

    # ── Órdenes creadas y ventas totales por mesero (hoy) ───────────────────
    stmt_orders = (
        select(
            Order.waiter_uuid,
            Order.waiter_name,
            func.count(func.distinct(Order.id)).label("orders_count"),
            func.sum(Payment.amount).label("total_sales"),
        )
        .outerjoin(Payment, Payment.order_id == Order.id)
        .where(
            Order.created_at >= today_start,
            Order.waiter_uuid.isnot(None),
        )
        .group_by(Order.waiter_uuid, Order.waiter_name)
    )
    result_orders = await db.execute(stmt_orders)
    rows = result_orders.all()

    waiter_stats: dict = {}
    for row in rows:
        waiter_stats[row.waiter_uuid] = {
            "waiter_uuid": row.waiter_uuid,
            "waiter_name": row.waiter_name or "Desconocido",
            "orders_count": row.orders_count or 0,
            "total_sales": round(row.total_sales or 0.0, 2),
            "avg_delivery_seconds": None,  # calculado abajo
        }

    # ── Tiempo promedio de entrega: ready_at → delivered_at ──────────────────
    # (qué tan rápido lleva el mesero el plato una vez que cocina lo marca listo)
    # Ahora consultamos KitchenTicket en lugar de Order
    stmt_times = (
        select(Order.waiter_uuid, KitchenTicket.finished_at, KitchenTicket.delivered_at)
        .join(KitchenTicket, KitchenTicket.order_id == Order.id)
        .where(
            Order.created_at >= today_start,
            KitchenTicket.finished_at.isnot(None),
            KitchenTicket.delivered_at.isnot(None),
            Order.waiter_uuid.isnot(None),
        )
    )
    result_times = await db.execute(stmt_times)
    delivery_times: dict[str, list[float]] = {}
    for row in result_times.all():
        delta = (row.delivered_at - row.finished_at).total_seconds()
        if delta >= 0:
            delivery_times.setdefault(row.waiter_uuid, []).append(delta)

    for uuid, times in delivery_times.items():
        if uuid in waiter_stats and times:
            waiter_stats[uuid]["avg_delivery_seconds"] = round(sum(times) / len(times), 1)

    return sorted(waiter_stats.values(), key=lambda x: x["orders_count"], reverse=True)


@router.get("/kitchen/performance")
async def get_kitchen_performance(
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.VIEW_REPORTS)),
):
    """
    Estadísticas de desempeño por cocinero — órdenes manejadas, ítems preparados
    y tiempo promedio de preparación (PREPARING → READY).
    Basado en órdenes del día de hoy.
    """
    today_start = datetime.combine(date.today(), datetime.min.time())

    # ── Órdenes tomadas por cada cocinero (hoy) ──────────────────────────────
    # Ahora consultamos KitchenTicket en lugar de Order
    stmt_orders = (
        select(
            KitchenTicket.cook_uuid,
            KitchenTicket.cook_name,
            func.count(func.distinct(KitchenTicket.order_id)).label("orders_handled"),
        )
        .where(
            KitchenTicket.received_at >= today_start,
            KitchenTicket.cook_uuid.isnot(None),
        )
        .group_by(KitchenTicket.cook_uuid, KitchenTicket.cook_name)
    )
    result_orders = await db.execute(stmt_orders)
    cook_stats: dict = {}
    for row in result_orders.all():
        cook_stats[row.cook_uuid] = {
            "cook_uuid": row.cook_uuid,
            "cook_name": row.cook_name or "Desconocido",
            "orders_handled": row.orders_handled or 0,
            "items_prepared": 0,    # calculado abajo
            "avg_prep_seconds": None,  # calculado abajo
        }

    # ── Tiempo promedio de preparación: started_at → finished_at ─────────────
    # Ahora consultamos KitchenTicket en lugar de Order
    stmt_times = (
        select(KitchenTicket.cook_uuid, KitchenTicket.started_at, KitchenTicket.finished_at)
        .where(
            KitchenTicket.received_at >= today_start,
            KitchenTicket.started_at.isnot(None),
            KitchenTicket.finished_at.isnot(None),
            KitchenTicket.cook_uuid.isnot(None),
        )
    )
    result_times = await db.execute(stmt_times)
    prep_times: dict[str, list[float]] = {}
    for row in result_times.all():
        delta = (row.finished_at - row.started_at).total_seconds()
        if delta >= 0:
            prep_times.setdefault(row.cook_uuid, []).append(delta)

    for uuid, times in prep_times.items():
        if uuid in cook_stats and times:
            cook_stats[uuid]["avg_prep_seconds"] = round(sum(times) / len(times), 1)

    # ── Ítems preparados por cocinero (desde KitchenTicket) ───────────────────
    stmt_items = (
        select(KitchenTicket.cook_uuid, func.count(KitchenTicket.id).label("items_count"))
        .where(
            KitchenTicket.cook_uuid.isnot(None),
            KitchenTicket.finished_at.isnot(None),
        )
        .group_by(KitchenTicket.cook_uuid)
    )
    result_items = await db.execute(stmt_items)
    for row in result_items.all():
        if row.cook_uuid in cook_stats:
            cook_stats[row.cook_uuid]["items_prepared"] = row.items_count

    return sorted(cook_stats.values(), key=lambda x: x["orders_handled"], reverse=True)


@router.get("/kitchen/dish-speed")
async def get_dish_speed(
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission(Permission.VIEW_REPORTS)),
):
    """
    Tiempo promedio de preparación por platillo (preparing_at → ready_at por ítem).
    Ordenado de más lento a más rápido para identificar cuellos de botella.
    Solo incluye ítems con ambos timestamps registrados (datos históricos acumulados).
    """
    # ── Tiempo promedio por platillo (started_at → finished_at en KitchenTicket)
    # ── Tiempo promedio por platillo (started_at → finished_at en KitchenTicket)
    # Usamos extract('epoch') para compatibilidad con PostgreSQL
    stmt = (
        select(
            KitchenTicket.product_name,
            func.count(KitchenTicket.id).label("sample_count"),
            func.avg(
                func.extract("epoch", KitchenTicket.finished_at - KitchenTicket.started_at)
            ).label("avg_seconds"),
        )
        .where(
            KitchenTicket.started_at.isnot(None),
            KitchenTicket.finished_at.isnot(None),
        )
        .group_by(KitchenTicket.product_name)
        .order_by(func.avg(
            func.extract("epoch", KitchenTicket.finished_at - KitchenTicket.started_at)
        ).desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    return [
        {
            "product_name": row.product_name,
            "avg_prep_seconds": round(row.avg_seconds or 0.0, 1),
            "sample_count": row.sample_count,
        }
        for row in rows
    ]
