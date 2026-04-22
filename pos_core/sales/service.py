"""
pos_core/sales/service.py
=========================
FACADE DE COMPATIBILIDAD — Fase 3 de Refactorización.

Este archivo re-exporta las funciones de los servicios especializados
para mantener compatibilidad con router.py durante la transición.

TODO (Fase 3 final): Actualizar router.py para importar directamente de
      order_service, payment_service, y analytics_service. Luego eliminar este archivo.
"""

# ── Ciclo de vida de órdenes ──────────────────────────────────────────────────
from pos_core.sales.order_service import (
    create_order,
    get_order_by_id,
    get_orders,
    get_kitchen_orders,
    get_order_with_relations as get_order_json,
    get_orders as get_orders_json,
    add_item_to_order,
    update_order_status,
    update_order_item_status,
    delete_order,
)

# ── Pagos ──────────────────────────────────────────────────────────────────────
from pos_core.sales.payment_service import add_payment

# ── Analíticas ─────────────────────────────────────────────────────────────────
from pos_core.sales.analytics_service import get_dashboard_stats

# ── Mesas (re-exportado desde su dominio, para compatibilidad) ─────────────────
from pos_core.tables.service import vacate_table_service

__all__ = [
    "create_order", "get_order_by_id", "get_orders", "get_kitchen_orders",
    "get_order_json", "get_orders_json", "add_item_to_order",
    "update_order_status", "update_order_item_status", "delete_order",
    "add_payment",
    "get_dashboard_stats",
    "vacate_table_service",
]
