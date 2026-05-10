"""
pos_core/sales/order_service.py
================================
Facade for the refactored order services.
"""

from .services.order_lifecycle_service import (
    create_order,
    get_order_by_id,
    get_orders,
    get_order_with_relations,
    update_order_status,
    delete_order,
)
from .services.order_item_service import (
    add_item_to_order,
    update_order_item_status,
)
from .services.order_action_service import (
    cancel_order,
    cancel_order_item,
    transfer_order_table,
)
