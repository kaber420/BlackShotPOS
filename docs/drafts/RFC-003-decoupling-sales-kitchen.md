# Decoupling Sales from Kitchen Operational Logic

The goal is to purify the Sales domain, removing logic and states that are strictly operational (kitchen/preparation) and don't belong in the commercial lifecycle.

## Context
Currently, the Sales module (specifically `order_lifecycle_service.py`) handles kitchen-related states like `PREPARING` and `READY`. This creates tight coupling and confuses the commercial domain with operational details.

## Phases of Refactoring

### Phase 1: Sales Domain Purification
Clean up the models, repositories, and services in `pos_core/sales` to remove any "kitchen awareness".

- **Models**: Remove `PREPARING` and `READY` from `OrderStatus`.
- **Repository**: Remove `get_active_for_kitchen`.
- **Services**: 
    - Remove `get_kitchen_orders` from `order_lifecycle_service.py`.
    - **payment_service.py**: Restringir su alcance. Un pago (total o parcial) **nunca** debe cambiar el estado operativo/cocina. Su única función es registrar el abono y marcar la orden como `PAID` solo si el saldo llega a cero.
- **Exports**: Clean up `order_service.py` facade.

### Phase 2: Inventory Listener Alignment
Update `pos_core/inventory/listeners.py` to stop relying on `OrderStatus.PREPARING`. 

- The inventory listener for `sales.payment_received` will now only discount items that **don't** go to kitchen (retail products).
- The listener for `kitchen.item_preparing` will continue to handle production items, but it won't attempt to update `OrderItem.status` to `PREPARING`.

### Phase 3: Analytics & Dashboard Redirection
Update the Dashboard to pull operational metrics from the source of truth (Kitchen module).

- **Kitchen Repository**: Add `count_tickets_by_status` helper.
- **Analytics Service**: Refactor `get_dashboard_stats` to call the new kitchen helper instead of filtering orders by status.

### Phase 4: Validation & Cleanup
- Verify API contracts.
- Ensure the frontend doesn't break (it might need small adjustments if it was hardcoded to look for `PREPARING` in the order list).
- Run full test suite.

## Proposed Changes Summary

### [Phase 1: Sales Domain]
- **models.py**: Remove operational statuses.
- **repository.py**: Remove kitchen-specific queries.
- **order_lifecycle_service.py**: Remove `get_kitchen_orders`.
- **payment_service.py**: Los pagos solo afectan el balance financiero, no el estado operativo de los items.

### [Phase 2: Inventory]
- **listeners.py**: Decouple stock depletion from sales status.

### [Phase 3: Analytics & Kitchen]
- **service.py (Analytics)**: Pull from Kitchen Tickets.
- **repository.py (Kitchen)**: Add status counters.

## Verification Plan
- `pytest tests/pos_core/sales/`
- `pytest tests/pos_core/kitchen/`
- Manual check of Dashboard and KDS interaction.
