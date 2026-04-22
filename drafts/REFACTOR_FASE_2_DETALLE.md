# Refactorización Profesional - Fase 2: Patrón Repositorio
## Guía de Implementación Exacta

> **Prerequisito:** La Fase 1 debe estar completa y verificada: `pos_core/exceptions.py` existe, `pos_core/sales/schemas.py` está activo y el Router usa `response_model=OrderRead`.

Este documento contiene el código exacto para implementar la **Fase 2 (Aislamiento de Capa de Datos)**. El objetivo es extraer **todas** las sentencias `select()`, `session.exec()` y `session.execute()` de `service.py` hacia un `repository.py` dedicado, siguiendo el principio de Responsabilidad Única.

---

## Por qué esta fase es crítica

Actualmente `service.py` mezcla dos preocupaciones en la misma función:

```python
# ❌ ANTES: La lógica de negocio ("¿está pagada?") convive con SQL puro
async def add_payment(session, order_id, method, amount, vacate_table=True):
    payment = Payment(order_id=order_id, ...)
    session.add(payment)
    order = await session.get(Order, order_id)   # ← SQL crudo en el Servicio
    if order:
        order.is_paid = True
        ...
    await session.commit()
```

Después de la Fase 2:
```python
# ✅ DESPUÉS: service.py habla con el Repository, no con SQLAlchemy
async def add_payment(session, order_id, method, amount, vacate_table=True):
    order = await order_repo.get_with_relations(session, order_id)   # ← Repository
    if not order:
        raise OrderNotFoundError(order_id)
    payment = await order_repo.create_payment(session, order_id, method, amount)
    order.is_paid = True
    order.status = OrderStatus.PAID
    # El Service hace commit() al final, controlando la transacción
    await session.commit()
```

---

## 1. Crear `pos_core/sales/repository.py`

Este archivo es el único lugar donde SQLAlchemy puede hablar con la base de datos para el módulo de ventas.

**Reglas del Repositorio:**
- ✅ Puede usar `select()`, `session.add()`, `session.get()`, `session.delete()`
- ✅ Puede recibir `AsyncSession` como parámetro
- ❌ **NUNCA hace `session.commit()`** — esa responsabilidad es del Servicio
- ❌ **NUNCA contiene reglas de negocio** (no evalúa si algo "puede" hacerse)

```python
# pos_core/sales/repository.py

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from .models import Order, OrderItem, Payment, OrderStatus, PaymentMethod
from pos_core.inventory.models import Modifier, Product, ProductVariant


class OrderRepository:
    """
    Repositorio de Órdenes: única fuente de acceso a datos para el módulo de ventas.
    
    REGLA FUNDAMENTAL: Este repositorio SOLO hace operaciones de lectura/escritura
    en la BD. Nunca ejecuta session.commit(). El control transaccional lo tiene
    exclusivamente el Servicio.
    """

    async def get_by_id(self, session: AsyncSession, order_id: int) -> Optional[Order]:
        """Obtiene una orden por ID, sin relaciones precargadas."""
        return await session.get(Order, order_id)

    async def get_with_relations(self, session: AsyncSession, order_id: int) -> Optional[Order]:
        """
        Obtiene una orden con todas sus relaciones precargadas (eager loading).
        Úsalo cuando necesitas acceder a items, pagos, variantes o modificadores.
        """
        statement = (
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.items).selectinload(OrderItem.modifiers),
                selectinload(Order.items).selectinload(OrderItem.variant).selectinload(ProductVariant.measure),
                selectinload(Order.payments),
            )
        )
        result = await session.execute(statement)
        return result.unique().scalar_one_or_none()

    async def get_all(
        self,
        session: AsyncSession,
        status: Optional[OrderStatus] = None,
    ) -> List[Order]:
        """
        Lista todas las órdenes con relaciones completas.
        Filtra opcionalmente por estado.
        """
        statement = (
            select(Order)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.items).selectinload(OrderItem.modifiers),
                selectinload(Order.items).selectinload(OrderItem.variant).selectinload(ProductVariant.measure),
                selectinload(Order.payments),
            )
        )
        if status is not None:
            statement = statement.where(Order.status == status)

        result = await session.execute(statement)
        return result.unique().scalars().all()

    async def get_active_for_kitchen(self, session: AsyncSession) -> List[Order]:
        """
        Retorna las órdenes PENDING y PREPARING para la pantalla de cocina (KDS).
        Ordenadas por antigüedad (primero la más vieja).
        """
        statement = (
            select(Order)
            .where(Order.status.in_([OrderStatus.PENDING, OrderStatus.PREPARING]))
            .order_by(Order.created_at)
            .options(
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.items).selectinload(OrderItem.modifiers),
                selectinload(Order.items).selectinload(OrderItem.variant).selectinload(ProductVariant.measure),
                selectinload(Order.payments),
            )
        )
        result = await session.execute(statement)
        return result.unique().scalars().all()

    async def save(self, session: AsyncSession, order: Order) -> None:
        """Persiste cambios en un objeto Order en la sesión (sin commit)."""
        session.add(order)

    async def delete(self, session: AsyncSession, order: Order) -> None:
        """Elimina un objeto Order de la sesión (sin commit)."""
        await session.delete(order)

    async def create_payment(
        self,
        session: AsyncSession,
        order_id: int,
        method: PaymentMethod,
        amount: float,
    ) -> Payment:
        """Crea y persiste un objeto Payment en la sesión (sin commit)."""
        payment = Payment(order_id=order_id, method=method, amount=amount)
        session.add(payment)
        return payment


class OrderItemRepository:
    """
    Repositorio de Ítems de Orden.
    """

    async def get_by_id(
        self, session: AsyncSession, order_id: int, item_id: int
    ) -> Optional[OrderItem]:
        """Obtiene un ítem de la orden con sus modificadores precargados."""
        statement = (
            select(OrderItem)
            .where(OrderItem.id == item_id, OrderItem.order_id == order_id)
            .options(selectinload(OrderItem.modifiers))
        )
        result = await session.execute(statement)
        return result.scalar_one_or_none()

    async def get_items_for_order(
        self, session: AsyncSession, order_id: int
    ) -> List[OrderItem]:
        """Obtiene todos los ítems de una orden con modificadores."""
        statement = (
            select(OrderItem)
            .where(OrderItem.order_id == order_id)
            .options(selectinload(OrderItem.modifiers))
        )
        result = await session.execute(statement)
        return result.scalars().all()

    async def save(self, session: AsyncSession, item: OrderItem) -> None:
        """Persiste cambios en un ítem (sin commit)."""
        session.add(item)


# Instancias singleton para importar en el servicio
order_repo = OrderRepository()
item_repo = OrderItemRepository()
```

---

## 2. Refactorizar `service.py` función por función

La estrategia es clara: **una función a la vez**, verificando que la API siga respondiendo después de cada cambio. No refactorizar todo de golpe.

### 2.1 — `get_order_by_id` (La más fácil)

**ANTES:**
```python
async def get_order_by_id(session: AsyncSession, order_id: int) -> Optional[Order]:
    return await session.get(Order, order_id)
```

**DESPUÉS:**
```python
from pos_core.sales.repository import order_repo

async def get_order_by_id(session: AsyncSession, order_id: int) -> Optional[Order]:
    return await order_repo.get_by_id(session, order_id)
```

---

### 2.2 — `get_orders_json` y `get_order_json`

**ANTES:**
```python
async def get_orders_json(session: AsyncSession, status: Optional[OrderStatus] = None) -> List[dict]:
    from sqlalchemy.orm import selectinload
    statement = select(Order).options(
        selectinload(Order.items),
        selectinload(Order.items, OrderItem.product),
        # ... 4 líneas más de selectinload
    )
    if status is not None:
        statement = statement.where(Order.status == status)
    result = await session.execute(statement)
    return result.unique().scalars().all()
```

**DESPUÉS:**
```python
async def get_orders_json(session: AsyncSession, status: Optional[OrderStatus] = None) -> List[Order]:
    return await order_repo.get_all(session, status)

async def get_order_json(session: AsyncSession, order_id: int) -> Optional[Order]:
    return await order_repo.get_with_relations(session, order_id)
```

---

### 2.3 — `get_kitchen_orders`

**ANTES:**
```python
async def get_kitchen_orders(session: AsyncSession) -> list:
    from sqlalchemy.orm import selectinload
    statement = (
        select(Order)
        .where(Order.status.in_([OrderStatus.PENDING, OrderStatus.PREPARING]))
        .order_by(Order.created_at)
        .options(
            selectinload(Order.items),
            selectinload(Order.items, OrderItem.product),
            # ...
        )
    )
    result = await session.execute(statement)
    return result.unique().scalars().all()
```

**DESPUÉS:**
```python
async def get_kitchen_orders(session: AsyncSession) -> List[Order]:
    return await order_repo.get_active_for_kitchen(session)
```

---

### 2.4 — `add_payment` (El más importante — desacoplamiento de mesas)

> [!IMPORTANT]
> Esta es la función de mayor impacto. Aquí aplicamos el desacoplamiento crítico:
> `payment_service` NO llama a `vacate_table_service` directamente. La liberación
> de mesa se convierte en responsabilidad del **Router** que coordina ambas acciones.

**ANTES (en service.py):**
```python
async def add_payment(session, order_id, method, amount, vacate_table=True) -> Payment:
    payment = Payment(order_id=order_id, method=method, amount=amount)
    session.add(payment)
    order = await session.get(Order, order_id)
    if order:
        order.is_paid = True
        order.status = OrderStatus.PAID
        if order.table_id and vacate_table:
            await vacate_table_service(session, order.table_id)  # ← ACOPLAMIENTO
    await session.commit()
    await session.refresh(payment)
    return payment
```

**DESPUÉS (en service.py):**
```python
from pos_core.sales.repository import order_repo
from pos_core.exceptions import OrderNotFoundError, InvalidOrderStateError

async def add_payment(
    session: AsyncSession,
    order_id: int,
    method: PaymentMethod,
    amount: float,
) -> Payment:
    """
    Registra un pago y marca la orden como pagada.
    
    RESPONSABILIDAD ÚNICA: Esta función SOLO gestiona el registro financiero.
    La lógica de liberar la mesa es responsabilidad del Router o del Servicio
    Orquestador que llame a table_service.vacate_table() por separado.
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
    
    # El Service controla el límite transaccional con un único commit
    await session.commit()
    await session.refresh(payment)
    return payment
```

**Actualizar el Router para orquestar (en router.py):**

```python
# router.py — El Router ahora coordina pago + liberación de mesa

from pos_core.tables import service as table_service  # import del módulo de mesas

@router.post("/orders/{order_id}/payments", response_model=Payment)
async def pay_order(
    order_id: int,
    payment_in: PaymentCreate,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_permission("can_charge")),
):
    """Registra un pago. Si vacate_table=True, libera la mesa en una operación separada."""
    order = await service.get_order_by_id(db, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # 1. Registrar el pago (responsabilidad financiera pura)
    payment = await service.add_payment(db, order_id, payment_in.method, payment_in.amount)
    
    # 2. Si el cliente se va, liberar la mesa (responsabilidad del dominio de mesas)
    if order.table_id and payment_in.vacate_table:
        await table_service.vacate_table_service(db, order.table_id)
    
    # 3. Broadcasts y notificaciones
    asyncio.create_task(trigger_broadcast("kitchen_orders"))
    asyncio.create_task(trigger_broadcast("recent_orders"))
    asyncio.create_task(trigger_broadcast("dashboard_stats"))
    asyncio.create_task(trigger_broadcast("tables"))
    
    if order.table_id and payment_in.vacate_table:
        asyncio.create_task(trigger_iot_broadcast(order.table_id, "clear_table", "", data={}))

    return payment
```

---

### 2.5 — `update_order_status` (La más compleja)

Esta función tiene lógica de negocio legítima mezclada con SQL. La refactorización la preserva pero limpia los accesos de datos.

**DESPUÉS:**
```python
async def update_order_status(
    session: AsyncSession,
    order_id: int,
    new_status: OrderStatus,
    cook_uuid: Optional[str] = None,
    cook_name: Optional[str] = None,
    delivered_by_uuid: Optional[str] = None,
    delivered_by_name: Optional[str] = None,
) -> Optional[Order]:
    from datetime import datetime, timezone

    order = await order_repo.get_by_id(session, order_id)
    if not order:
        raise OrderNotFoundError(order_id)

    old_status = order.status
    order.status = new_status
    now = datetime.now(timezone.utc)

    # ── Timestamps de ciclo de vida ────────────────────────────────────────────
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
                data={"order_id": order.id, "status": "LISTO", "progress": 100}
            )

    elif new_status == OrderStatus.DELIVERED and order.delivered_at is None:
        order.delivered_at = now

    await order_repo.save(session, order)

    # ── Cancelación libera la mesa (via tabla de mesas, no acoplado) ──────────
    if new_status == OrderStatus.CANCELLED and order.table_id:
        from pos_core.tables import service as table_service
        await table_service.vacate_table_service(session, order.table_id)

    await session.commit()
    await session.refresh(order)

    # ── Propagar estado a los ítems ───────────────────────────────────────────
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
```

---

### 2.6 — `delete_order`

**DESPUÉS:**
```python
async def delete_order(session: AsyncSession, order_id: int) -> bool:
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

## 3. Imports finales en `service.py`

Al terminar la refactorización, el bloque de imports de `service.py` debe quedar así:

```python
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from .models import Order, OrderItem, Payment, OrderStatus, OrderType, PaymentMethod
from pos_core.inventory.service import process_inventory_depletion
from pos_core.sales.shifts_service import get_active_shift
from pos_core.events.service import trigger_iot_broadcast
from pos_core.exceptions import OrderNotFoundError, InvalidOrderStateError
from pos_core.sales.repository import order_repo, item_repo

# ELIMINADOS:
# - from sqlalchemy.orm import selectinload  (ahora vive en repository.py)
# - from pos_core.inventory.models import ProductVariant (solo el repo lo necesita)
```

---

## 4. Criterios de Finalización de la Fase 2

La fase está **completa** cuando se cumplen todas estas condiciones:

| Criterio | Verificación |
|---|---|
| ✅ `repository.py` existe en `pos_core/sales/` | `ls pos_core/sales/` |
| ✅ Cero `select()` en `service.py` | `grep -n "select(" pos_core/sales/service.py` → sin resultados |
| ✅ Cero `session.execute()` en `service.py` | `grep -n "session.execute" pos_core/sales/service.py` → sin resultados |
| ✅ Cero `selectinload` en `service.py` | `grep -n "selectinload" pos_core/sales/service.py` → sin resultados |
| ✅ `add_payment` NO llama a `vacate_table_service` | Revisión manual del código |
| ✅ El endpoint `GET /orders` sigue respondiendo | `curl http://localhost:8000/orders` |
| ✅ El endpoint `POST /orders/{id}/payments` funciona | Test manual en UI |
| ✅ Los WebSockets del KDS siguen actualizando | Test visual en `/kitchen` |

---

## 5. Orden de ejecución recomendada

Para minimizar el riesgo, implementar en este orden exacto:

```
1. Crear repository.py  (no rompe nada, es nuevo)
2. Refactorizar get_order_by_id  → Verificar GET /orders/{id}
3. Refactorizar get_orders_json / get_order_json → Verificar GET /orders
4. Refactorizar get_kitchen_orders → Verificar pantalla KDS
5. Refactorizar add_payment + actualizar Router → ⚠️ Verificar flujo de pago completo
6. Refactorizar update_order_status → Verificar KDS y cambios de estado
7. Refactorizar delete_order → Verificar borrado de orden vacía
8. Ejecutar grep de validación (tabla de criterios del paso 4)
```

---

> [!NOTE]
> La Fase 3 (desintegración del monolito en `order_service`, `payment_service`, `analytics_service`) puede comenzar **inmediatamente** después de completar esta fase. La Fase 2 hace que la Fase 3 sea segura, porque ya no hay SQL suelto que pueda romperse al mover archivos.

*Ver [PLAN_REFACTOR_PROFESSIONAL.md](file:///home/kaber420/Documentos/proyectos/blackshot/drafts/PLAN_REFACTOR_PROFESSIONAL.md) para el contexto completo del roadmap.*
