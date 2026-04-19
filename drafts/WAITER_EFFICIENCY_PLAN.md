# Plan: Registro de Eficiencia y Estadísticas de Meseros

**Proyecto:** BlackShot POS  
**Estado:** BORRADOR v2 — pendiente de ejecución  
**Fecha:** 2026-04-19  
**Conversación de referencia:** `7fe9c8da-b7a5-44f7-9fc9-ee7b367611e5`

---

## Contexto y Objetivo

Este plan detalla los cambios necesarios para medir la carga de trabajo y la rapidez de los meseros, permitiendo identificar quiénes son los más activos y eficientes.

### Estado Actual del Código

- ✅ `pos_core/roles.py` — ya existe con `Permission` y `ROLE_PRESETS` funcionales.
- ✅ `pos_core/sales/service.py` — `create_order()` ya existe pero **no recibe el usuario creador**.
- ✅ `pos_core/sales/router.py` — `create_new_order()` tiene `user=Depends(require_role("waiter"))` disponible pero **no lo pasa al servicio**.
- ✅ `pos_core/sales/analytics_router.py` — `/dashboard` existe, pero **no hay endpoint de meseros**.
- ✅ `pos_core/sales/models.py` — `Order` y `OrderItem` existen pero **sin campos de mesero ni timestamps de ciclo de vida**.
- ✅ `bs_frontend/src/routes/(app)/admin/analytics/+page.svelte` — existe pero sin sección de desempeño de equipo.

---

## Cambios Propuestos

---

### FASE 1 — Migración de Base de Datos

**Archivo:** `scripts/migrate_waiter_tracking.py` (**NUEVO**)

La tabla `Order` necesita campos para saber quién creó la orden y cuándo ocurrió cada transición. La tabla `OrderItem` necesita saber quién entregó cada platillo.

```python
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'pos_database.db')

MIGRATIONS = [
    # En la tabla Order
    "ALTER TABLE `order` ADD COLUMN waiter_uuid TEXT",
    "ALTER TABLE `order` ADD COLUMN waiter_name TEXT",
    "ALTER TABLE `order` ADD COLUMN preparing_at DATETIME",
    "ALTER TABLE `order` ADD COLUMN ready_at DATETIME",
    "ALTER TABLE `order` ADD COLUMN delivered_at DATETIME",
    # En la tabla OrderItem
    "ALTER TABLE orderitem ADD COLUMN delivered_by_uuid TEXT",
    "ALTER TABLE orderitem ADD COLUMN delivered_by_name TEXT",
    "ALTER TABLE orderitem ADD COLUMN preparing_at DATETIME",
    "ALTER TABLE orderitem ADD COLUMN ready_at DATETIME",
    "ALTER TABLE orderitem ADD COLUMN delivered_at DATETIME",
]

conn = sqlite3.connect(DB_PATH)
for sql in MIGRATIONS:
    try:
        conn.execute(sql)
        conn.commit()
        print(f"✅ {sql[:60]}...")
    except sqlite3.OperationalError as e:
        print(f"ℹ️  Ignorado (ya existe): {e}")
conn.close()
print("🏁 Migración completada.")
```

> **Nota:** SQLite usa `order` como palabra reservada. La tabla generada por SQLModel se llama `order` en minúsculas — usar backticks al ejecutar ALTER TABLE manualmente.

---

### FASE 2 — Modelos SQLModel (`pos_core/sales/models.py`)

**Archivo:** `pos_core/sales/models.py` (**MODIFICAR**)

Agregar campos a `Order` (después de `updated_at`) y a `OrderItem` (después de `status`).

#### `Order` — campos nuevos:

```python
# Rastreo del mesero creador
waiter_uuid: Optional[str] = Field(default=None, description="UUID del mesero que creó la orden")
waiter_name: Optional[str] = Field(default=None, description="Nombre del mesero (snapshot para auditoría rápida)")

# Timestamps de ciclo de vida de la orden
preparing_at: Optional[datetime] = Field(default=None, description="Cuando la cocina empezó a preparar")
ready_at: Optional[datetime] = Field(default=None, description="Cuando la cocina marcó la orden como lista")
delivered_at: Optional[datetime] = Field(default=None, description="Cuando el mesero entregó la orden a la mesa")
```

#### `OrderItem` — campos nuevos:

```python
# Rastreo de entrega por ítem
delivered_by_uuid: Optional[str] = Field(default=None)
delivered_by_name: Optional[str] = Field(default=None)

# Timestamps de ciclo de vida del ítem (para eficiencia por platillo)
preparing_at: Optional[datetime] = Field(default=None)
ready_at: Optional[datetime] = Field(default=None)
delivered_at: Optional[datetime] = Field(default=None)
```

#### Resultado final del modelo `Order` (sección relevante):

```python
class Order(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    type: OrderType
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    is_paid: bool = Field(default=False)
    table_id: Optional[int] = Field(default=None, foreign_key="table.id")
    shift_id: Optional[int] = Field(default=None, foreign_key="shift.id")
    external_reference: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    # --- NUEVO ---
    waiter_uuid: Optional[str] = Field(default=None)
    waiter_name: Optional[str] = Field(default=None)
    preparing_at: Optional[datetime] = Field(default=None)
    ready_at: Optional[datetime] = Field(default=None)
    delivered_at: Optional[datetime] = Field(default=None)
    # --- FIN NUEVO ---
    items: List[OrderItem] = Relationship(back_populates="order")
    payments: List[Payment] = Relationship(back_populates="order")
    shift: Optional[Shift] = Relationship(back_populates="orders")
```

---

### FASE 3 — Lógica de Negocio (`pos_core/sales/service.py`)

**Archivo:** `pos_core/sales/service.py` (**MODIFICAR**)

#### 3.1 — `create_order()`: inyectar el mesero creador

Cambiar la firma para aceptar `waiter_uuid` y `waiter_name`:

```python
async def create_order(
    session: AsyncSession,
    order_type: OrderType,
    table_id: Optional[int] = None,
    external_reference: Optional[str] = None,
    waiter_uuid: Optional[str] = None,   # NUEVO
    waiter_name: Optional[str] = None,   # NUEVO
) -> Order:
    active_shift = await get_active_shift(session)
    shift_id = active_shift.id if active_shift else None

    db_order = Order(
        type=order_type,
        table_id=table_id,
        shift_id=shift_id,
        external_reference=external_reference,
        status=OrderStatus.PENDING,
        waiter_uuid=waiter_uuid,   # NUEVO
        waiter_name=waiter_name,   # NUEVO
    )
    # ... resto igual
```

#### 3.2 — `update_order_status()`: grabar timestamps automáticamente

Dentro del bloque `if order:`, antes del `await session.commit()`:

```python
from datetime import datetime

# Grabar timestamps según la transición
if new_status == OrderStatus.PREPARING and order.preparing_at is None:
    order.preparing_at = datetime.utcnow()

elif new_status == OrderStatus.READY and order.ready_at is None:
    order.ready_at = datetime.utcnow()

elif new_status == OrderStatus.DELIVERED and order.delivered_at is None:
    order.delivered_at = datetime.utcnow()
    # También registrar quién entregó (se pasa como parámetro adicional)
```

> **Nota:** Para registrar quién entregó (`delivered_by`), el endpoint de `PATCH /orders/{id}/status` necesitará opcionalmente recibir el user del token y pasarlo al service si `new_status == DELIVERED`. Ver Fase 4.

#### 3.3 — `update_order_item_status()`: grabar timestamps por ítem

Dentro del bloque `if item:`, después de `item.status = new_status`:

```python
from datetime import datetime

if new_status == OrderStatus.PREPARING and item.preparing_at is None:
    item.preparing_at = datetime.utcnow()
elif new_status == OrderStatus.READY and item.ready_at is None:
    item.ready_at = datetime.utcnow()
elif new_status == OrderStatus.DELIVERED and item.delivered_at is None:
    item.delivered_at = datetime.utcnow()
    # item.delivered_by_uuid = delivered_by_uuid  # pasar desde router
    # item.delivered_by_name = delivered_by_name
```

#### 3.4 — `format_order_json()`: exponer los campos nuevos

En el `return {}` de `format_order_json()`, agregar:

```python
return {
    "id": order.id,
    "type": order.type,
    "status": order.status,
    "is_paid": order.is_paid,
    "table_id": order.table_id,
    "shift_id": order.shift_id,
    "external_reference": order.external_reference,
    "created_at": order.created_at.isoformat(),
    "updated_at": order.updated_at.isoformat(),
    # --- NUEVO ---
    "waiter_uuid": order.waiter_uuid,
    "waiter_name": order.waiter_name,
    "preparing_at": order.preparing_at.isoformat() if order.preparing_at else None,
    "ready_at": order.ready_at.isoformat() if order.ready_at else None,
    "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
    # --- FIN NUEVO ---
    "items": items_data,
}
```

Y en cada ítem dentro de `items_data`:

```python
{
    "id": item.id,
    "product_id": item.product_id,
    "product": {...},
    "variant": {...},
    "quantity": item.quantity,
    "unit_price": item.unit_price,
    "status": item.status,
    "modifiers": [...],
    # --- NUEVO ---
    "delivered_by_uuid": item.delivered_by_uuid,
    "delivered_by_name": item.delivered_by_name,
    "preparing_at": item.preparing_at.isoformat() if item.preparing_at else None,
    "ready_at": item.ready_at.isoformat() if item.ready_at else None,
    "delivered_at": item.delivered_at.isoformat() if item.delivered_at else None,
    # --- FIN NUEVO ---
}
```

---

### FASE 4 — Router de Órdenes (`pos_core/sales/router.py`)

**Archivo:** `pos_core/sales/router.py` (**MODIFICAR**)

#### 4.1 — `create_new_order()`: pasar el usuario al service

El `user` dict ya está disponible como resultado de `Depends(require_role(...))`. Pasarlo al service:

```python
@router.post("/orders", response_model=Order)
async def create_new_order(
    order_in: OrderCreate,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role("waiter")),
):
    """Crea una nueva orden y notifica a la cocina en tiempo real."""
    order = await service.create_order(
        db,
        order_in.type,
        order_in.table_id,
        order_in.external_reference,
        waiter_uuid=user.get("user_uuid"),   # NUEVO
        waiter_name=user.get("username"),     # NUEVO
    )
    asyncio.create_task(broadcast_updates())
    return order
```

> **Importante:** Verificar qué claves devuelve `user` en el dict de `require_role`. Revisar `omni_auth/security.py` para confirmar los nombres exactos (`user_uuid`, `username`).

#### 4.2 — `update_status()`: registrar quién entregó

```python
@router.patch("/orders/{order_id}/status", response_model=Order)
async def update_status(
    order_id: int,
    status: OrderStatus,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role(["kitchen", "waiter", "cashier"])),
):
    order = await service.update_order_status(
        db,
        order_id,
        status,
        delivered_by_uuid=user.get("user_uuid") if status == OrderStatus.DELIVERED else None,
        delivered_by_name=user.get("username") if status == OrderStatus.DELIVERED else None,
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    asyncio.create_task(broadcast_updates())
    return order
```

Y en `service.update_order_status()`, actualizar la firma:

```python
async def update_order_status(
    session: AsyncSession,
    order_id: int,
    new_status: OrderStatus,
    delivered_by_uuid: Optional[str] = None,  # NUEVO
    delivered_by_name: Optional[str] = None,  # NUEVO
) -> Optional[Order]:
```

---

### FASE 5 — Analytics Endpoint (`pos_core/sales/analytics_router.py`)

**Archivo:** `pos_core/sales/analytics_router.py` (**MODIFICAR**)

Agregar el endpoint `/analytics/waiters/performance`:

```python
from sqlmodel import select, func
from .models import Order, OrderItem, OrderStatus

@router.get("/waiters/performance")
async def get_waiter_performance(
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role(["admin", "manager"])),
):
    """
    Retorna estadísticas de desempeño por mesero.
    Incluye: órdenes creadas, ventas totales, tiempo promedio de entrega.
    """
    from datetime import date, datetime
    from sqlalchemy import cast, Date

    today_start = datetime.combine(date.today(), datetime.min.time())

    # 1. Órdenes creadas y ventas totales por mesero (hoy)
    stmt_orders = (
        select(
            Order.waiter_uuid,
            Order.waiter_name,
            func.count(Order.id).label("orders_count"),
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

    waiter_stats = {}
    for row in rows:
        waiter_stats[row.waiter_uuid] = {
            "waiter_uuid": row.waiter_uuid,
            "waiter_name": row.waiter_name or "Desconocido",
            "orders_count": row.orders_count or 0,
            "total_sales": round(row.total_sales or 0.0, 2),
            "avg_delivery_seconds": None,  # se calcula abajo
        }

    # 2. Tiempo promedio de entrega: desde ready_at hasta delivered_at
    #    (qué tan rápido el mesero lleva el plato después de que cocina lo marca listo)
    stmt_times = (
        select(Order.waiter_uuid, Order.ready_at, Order.delivered_at)
        .where(
            Order.created_at >= today_start,
            Order.ready_at.isnot(None),
            Order.delivered_at.isnot(None),
            Order.waiter_uuid.isnot(None),
        )
    )
    result_times = await db.execute(stmt_times)
    time_rows = result_times.all()

    # Agrupar deltas por mesero
    delivery_times: dict[str, list[float]] = {}
    for row in time_rows:
        delta = (row.delivered_at - row.ready_at).total_seconds()
        if delta >= 0:
            delivery_times.setdefault(row.waiter_uuid, []).append(delta)

    for uuid, times in delivery_times.items():
        if uuid in waiter_stats and times:
            waiter_stats[uuid]["avg_delivery_seconds"] = round(sum(times) / len(times), 1)

    # Ordenar por número de órdenes descending
    result = sorted(waiter_stats.values(), key=lambda x: x["orders_count"], reverse=True)
    return result
```

---

### FASE 6 — Frontend: Dashboard (`bs_frontend/src/routes/(app)/admin/analytics/+page.svelte`)

**Archivo:** `bs_frontend/src/routes/(app)/admin/analytics/+page.svelte` (**MODIFICAR**)

#### 6.1 — Fetch de datos

En `onMount` o con `$effect`, agregar la llamada a `/analytics/waiters/performance`:

```typescript
let waiterStats: WaiterStat[] = $state([]);

interface WaiterStat {
    waiter_uuid: string;
    waiter_name: string;
    orders_count: number;
    total_sales: number;
    avg_delivery_seconds: number | null;
}

async function loadWaiterStats() {
    const token = localStorage.getItem('X-Omni-Token');
    const res = await fetch('/api/analytics/waiters/performance', {
        headers: { 'X-Omni-Token': token ?? '' }
    });
    if (res.ok) waiterStats = await res.json();
}

// Función helper para formatear segundos → "1m 23s"
function formatSeconds(secs: number | null): string {
    if (secs === null) return '—';
    const m = Math.floor(secs / 60);
    const s = Math.round(secs % 60);
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
}
```

#### 6.2 — Sección UI: "Desempeño de Equipo"

Agregar debajo de las tarjetas de dashboard existentes:

```svelte
<!-- Sección: Desempeño de Equipo -->
<section class="team-performance">
    <h2>Desempeño del Equipo</h2>
    <p class="subtitle">Basado en órdenes del día de hoy</p>

    {#if waiterStats.length === 0}
        <p class="empty-state">Sin datos de meseros para hoy.</p>
    {:else}
        <div class="waiter-table-wrapper">
            <table class="waiter-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Mesero</th>
                        <th>Órdenes</th>
                        <th>Ventas Hoy</th>
                        <th>Tiempo Prom. Entrega</th>
                        <th>Eficiencia</th>
                    </tr>
                </thead>
                <tbody>
                    {#each waiterStats as stat, i}
                        <tr class:top={i === 0}>
                            <td>{i + 1}</td>
                            <td class="waiter-name">{stat.waiter_name}</td>
                            <td>{stat.orders_count}</td>
                            <td>${stat.total_sales.toFixed(2)}</td>
                            <td>{formatSeconds(stat.avg_delivery_seconds)}</td>
                            <td>
                                <!-- Badge visual de rapidez -->
                                {#if stat.avg_delivery_seconds !== null}
                                    <span class="badge {stat.avg_delivery_seconds < 120 ? 'badge-fast' : stat.avg_delivery_seconds < 300 ? 'badge-ok' : 'badge-slow'}">
                                        {stat.avg_delivery_seconds < 120 ? '🔥 Rápido' : stat.avg_delivery_seconds < 300 ? '✅ Normal' : '🐢 Lento'}
                                    </span>
                                {:else}
                                    <span class="badge badge-neutral">Sin datos</span>
                                {/if}
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    {/if}
</section>
```

---

### FASE 7 — Registrar el router de analytics en el app principal

**Archivo:** `pos_core/__init__.py` o el archivo principal donde se montan los routers (verificar cuál es).

Asegurarse de que `analytics_router` esté montado con el prefijo correcto:

```python
# En el archivo principal de FastAPI (ej. pos_core/cli.py o similar)
from pos_core.sales.analytics_router import router as analytics_router

app.include_router(analytics_router, prefix="/api/analytics", tags=["analytics"])
```

> **Verificar:** Abrir `pos_core/cli.py` o el entry point para confirmar el prefijo actual de `analytics_router` y que el frontend use la URL correcta.

---

## Orden de Ejecución y Checklist

```
FASE 1: Migración SQLite                           ~10 min
FASE 2: Actualizar models.py (Order + OrderItem)   ~15 min
FASE 3: Actualizar service.py                      ~25 min
FASE 4: Actualizar router.py                       ~15 min
FASE 5: Nuevo endpoint analytics                   ~30 min
FASE 6: Frontend dashboard sección meseros         ~45 min
FASE 7: Verificar montaje router analytics         ~5 min
──────────────────────────────────────────────────────────
Total estimado:                                   ~2h 25min
```

### Checklist para el desarrollador

- [ ] **FASE 1** — Ejecutar `python scripts/migrate_waiter_tracking.py`
- [ ] **FASE 2** — Agregar 5 campos a `Order` y 5 campos a `OrderItem` en `models.py`
- [ ] **FASE 3.1** — `create_order()` recibe `waiter_uuid` + `waiter_name`
- [ ] **FASE 3.2** — `update_order_status()` graba `preparing_at`, `ready_at`, `delivered_at`
- [ ] **FASE 3.3** — `update_order_item_status()` graba timestamps por ítem
- [ ] **FASE 3.4** — `format_order_json()` serializa los campos nuevos
- [ ] **FASE 4.1** — `create_new_order()` en router pasa `user` al service
- [ ] **FASE 4.2** — `update_status()` en router pasa `delivered_by` al service
- [ ] **FASE 5** — Agregar endpoint `GET /analytics/waiters/performance`
- [ ] **FASE 6** — Agregar sección "Desempeño de Equipo" en el frontend
- [ ] **FASE 7** — Verificar que `analytics_router` está montado en el app principal
- [ ] **TEST MANUAL** — Flujo completo descrito abajo

---

## Advertencias y Puntos de Atención

> [!WARNING]
> **SQLite y palabra reservada `order`**  
> La tabla se llama `order` (minúsculas, generada por SQLModel). En ALTER TABLE manual usar backticks: `` ALTER TABLE `order` ADD COLUMN ... ``

> [!IMPORTANT]
> **Verificar claves del dict `user`**  
> En `omni_auth/security.py`, el dict que devuelve `require_role` puede usar `user_uuid` o `sub` o `id`. Verificar antes de codificar `user.get("user_uuid")`.

> [!NOTE]
> **Órdenes históricas sin mesero**  
> Las órdenes creadas antes de esta migración tendrán `waiter_uuid = NULL`. El endpoint de analytics filtra con `.where(Order.waiter_uuid.isnot(None))` para excluirlas limpiamente.

> [!TIP]
> **Eficiencia por ítem vs. por orden**  
> Los timestamps en `OrderItem` permiten analíticas futuras más granulares (ej. "¿cuánto tarda la cocina en preparar un cappuccino?"). Para esta primera versión, el endpoint de eficiencia usa solo los timestamps de `Order`; los de `OrderItem` quedan disponibles para el siguiente sprint.

---

## Verificación

### Manual
1. Abrir sesión como "Mesero A" (rol `waiter`).
2. Crear una orden nueva → verificar en BD que `waiter_uuid` y `waiter_name` se guardaron en `Order`.
3. Desde Cocina, marcar la orden como `PREPARING` → verificar que `preparing_at` se grabó.
4. Marcar como `READY` → verificar `ready_at`.
5. "Mesero A" marca como `DELIVERED` → verificar `delivered_at`.
6. Visitar `/admin/analytics` → confirmar que "Mesero A" aparece en la tabla con sus estadísticas.
7. Verificar que el tiempo promedio de entrega calculado es correcto (`delivered_at - ready_at`).

### Automatizada (opcional)
- Prueba unitaria para `create_order()` verificando que los campos `waiter_*` se persisten.
- Prueba unitaria para `update_order_status()` verificando que los timestamps se graban en la transición correcta y **no se sobreescriben** en transiciones posteriores (gracias a la guardia `if order.preparing_at is None`).
