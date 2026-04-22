# Refactorización Profesional - Fase 3: Desintegración del Monolito

Este documento contiene el código exacto para implementar la **Fase 3** de la refactorización.
El objetivo es partir `pos_core/sales/service.py` en módulos con **Responsabilidad Única**,
mover la lógica de mesas a su dominio propio, y desacoplar completamente el pago de la liberación de mesa.

> [!IMPORTANT]
> **Prerequisitos:** Las Fases 1 y 2 deben estar completas y en `main`.
> Verifica que `pos_core/sales/repository.py` y `pos_core/sales/schemas.py` existan antes de continuar.

---

## Visión General: De 1 Archivo a 4 Módulos

```
ANTES                                DESPUÉS
──────────────────────               ──────────────────────────────────────────
pos_core/sales/
  service.py  (496 líneas)    →      order_service.py    (ciclo de vida órdenes)
                                     payment_service.py  (lógica financiera pura)
                                     analytics_service.py (estadísticas dashboard)
pos_core/tables/
  service.py  (59 líneas)     →      service.py          (+ vacate_table migrado aquí)
```

---

## Paso 1: Crear `pos_core/sales/order_service.py`

Este archivo contiene todo lo relacionado con el **ciclo de vida de una orden**: crear, leer,
actualizar estado, manejar ítems y eliminar. No sabe nada de pagos ni de analíticas.

```python
"""
pos_core/sales/order_service.py
================================
Servicio de Órdenes: gestiona el ciclo de vida completo de una orden.

RESPONSABILIDADES:
  - Crear, leer, actualizar y eliminar órdenes.
  - Gestionar ítems de orden (agregar, actualizar estado).
  - Coordinar con inventory_service para el descuento de stock.
  - Coordinar con table_service al cancelar (vía import local para evitar circulares).
  - Controlar límites transaccionales (session.commit).
  - NO contiene lógica financiera (eso es payment_service).
  - NO contiene cálculos de analíticas (eso es analytics_service).
"""
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .models import Order, OrderItem, OrderStatus, OrderType
from .repository import order_repo, item_repo
from pos_core.inventory.service import process_inventory_depletion
from pos_core.sales.shifts_service import get_active_shift
from pos_core.events.service import trigger_iot_broadcast
from pos_core.exceptions import OrderNotFoundError, InvalidOrderStateError


# ── Creación ───────────────────────────────────────────────────────────────────

async def create_order(
    session: AsyncSession,
    order_type: OrderType,
    table_id: Optional[int] = None,
    external_reference: Optional[str] = None,
    waiter_uuid: Optional[str] = None,
    waiter_name: Optional[str] = None,
) -> Order:
    active_shift = await get_active_shift(session)
    shift_id = active_shift.id if active_shift else None

    db_order = Order(
        type=order_type,
        table_id=table_id,
        shift_id=shift_id,
        external_reference=external_reference,
        status=OrderStatus.PENDING,
        waiter_uuid=waiter_uuid,
        waiter_name=waiter_name,
    )
    session.add(db_order)

    # Marcar mesa como ocupada si se asigna una
    if table_id:
        from pos_core.tables.models import Table
        db_table = await session.get(Table, table_id)
        if db_table and db_table.status != "Occupied":
            db_table.status = "Occupied"
            db_table.occupied_at = datetime.now(timezone.utc)
            session.add(db_table)

    await session.commit()
    await session.refresh(db_order)
    return db_order


# ── Lectura ────────────────────────────────────────────────────────────────────

async def get_order_by_id(session: AsyncSession, order_id: int) -> Optional[Order]:
    return await order_repo.get_by_id(session, order_id)


async def get_orders(
    session: AsyncSession, status: Optional[OrderStatus] = None
) -> List[Order]:
    return await order_repo.get_all(session, status)


async def get_kitchen_orders(session: AsyncSession) -> List[Order]:
    """Retorna las órdenes PENDING y PREPARING para la pantalla KDS."""
    return await order_repo.get_active_for_kitchen(session)


async def get_order_with_relations(
    session: AsyncSession, order_id: int
) -> Optional[Order]:
    """Obtiene una orden con todas sus relaciones cargadas (para serialización Pydantic)."""
    return await order_repo.get_with_relations(session, order_id)


# ── Ítems de Orden ─────────────────────────────────────────────────────────────

async def add_item_to_order(
    session: AsyncSession,
    order_id: int,
    product_id: int,
    quantity: int,
    product_variant_id: Optional[int] = None,
    modifier_ids: Optional[List[int]] = None,
) -> OrderItem:
    from pos_core.inventory.models import Product, ProductVariant, Modifier

    product = await session.get(Product, product_id)
    if not product:
        raise ValueError(f"Product with id {product_id} not found")

    base_price = product.price
    if product_variant_id:
        variant = await session.get(ProductVariant, product_variant_id)
        if variant:
            base_price = variant.price
        else:
            raise ValueError(f"Variant with id {product_variant_id} not found")

    extra_price = 0.0
    modifiers = []
    if modifier_ids:
        for m_id in modifier_ids:
            mod = await session.get(Modifier, m_id)
            if mod:
                extra_price += mod.extra_price
                modifiers.append(mod)

    order_item = OrderItem(
        order_id=order_id,
        product_id=product_id,
        product_variant_id=product_variant_id,
        quantity=quantity,
        unit_price=base_price + extra_price,
        modifiers=modifiers,
    )
    session.add(order_item)
    await session.commit()
    await session.refresh(order_item)
    return order_item


# ── Actualización de Estado de Orden ──────────────────────────────────────────

async def update_order_status(
    session: AsyncSession,
    order_id: int,
    new_status: OrderStatus,
    cook_uuid: Optional[str] = None,
    cook_name: Optional[str] = None,
    delivered_by_uuid: Optional[str] = None,
    delivered_by_name: Optional[str] = None,
) -> Optional[Order]:
    order = await order_repo.get_by_id(session, order_id)
    if not order:
        raise OrderNotFoundError(order_id)

    old_status = order.status
    order.status = new_status
    now = datetime.now(timezone.utc)

    if new_status == OrderStatus.PREPARING and order.preparing_at is None:
        order.preparing_at = now
        if cook_uuid and order.cook_uuid is None:
            order.cook_uuid = cook_uuid
            order.cook_name = cook_name

    elif new_status == OrderStatus.READY and order.ready_at is None:
        order.ready_at = now
        if cook_uuid and order.cook_uuid is None:
            order.cook_uuid = cook_uuid
            order.cook_name = cook_name
        if order.table_id:
            await trigger_iot_broadcast(
                order.table_id, "order_update", "",
                data={"order_id": order.id, "status": "LISTO", "progress": 100},
            )

    elif new_status == OrderStatus.DELIVERED and order.delivered_at is None:
        order.delivered_at = now

    await order_repo.save(session, order)

    # Cancelación: delegar liberación de mesa al table_service (sin acoplamiento directo)
    if new_status == OrderStatus.CANCELLED and order.table_id:
        from pos_core.tables import service as table_service
        await table_service.vacate_table_service(session, order.table_id)

    await session.commit()
    await session.refresh(order)

    # Propagar estado a los ítems
    order_items = await item_repo.get_items_for_order(session, order_id)

    if new_status in (OrderStatus.READY, OrderStatus.DELIVERED):
        items_to_advance = [
            i for i in order_items
            if i.status in (OrderStatus.PENDING, OrderStatus.PREPARING, OrderStatus.READY)
        ]
        items_to_deplete = [i for i in order_items if i.status == OrderStatus.PENDING]
        for i in items_to_advance:
            i.status = new_status
            if new_status == OrderStatus.READY and i.ready_at is None:
                i.ready_at = now
                if cook_uuid and i.cook_uuid is None:
                    i.cook_uuid = cook_uuid
                    i.cook_name = cook_name
            elif new_status == OrderStatus.DELIVERED and i.delivered_at is None:
                i.delivered_at = now
                if delivered_by_uuid and i.delivered_by_uuid is None:
                    i.delivered_by_uuid = delivered_by_uuid
                    i.delivered_by_name = delivered_by_name
            await item_repo.save(session, i)
        if items_to_deplete:
            await process_inventory_depletion(session, items_to_deplete)
        if items_to_advance:
            await session.commit()

    elif old_status == OrderStatus.PENDING and new_status == OrderStatus.PREPARING:
        items_to_deplete = [i for i in order_items if i.status == OrderStatus.PENDING]
        for i in items_to_deplete:
            i.status = OrderStatus.PREPARING
            if i.preparing_at is None:
                i.preparing_at = now
            if cook_uuid and i.cook_uuid is None:
                i.cook_uuid = cook_uuid
                i.cook_name = cook_name
            await item_repo.save(session, i)
        if items_to_deplete:
            await process_inventory_depletion(session, items_to_deplete)
            await session.commit()

    return order


# ── Actualización de Estado de Ítem Individual ────────────────────────────────

async def update_order_item_status(
    session: AsyncSession,
    order_id: int,
    item_id: int,
    new_status: OrderStatus,
    cook_uuid: Optional[str] = None,
    cook_name: Optional[str] = None,
    delivered_by_uuid: Optional[str] = None,
    delivered_by_name: Optional[str] = None,
) -> Optional[OrderItem]:
    item = await item_repo.get_by_id(session, order_id, item_id)
    if not item:
        return None

    old_status = item.status
    if old_status == new_status:
        return item

    item.status = new_status
    now = datetime.now(timezone.utc)

    if new_status == OrderStatus.PREPARING and item.preparing_at is None:
        item.preparing_at = now
        if cook_uuid and item.cook_uuid is None:
            item.cook_uuid = cook_uuid
            item.cook_name = cook_name
    elif new_status == OrderStatus.READY and item.ready_at is None:
        item.ready_at = now
        if cook_uuid and item.cook_uuid is None:
            item.cook_uuid = cook_uuid
            item.cook_name = cook_name
    elif new_status == OrderStatus.DELIVERED and item.delivered_at is None:
        item.delivered_at = now
        if delivered_by_uuid and item.delivered_by_uuid is None:
            item.delivered_by_uuid = delivered_by_uuid
            item.delivered_by_name = delivered_by_name

    await item_repo.save(session, item)

    if old_status == OrderStatus.PENDING and new_status in (
        OrderStatus.PREPARING, OrderStatus.READY, OrderStatus.DELIVERED
    ):
        await process_inventory_depletion(session, [item])

    # Recalcular estado de la orden padre
    order_items = await item_repo.get_items_for_order(session, order_id)
    order = await order_repo.get_by_id(session, order_id)

    if order:
        all_completed = True
        all_delivered = True
        all_cancelled = True
        any_preparing = False
        any_pending = False

        for i in order_items:
            status = new_status if i.id == item_id else i.status
            if status == OrderStatus.PREPARING:
                any_preparing = True
            if status == OrderStatus.PENDING:
                any_pending = True
            if status not in (OrderStatus.READY, OrderStatus.DELIVERED, OrderStatus.CANCELLED):
                all_completed = False
            if status not in (OrderStatus.DELIVERED, OrderStatus.CANCELLED):
                all_delivered = False
            if status != OrderStatus.CANCELLED:
                all_cancelled = False

        new_order_status = None
        if all_cancelled and len(order_items) > 0:
            new_order_status = OrderStatus.CANCELLED
            if order.table_id:
                from pos_core.tables import service as table_service
                await table_service.vacate_table_service(session, order.table_id)
        elif all_delivered and len(order_items) > 0:
            new_order_status = OrderStatus.DELIVERED
        elif all_completed and len(order_items) > 0:
            new_order_status = OrderStatus.READY
        elif any_preparing:
            new_order_status = OrderStatus.PREPARING
        elif any_pending:
            new_order_status = OrderStatus.PENDING

        if new_order_status and new_order_status != order.status:
            if cook_uuid and order.cook_uuid is None:
                order.cook_uuid = cook_uuid
                order.cook_name = cook_name

            if order.status != OrderStatus.PAID:
                is_becoming_ready = (
                    new_order_status == OrderStatus.READY
                    and order.status != OrderStatus.READY
                )
                order.status = new_order_status
                await order_repo.save(session, order)

                if is_becoming_ready and order.table_id:
                    await trigger_iot_broadcast(
                        order.table_id, "order_update", "",
                        data={"order_id": order.id, "status": "LISTO", "progress": 100},
                    )

    await session.commit()
    await session.refresh(item)
    return item


# ── Eliminación ────────────────────────────────────────────────────────────────

async def delete_order(session: AsyncSession, order_id: int) -> bool:
    """
    Elimina físicamente una orden VACÍA.
    Si tiene artículos, lanza error para proteger la auditoría.
    """
    order = await order_repo.get_with_relations(session, order_id)
    if not order:
        return False

    if len(order.items) > 0:
        raise InvalidOrderStateError(
            "No se puede eliminar una orden que ya contiene artículos. "
            "Use Cancelar para mantener auditoría."
        )

    if order.table_id:
        from pos_core.tables import service as table_service
        await table_service.vacate_table_service(session, order.table_id)

    await order_repo.delete(session, order)
    await session.commit()
    return True
```

---

## Paso 2: Crear `pos_core/sales/payment_service.py`

Lógica financiera pura. **No importa `table_service` ni sabe que existen las mesas.**

```python
"""
pos_core/sales/payment_service.py
==================================
Servicio de Pagos: responsabilidad única de registrar transacciones financieras.

REGLA DE ORO:
  Este módulo NO debe importar ni conocer pos_core.tables.
  La coordinación "pagar + liberar mesa" es responsabilidad del Router (orquestador).
"""
from sqlalchemy.ext.asyncio import AsyncSession

from .models import Payment, PaymentMethod
from .repository import order_repo
from pos_core.exceptions import OrderNotFoundError, InvalidOrderStateError
from .models import OrderStatus


async def add_payment(
    session: AsyncSession,
    order_id: int,
    method: PaymentMethod,
    amount: float,
) -> Payment:
    """
    Registra un pago y marca la orden como PAID.

    RESPONSABILIDAD ÚNICA: Solo gestiona la transacción financiera.
    La liberación de mesa es responsabilidad del Router, que llama a
    table_service.vacate_table_service() por separado si es necesario.
    """
    order = await order_repo.get_by_id(session, order_id)
    if not order:
        raise OrderNotFoundError(order_id)
    if order.is_paid:
        raise InvalidOrderStateError("Esta orden ya fue pagada.")

    payment = await order_repo.create_payment(session, order_id, method, amount)
    order.is_paid = True
    order.status = OrderStatus.PAID
    await order_repo.save(session, order)

    await session.commit()
    await session.refresh(payment)
    return payment
```

---

## Paso 3: Crear `pos_core/sales/analytics_service.py`

Extrae `get_dashboard_stats` de `service.py`. Las queries SQL complejas de `analytics_router.py`
**ya están bien ubicadas** en el router (son solo lecturas, sin lógica de negocio), no necesitan moverse.

```python
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
```

---

## Paso 4: Migrar `vacate_table_service` a `pos_core/tables/service.py`

Agregar la función al final del archivo existente. La función ya existía en `sales/service.py`;
ahora vive permanentemente en su dominio correcto.

```python
# AGREGAR al final de pos_core/tables/service.py

async def vacate_table_service(
    session: AsyncSession, table_id: int
) -> Optional[dict]:
    """
    Libera una mesa, calcula el tiempo de ocupación y retorna estadísticas.
    Puede ser llamada por el Router al pagar, o por order_service al cancelar.
    """
    from datetime import datetime, timezone

    db_table = await session.get(Table, table_id)
    if not db_table:
        return None

    occupied_at = db_table.occupied_at
    if occupied_at and occupied_at.tzinfo is None:
        occupied_at = occupied_at.replace(tzinfo=timezone.utc)

    res = {
        "table_id":        table_id,
        "number":          db_table.number,
        "occupied_at":     occupied_at.isoformat() if occupied_at else None,
        "vacated_at":      datetime.now(timezone.utc).isoformat(),
        "duration_minutes": 0,
    }

    if occupied_at:
        delta = datetime.now(timezone.utc) - occupied_at
        res["duration_minutes"] = round(delta.total_seconds() / 60, 2)

    db_table.status = "Free"
    db_table.occupied_at = None
    session.add(db_table)
    await session.commit()

    return res
```

---

## Paso 5: Actualizar `pos_core/sales/service.py` (Facade de Compatibilidad)

> [!IMPORTANT]
> **No borres `service.py` todavía.** El Router lo importa como `from . import service`.
> Convertirlo en un **facade** te permite migrar sin tocar el Router en esta fase.

Reemplaza el contenido completo de `service.py` por este facade:

```python
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
```

---

## Paso 6: Actualizar las Importaciones del Router

El `router.py` actualmente importa `from . import service`. Con el facade del Paso 5,
**no necesitas tocar `router.py` en esta fase**. El router sigue funcionando igual.

Sin embargo, hay **una línea en `router.py` que sí debes verificar** para asegurar el desacoplamiento
de pagos y mesas (ya estaba bien implementado, solo confirma que sigue así):

```python
# router.py — Endpoint POST /orders/{order_id}/payments  (ya correcto desde Fase 2)
# ✅ El router orquesta ambos dominios sin acoplarlos:

@router.post("/orders/{order_id}/payments", response_model=Payment)
async def pay_order(order_id, payment_in, db, user):
    order = await service.get_order_by_id(db, order_id)  # 1. Verificar orden

    payment = await service.add_payment(db, order_id, payment_in.method, payment_in.amount)  # 2. Pago

    if order.table_id and payment_in.vacate_table:
        await table_service.vacate_table_service(db, order.table_id)  # 3. Mesa (independiente)

    # 4. Broadcasts...
    return payment
```

---

## Criterios de Verificación (Definition of Done Fase 3)

Ejecuta estos pasos después de implementar:

### 1. Verificar que los módulos importan sin errores
```bash
cd /home/kaber420/Documentos/proyectos/blackshot
source .venv/bin/activate
python -c "from pos_core.sales.order_service import create_order; print('✅ order_service OK')"
python -c "from pos_core.sales.payment_service import add_payment; print('✅ payment_service OK')"
python -c "from pos_core.sales.analytics_service import get_dashboard_stats; print('✅ analytics_service OK')"
python -c "from pos_core.tables.service import vacate_table_service; print('✅ table vacate OK')"
python -c "from pos_core.sales import service; print('✅ facade OK')"
```

### 2. Iniciar el servidor y hacer smoke test
```bash
blackshot  # Iniciar servidor

# En otra terminal:
curl http://localhost:8000/api/orders        # Debe retornar lista de órdenes
curl http://localhost:8000/api/analytics/dashboard  # Debe retornar stats
```

### 3. Checklist de desacoplamiento
- [ ] `payment_service.py` NO contiene ningún `import` de `pos_core.tables`
- [ ] `order_service.py` solo importa `table_service` con `import local` dentro de funciones (evita circulares)
- [ ] `analytics_service.py` NO contiene `session.exec()` ni `select()` directos
- [ ] `pos_core/tables/service.py` contiene `vacate_table_service`
- [ ] `pos_core/sales/service.py` solo tiene re-exportaciones (es un facade puro)

---

## Estrategia de Rollback

Si algo falla después de aplicar el facade:

1. Restaurar el `service.py` original desde git: `git checkout HEAD -- pos_core/sales/service.py`
2. Los nuevos archivos (`order_service.py`, `payment_service.py`, `analytics_service.py`) no afectan nada hasta que sean importados.
3. El facade es la única pieza de riesgo: si hay un error de importación circular, git revert del facade y el sistema vuelve al estado anterior en segundos.

---

*Al completar esta fase, el `service.py` original habrá sido reemplazado funcionalmente.*
*La Fase 4 (WebSockets + TypeScript) puede comenzar en paralelo con el frontend.*
