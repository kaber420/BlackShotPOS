from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, func
from datetime import datetime, timedelta, date

from pos_core.database import get_session
from .models import Order, Payment, PaymentMethod, OrderStatus, OrderItem
from omni_auth.security import require_role

router = APIRouter()

@router.get("/dashboard")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role("admin")) # The UI will enforce can_view_reports but here we just check admin/manager or generic require_role mapping. Wait, let's use a function that checks for the permission. 
):
    # For now, just require a generic authenticated state or role.
    today_start = datetime.combine(date.today(), datetime.min.time())
    
    # Total sales today
    stmt_sales = select(func.sum(Payment.amount)).join(Order).where(Payment.timestamp >= today_start, Order.status == OrderStatus.PAID)
    result_sales = await db.execute(stmt_sales)
    sales_today = result_sales.scalar() or 0.0

    # Orders count
    stmt_orders = select(func.count(Order.id)).where(Order.created_at >= today_start)
    result_orders = await db.execute(stmt_orders)
    orders_count = result_orders.scalar() or 0

    # Cancelled Orders
    stmt_cancelled = select(func.count(Order.id)).where(Order.created_at >= today_start, Order.status == OrderStatus.CANCELLED)
    result_cancelled = await db.execute(stmt_cancelled)
    cancelled_count = result_cancelled.scalar() or 0

    # Sales by payment method
    stmt_methods = select(Payment.method, func.sum(Payment.amount)).where(Payment.timestamp >= today_start).group_by(Payment.method)
    res_methods = await db.execute(stmt_methods)
    payment_methods = [{"method": row[0].value, "total": row[1]} for row in res_methods.all()]

    return {
        "sales_today": sales_today,
        "orders_count": orders_count,
        "cancelled_count": cancelled_count,
        "payments_by_method": payment_methods
    }
