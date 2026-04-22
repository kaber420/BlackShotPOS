"""
pos_core/sales/analytics_service.py
=====================================
Servicio de Analíticas: cálculos de estadísticas para dashboards en tiempo real.

RESPONSABILIDADES:
  - Calcular métricas a partir de las órdenes activas en memoria.
  - Actuar como capa intermedia entre el Router y los datos en caliente.
  - Para reportes históricos con SQL agregado, ver analytics_router.py directamente.
"""
from datetime import datetime, timezone, timedelta
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from .models import OrderStatus
from .repository import order_repo
from pos_core.sales.schemas import OrderRead


async def get_dashboard_stats(session: AsyncSession) -> dict:
    """
    Calcula las estadísticas en tiempo real para el widget del Dashboard POS.
    Opera sobre todas las órdenes actuales en memoria usando los DTOs de Pydantic.
    """
    orders_db = await order_repo.get_all(session)
    orders = [OrderRead.model_validate(o).model_dump(mode="json") for o in orders_db]

    preparing_count = len([
        o for o in orders
        if o["status"] in (OrderStatus.PREPARING.value, OrderStatus.PENDING.value)
    ])
    ready_count = len([o for o in orders if o["status"] == OrderStatus.READY.value])

    now = datetime.now(timezone.utc)
    start_of_today = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    start_of_week = start_of_today - timedelta(days=now.weekday())

    def find_best_product(filtered_orders: List[dict]) -> str:
        product_counts: dict = {}
        for o in filtered_orders:
            for item in o.get("items", []):
                name = (
                    item.get("product", {}).get("name", "Producto")
                    if item.get("product")
                    else "Producto"
                )
                product_counts[name] = product_counts.get(name, 0) + item.get("quantity", 0)
        if not product_counts:
            return "Ninguno aún"
        return sorted(product_counts.items(), key=lambda x: x[1], reverse=True)[0][0]

    def ensure_utc(dt_str: str) -> datetime:
        dt = datetime.fromisoformat(dt_str)
        return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt

    today_orders = [o for o in orders if ensure_utc(o["created_at"]) >= start_of_today]
    week_orders  = [o for o in orders if ensure_utc(o["created_at"]) >= start_of_week]

    return {
        "preparingCount":   preparing_count,
        "readyCount":       ready_count,
        "starProductToday": find_best_product(today_orders),
        "starProductWeek":  find_best_product(week_orders),
    }
