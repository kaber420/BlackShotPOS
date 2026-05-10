"""
pos_core/analytics/service.py
=====================================
Servicio de Analíticas: cálculos de estadísticas para dashboards en tiempo real.

RESPONSABILIDADES:
  - Calcular métricas a partir de las órdenes activas en memoria.
  - Actuar como capa intermedia entre el Router y los datos en caliente.
  - Para reportes históricos con SQL agregado, ver router.py directamente.
"""
from datetime import datetime, timezone, timedelta
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from pos_core.sales.models import OrderStatus
from pos_core.sales.repository import order_repo
from pos_core.sales.schemas import OrderRead
from pos_core.kitchen.repository import kitchen_repo
from pos_core.kitchen.models import KitchenStatus


async def get_dashboard_stats(session: AsyncSession) -> dict:
    """
    Calcula las estadísticas en tiempo real para el widget del Dashboard POS.
    Utiliza agregación SQL para máxima eficiencia y estabilidad.
    """
    now = datetime.now()
    start_of_today = datetime(now.year, now.month, now.day)
    start_of_week = start_of_today - timedelta(days=now.weekday())
    start_of_month = datetime(now.year, now.month, 1)

    # Obtenemos los productos estrella directamente desde SQL
    star_today = await order_repo.get_star_product_name(session, start_of_today)
    star_week  = await order_repo.get_star_product_name(session, start_of_week)
    star_month = await order_repo.get_star_product_name(session, start_of_month)

    # Métricas operativas desde Cocina
    kitchen_stats = await kitchen_repo.count_tickets_by_status(session)
    preparing_count = kitchen_stats.get(KitchenStatus.PREPARING, 0) + kitchen_stats.get(KitchenStatus.PENDING, 0)
    ready_count = kitchen_stats.get(KitchenStatus.READY, 0)

    return {
        "preparingCount":   preparing_count,
        "readyCount":       ready_count,
        "starProductToday": star_today,
        "starProductWeek":  star_week,
        "starProductMonth": star_month,
    }
