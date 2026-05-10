# Plan: Registro de Eficiencia y Estadísticas de Cocineros (KDS)

**Proyecto:** BlackShot POS  
**Estado:** BORRADOR v1 — pendiente de ejecución  
**Fecha:** 2026-04-19  
**Planes relacionados:** `WAITER_EFFICIENCY_PLAN.md`, `ADMIN_PANEL_PLAN.md`

---

## Contexto y Objetivo

Este plan detalla los cambios necesarios para medir la carga de trabajo y velocidad de los **cocineros**, permitiendo al gerente identificar cuellos de botella, platillos lentos y turnos críticos de producción.

La base de datos (timestamps en `Order` y `OrderItem`) ya está siendo preparada por el `WAITER_EFFICIENCY_PLAN.md`. Este plan **reutiliza esa infraestructura** y agrega:

- Registro del **cocinero** que marca cada orden/ítem como `PREPARING` o `READY`
- Analytics de velocidad de preparación por cocinero
- Analytics de velocidad por platillo (¿cuál tarda más?)
- Sección "Desempeño de Cocina" en el panel admin

### Estado Actual del Código

- ✅ `pos_core/sales/models.py` — `Order` y `OrderItem` tendrán `preparing_at`, `ready_at` (via WAITER plan)
- ✅ `pos_core/sales/service.py` — `update_order_status()` / `update_order_item_status()` existen
- ✅ `pos_core/sales/router.py` — `update_status()` tiene `user=Depends(require_role(...))` disponible
- ✅ `pos_core/sales/analytics_router.py` — existe con endpoint `/dashboard`
- ❌ **Nadie graba quién marcó la orden como `PREPARING` o `READY`** — ese dato se pierde hoy
- ❌ No hay endpoint de analíticas de cocina
- ❌ No hay sección de desempeño de cocina en el frontend admin

---

## Cambios Propuestos

---

### FASE 1 — Migración de Base de Datos

**Archivo:** `scripts/migrate_kitchen_tracking.py` (**NUEVO**)

Agregar campos de rastreo del cocinero en `Order` y `OrderItem`. Estos **complementan** los campos de `WAITER_EFFICIENCY_PLAN.md` — ejecutar ambas migraciones.

> **⚠️ Coordinación con WAITER_EFFICIENCY_PLAN.md**  
> Si ya ejecutaste `migrate_waiter_tracking.py`, los campos `preparing_at` y `ready_at` ya existen. Solo añadir los de cocinero a continuación.

```python
import sqlite3, os

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'pos_database.db')

MIGRATIONS = [
    # En la tabla Order — ¿quién marcó la orden como PREPARING/READY?
    "ALTER TABLE `order` ADD COLUMN cook_uuid TEXT",
    "ALTER TABLE `order` ADD COLUMN cook_name TEXT",
    # En la tabla OrderItem — ¿quién preparó cada platillo?
    "ALTER TABLE orderitem ADD COLUMN cook_uuid TEXT",
    "ALTER TABLE orderitem ADD COLUMN cook_name TEXT",
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
print("🏁 Migración de cocina completada.")
```

---

### FASE 2 — Modelos SQLModel (`pos_core/sales/models.py`)

**Archivo:** `pos_core/sales/models.py` (**MODIFICAR**)

Agregar campos de cocinero a `Order` y `OrderItem`, junto a los existentes de mesero (del plan de meseros).

#### `Order` — campos nuevos:

```python
# Rastreo del cocinero responsable (quien marcó PREPARING o READY)
cook_uuid: Optional[str] = Field(default=None, description="UUID del cocinero que tomó la orden")
cook_name: Optional[str] = Field(default=None, description="Nombre del cocinero (snapshot de auditoría)")
```

#### `OrderItem` — campos nuevos:

```python
# Rastreo del cocinero que preparó cada ítem individualmente
cook_uuid: Optional[str] = Field(default=None, description="UUID del cocinero que preparó este ítem")
cook_name: Optional[str] = Field(default=None, description="Nombre del cocinero (snapshot de auditoría)")
```

#### Resultado final del modelo `Order` (zona relevante, con ambos planes):

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
    # --- MESERO (WAITER_EFFICIENCY_PLAN) ---
    waiter_uuid: Optional[str] = Field(default=None)
    waiter_name: Optional[str] = Field(default=None)
    # --- COCINERO (KITCHEN_EFFICIENCY_PLAN) ---
    cook_uuid: Optional[str] = Field(default=None)
    cook_name: Optional[str] = Field(default=None)
    # --- TIMESTAMPS DE CICLO DE VIDA ---
    preparing_at: Optional[datetime] = Field(default=None)
    ready_at: Optional[datetime] = Field(default=None)
    delivered_at: Optional[datetime] = Field(default=None)
    # --- RELACIONES ---
    items: List[OrderItem] = Relationship(back_populates="order")
    payments: List[Payment] = Relationship(back_populates="order")
    shift: Optional[Shift] = Relationship(back_populates="orders")
```

---

### FASE 3 — Lógica de Negocio (`pos_core/sales/service.py`)

**Archivo:** `pos_core/sales/service.py` (**MODIFICAR**)

#### 3.1 — `update_order_status()`: registrar quién marcó PREPARING / READY

Extender la firma para aceptar `cook_uuid` y `cook_name`:

```python
async def update_order_status(
    session: AsyncSession,
    order_id: int,
    new_status: OrderStatus,
    delivered_by_uuid: Optional[str] = None,  # del plan de meseros
    delivered_by_name: Optional[str] = None,  # del plan de meseros
    cook_uuid: Optional[str] = None,           # NUEVO
    cook_name: Optional[str] = None,           # NUEVO
) -> Optional[Order]:
```

Dentro del bloque de transición de estados (junto a los timestamps existentes):

```python
from datetime import datetime

if new_status == OrderStatus.PREPARING and order.preparing_at is None:
    order.preparing_at = datetime.utcnow()
    # Grabar quién inició la preparación (cocinero)
    if cook_uuid and order.cook_uuid is None:
        order.cook_uuid = cook_uuid
        order.cook_name = cook_name

elif new_status == OrderStatus.READY and order.ready_at is None:
    order.ready_at = datetime.utcnow()
    # Si el cocinero aún no estaba registrado (orden tomada sin PREPARING)
    if cook_uuid and order.cook_uuid is None:
        order.cook_uuid = cook_uuid
        order.cook_name = cook_name

elif new_status == OrderStatus.DELIVERED and order.delivered_at is None:
    order.delivered_at = datetime.utcnow()
    # delivered_by ya maneja el plan de meseros
```

#### 3.2 — `update_order_item_status()`: registrar el cocinero por ítem

```python
async def update_order_item_status(
    session: AsyncSession,
    item_id: int,
    new_status: OrderStatus,
    cook_uuid: Optional[str] = None,    # NUEVO
    cook_name: Optional[str] = None,    # NUEVO
    delivered_by_uuid: Optional[str] = None,
    delivered_by_name: Optional[str] = None,
) -> Optional[OrderItem]:
    ...
    if new_status == OrderStatus.PREPARING and item.preparing_at is None:
        item.preparing_at = datetime.utcnow()
        if cook_uuid and item.cook_uuid is None:
            item.cook_uuid = cook_uuid
            item.cook_name = cook_name

    elif new_status == OrderStatus.READY and item.ready_at is None:
        item.ready_at = datetime.utcnow()
        if cook_uuid and item.cook_uuid is None:
            item.cook_uuid = cook_uuid
            item.cook_name = cook_name

    elif new_status == OrderStatus.DELIVERED and item.delivered_at is None:
        item.delivered_at = datetime.utcnow()
        if delivered_by_uuid:
            item.delivered_by_uuid = delivered_by_uuid
            item.delivered_by_name = delivered_by_name
```

#### 3.3 — `format_order_json()`: exponer los campos de cocina

Agregar en el `return {}` principal:

```python
# --- COCINA (nuevo) ---
"cook_uuid": order.cook_uuid,
"cook_name": order.cook_name,
```

Y en cada ítem de `items_data`:

```python
# --- COCINA (nuevo) ---
"cook_uuid": item.cook_uuid,
"cook_name": item.cook_name,
```

---

### FASE 4 — Router de Órdenes (`pos_core/sales/router.py`)

**Archivo:** `pos_core/sales/router.py` (**MODIFICAR**)

#### 4.1 — `update_status()`: pasar el cocinero al service

El `user` dict ya está disponible. Pasarlo al service cuando la transición es de cocina:

```python
@router.patch("/orders/{order_id}/status", response_model=Order)
async def update_status(
    order_id: int,
    status: OrderStatus,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role(["kitchen", "waiter", "cashier", "manager", "admin"])),
):
    is_kitchen_transition = status in (OrderStatus.PREPARING, OrderStatus.READY)
    is_delivery_transition = status == OrderStatus.DELIVERED

    order = await service.update_order_status(
        db,
        order_id,
        status,
        # Cocinero solo se graba en transiciones de producción
        cook_uuid=user.get("user_uuid") if is_kitchen_transition else None,
        cook_name=user.get("username") if is_kitchen_transition else None,
        # Mesero solo se graba en entrega
        delivered_by_uuid=user.get("user_uuid") if is_delivery_transition else None,
        delivered_by_name=user.get("username") if is_delivery_transition else None,
    )
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    asyncio.create_task(broadcast_updates())
    return order
```

#### 4.2 — `update_item_status()`: pasar el cocinero por ítem

```python
@router.patch("/orders/{order_id}/items/{item_id}/status")
async def update_item_status(
    order_id: int,
    item_id: int,
    status: OrderStatus,
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role(["kitchen", "waiter", "cashier", "manager", "admin"])),
):
    is_kitchen_transition = status in (OrderStatus.PREPARING, OrderStatus.READY)
    is_delivery_transition = status == OrderStatus.DELIVERED

    item = await service.update_order_item_status(
        db,
        item_id,
        status,
        cook_uuid=user.get("user_uuid") if is_kitchen_transition else None,
        cook_name=user.get("username") if is_kitchen_transition else None,
        delivered_by_uuid=user.get("user_uuid") if is_delivery_transition else None,
        delivered_by_name=user.get("username") if is_delivery_transition else None,
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    asyncio.create_task(broadcast_updates())
    return item
```

---

### FASE 5 — Analytics Endpoint (`pos_core/sales/analytics_router.py`)

**Archivo:** `pos_core/sales/analytics_router.py` (**MODIFICAR**)

Agregar dos endpoints nuevos: uno de desempeño por cocinero y otro de velocidad por platillo.

#### 5.1 — `GET /analytics/kitchen/performance` — Desempeño por cocinero

```python
@router.get("/kitchen/performance")
async def get_kitchen_performance(
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role(["admin", "manager"])),
):
    """
    Retorna estadísticas de desempeño por cocinero.
    Incluye: órdenes preparadas, tiempo promedio de preparación (PREPARING→READY).
    """
    from datetime import date, datetime
    today_start = datetime.combine(date.today(), datetime.min.time())

    # Órdenes tomadas por cook (hoy)
    stmt_orders = (
        select(
            Order.cook_uuid,
            Order.cook_name,
            func.count(Order.id).label("orders_handled"),
        )
        .where(
            Order.created_at >= today_start,
            Order.cook_uuid.isnot(None),
        )
        .group_by(Order.cook_uuid, Order.cook_name)
    )
    result_orders = await db.execute(stmt_orders)
    rows = result_orders.all()

    cook_stats = {}
    for row in rows:
        cook_stats[row.cook_uuid] = {
            "cook_uuid": row.cook_uuid,
            "cook_name": row.cook_name or "Desconocido",
            "orders_handled": row.orders_handled or 0,
            "avg_prep_seconds": None,  # se calcula abajo
            "items_prepared": 0,       # se calcula abajo
        }

    # Tiempo promedio de preparación: PREPARING → READY (por orden)
    stmt_times = (
        select(Order.cook_uuid, Order.preparing_at, Order.ready_at)
        .where(
            Order.created_at >= today_start,
            Order.preparing_at.isnot(None),
            Order.ready_at.isnot(None),
            Order.cook_uuid.isnot(None),
        )
    )
    result_times = await db.execute(stmt_times)
    time_rows = result_times.all()

    prep_times: dict[str, list[float]] = {}
    for row in time_rows:
        delta = (row.ready_at - row.preparing_at).total_seconds()
        if delta >= 0:
            prep_times.setdefault(row.cook_uuid, []).append(delta)

    for uuid, times in prep_times.items():
        if uuid in cook_stats and times:
            cook_stats[uuid]["avg_prep_seconds"] = round(sum(times) / len(times), 1)

    # Ítems preparados por cocinero (de OrderItem)
    stmt_items = (
        select(OrderItem.cook_uuid, func.count(OrderItem.id).label("items_count"))
        .where(
            OrderItem.cook_uuid.isnot(None),
            OrderItem.ready_at.isnot(None),
        )
        .group_by(OrderItem.cook_uuid)
    )
    result_items = await db.execute(stmt_items)
    for row in result_items.all():
        if row.cook_uuid in cook_stats:
            cook_stats[row.cook_uuid]["items_prepared"] = row.items_count

    result = sorted(cook_stats.values(), key=lambda x: x["orders_handled"], reverse=True)
    return result
```

#### 5.2 — `GET /analytics/kitchen/dish-speed` — Velocidad por platillo

```python
@router.get("/kitchen/dish-speed")
async def get_dish_speed(
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role(["admin", "manager"])),
):
    """
    Retorna el tiempo promedio de preparación por platillo.
    Útil para identificar cuellos de botella en el menú.
    Tiempo medido: desde preparing_at del ítem hasta ready_at del ítem.
    """
    from sqlalchemy.orm import selectinload

    stmt = (
        select(
            OrderItem.product_id,
            func.avg(
                func.julianday(OrderItem.ready_at) - func.julianday(OrderItem.preparing_at)
            ).label("avg_days"),
            func.count(OrderItem.id).label("sample_count"),
        )
        .where(
            OrderItem.preparing_at.isnot(None),
            OrderItem.ready_at.isnot(None),
        )
        .group_by(OrderItem.product_id)
        .order_by(func.avg(
            func.julianday(OrderItem.ready_at) - func.julianday(OrderItem.preparing_at)
        ).desc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    # Obtener nombres de productos
    product_ids = [row.product_id for row in rows]
    from pos_core.inventory.models import Product
    products_stmt = select(Product).where(Product.id.in_(product_ids))
    products_res = await db.execute(products_stmt)
    products = {p.id: p.name for p in products_res.scalars().all()}

    return [
        {
            "product_id": row.product_id,
            "product_name": products.get(row.product_id, f"Producto #{row.product_id}"),
            # julianday diferencia en días → convertir a segundos
            "avg_prep_seconds": round((row.avg_days or 0) * 86400, 1),
            "sample_count": row.sample_count,
        }
        for row in rows
    ]
```

---

### FASE 6 — Frontend: Sección "Desempeño de Cocina" en Admin

**Archivo:** `bs_frontend/src/routes/(app)/admin/analytics/+page.svelte` (**MODIFICAR**)

Agregar dos secciones debajo de la de meseros (del `WAITER_EFFICIENCY_PLAN.md`).

#### 6.1 — Fetch de datos

```typescript
let cookStats: CookStat[] = $state([]);
let dishSpeed: DishSpeed[] = $state([]);

interface CookStat {
    cook_uuid: string;
    cook_name: string;
    orders_handled: number;
    avg_prep_seconds: number | null;
    items_prepared: number;
}

interface DishSpeed {
    product_id: number;
    product_name: string;
    avg_prep_seconds: number;
    sample_count: number;
}

async function loadKitchenStats() {
    const token = localStorage.getItem('X-Omni-Token');
    const headers = { 'X-Omni-Token': token ?? '' };
    const [cooks, dishes] = await Promise.all([
        fetch('/api/analytics/kitchen/performance', { headers }).then(r => r.json()),
        fetch('/api/analytics/kitchen/dish-speed', { headers }).then(r => r.json()),
    ]);
    cookStats = cooks;
    dishSpeed = dishes;
}

function formatSeconds(secs: number | null): string {
    if (secs === null) return '—';
    const m = Math.floor(secs / 60);
    const s = Math.round(secs % 60);
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

function prepBadge(secs: number | null): { label: string; cls: string } {
    if (secs === null) return { label: 'Sin datos', cls: 'badge-neutral' };
    if (secs < 300)  return { label: '⚡ Rápido',  cls: 'badge-fast' };
    if (secs < 600)  return { label: '✅ Normal',  cls: 'badge-ok' };
    return             { label: '🐢 Lento',   cls: 'badge-slow' };
}
```

#### 6.2 — Sección UI: "Desempeño de Cocina"

```svelte
<!-- Sección: Desempeño de Cocina -->
<section class="team-performance">
    <h2>Desempeño de Cocina</h2>
    <p class="subtitle">Basado en órdenes del día de hoy</p>

    {#if cookStats.length === 0}
        <p class="empty-state">Sin datos de cocineros para hoy.</p>
    {:else}
        <div class="waiter-table-wrapper">
            <table class="waiter-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Cocinero</th>
                        <th>Órdenes</th>
                        <th>Ítems Preparados</th>
                        <th>Tiempo Prom. Prep.</th>
                        <th>Velocidad</th>
                    </tr>
                </thead>
                <tbody>
                    {#each cookStats as stat, i}
                        {@const badge = prepBadge(stat.avg_prep_seconds)}
                        <tr class:top={i === 0}>
                            <td>{i + 1}</td>
                            <td class="waiter-name">{stat.cook_name}</td>
                            <td>{stat.orders_handled}</td>
                            <td>{stat.items_prepared}</td>
                            <td>{formatSeconds(stat.avg_prep_seconds)}</td>
                            <td>
                                <span class="badge {badge.cls}">{badge.label}</span>
                            </td>
                        </tr>
                    {/each}
                </tbody>
            </table>
        </div>
    {/if}
</section>

<!-- Sub-sección: Velocidad por Platillo -->
<section class="team-performance" style="margin-top: 2rem;">
    <h2>Velocidad por Platillo</h2>
    <p class="subtitle">Tiempo promedio de preparación — datos históricos acumulados</p>

    {#if dishSpeed.length === 0}
        <p class="empty-state">Sin datos suficientes de preparación por ítem.</p>
    {:else}
        <div class="waiter-table-wrapper">
            <table class="waiter-table">
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Platillo</th>
                        <th>Tiempo Prom.</th>
                        <th>Muestras</th>
                        <th>Clasificación</th>
                    </tr>
                </thead>
                <tbody>
                    {#each dishSpeed as dish, i}
                        {@const badge = prepBadge(dish.avg_prep_seconds)}
                        <tr>
                            <td>{i + 1}</td>
                            <td class="waiter-name">{dish.product_name}</td>
                            <td>{formatSeconds(dish.avg_prep_seconds)}</td>
                            <td class="opacity-60">{dish.sample_count} pedidos</td>
                            <td>
                                <span class="badge {badge.cls}">{badge.label}</span>
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

### FASE 7 — KDS Frontend: mostrar el cocinero asignado

**Archivo:** `bs_frontend/src/routes/(app)/kitchen/+page.svelte` (**MODIFICAR**)

Cuando una orden ya tiene `cook_name` (alguien la tomó), mostrarlo en la tarjeta de la orden para que otros cocineros sepan quién es responsable.

```svelte
{#if order.cook_name}
    <span class="cook-badge">
        👨‍🍳 {order.cook_name}
    </span>
{/if}
```

CSS del badge:
```css
.cook-badge {
    display: inline-block;
    font-size: 0.7rem;
    padding: 2px 8px;
    border-radius: 99px;
    background: rgba(var(--color-warning-rgb), 0.15);
    color: var(--color-warning);
    font-weight: 600;
    margin-top: 4px;
}
```

---

## Orden de Ejecución y Checklist

```
FASE 1: Migración SQLite (cook_uuid/name en Order + OrderItem)   ~10 min
FASE 2: Actualizar models.py (Order + OrderItem)                  ~10 min
FASE 3: Actualizar service.py (grabar cook en transiciones)       ~20 min
FASE 4: Actualizar router.py (pasar user a service por transición) ~15 min
FASE 5: Dos endpoints analytics de cocina                         ~35 min
FASE 6: Frontend — dos secciones en /admin/analytics              ~50 min
FASE 7: KDS — mostrar cook_name asignado en tarjeta               ~15 min
───────────────────────────────────────────────────────────────────────────
Total estimado:                                                   ~2h 35min
```

### Checklist para el desarrollador

- [ ] **FASE 1** — Ejecutar `python scripts/migrate_kitchen_tracking.py`
- [ ] **FASE 2** — Agregar `cook_uuid` + `cook_name` a `Order` y `OrderItem` en `models.py`
- [ ] **FASE 3** — `update_order_status()` graba `cook_uuid/name` en transiciones PREPARING/READY
- [ ] **FASE 3** — `update_order_item_status()` graba `cook_uuid/name` por ítem
- [ ] **FASE 3** — `format_order_json()` serializa `cook_uuid` y `cook_name`
- [ ] **FASE 4** — `update_status()` en router distingue transición de cocina vs. entrega
- [ ] **FASE 4** — `update_item_status()` en router pasa cook o delivered_by según la transición
- [ ] **FASE 5.1** — Agregar endpoint `GET /analytics/kitchen/performance`
- [ ] **FASE 5.2** — Agregar endpoint `GET /analytics/kitchen/dish-speed`
- [ ] **FASE 6** — Agregar sección "Desempeño de Cocina" en `/admin/analytics`
- [ ] **FASE 6** — Agregar tabla "Velocidad por Platillo"
- [ ] **FASE 7** — Mostrar `cook_name` en tarjeta KDS
- [ ] **TEST MANUAL** — Flujo completo descrito abajo

---

## Advertencias y Puntos de Atención

> [!IMPORTANT]
> **Depende del WAITER_EFFICIENCY_PLAN.md**  
> Los campos `preparing_at`, `ready_at` y `delivered_at` los agrega `migrate_waiter_tracking.py`. Este plan **no los duplica**, solo agrega `cook_uuid` y `cook_name`. Ejecutar la migración de meseros **primero**.

> [!WARNING]
> **SQLite y palabra reservada `order`**  
> Igual que en el plan de meseros, usar backticks en las sentencias ALTER TABLE manuales: `` ALTER TABLE `order` ADD COLUMN ... ``

> [!NOTE]
> **Distinción por transición en el router**  
> El mismo endpoint `PATCH /orders/{id}/status` es usado por cocineros (PREPARING→READY) y meseros (→DELIVERED). La lógica diferencia quién graba qué según la transición, no según el rol. Esto permite que un cashier avance el estado sin romper el tracking.

> [!TIP]
> **`julianday()` en SQLite**  
> Para calcular diferencias de tiempo en segundos con SQLite, se usa `julianday(ready_at) - julianday(preparing_at)` multiplicado por 86400. Es la forma nativa de SQLite — no usar `DATEDIFF()` que no existe en SQLite.

> [!TIP]
> **Platillos sin timestamps por ítem**  
> Si el KDS opera a nivel de **orden completa** (no ítem por ítem), `OrderItem.preparing_at` puede quedar en NULL. En ese caso el endpoint `dish-speed` no tendrá datos hasta que el flujo de ítem por ítem esté activo. Documentar esto en el onboarding del restaurante.

---

## Verificación

### Manual
1. Abrir sesión como "Cocinero A" (rol `kitchen`).
2. En el KDS, marcar una orden como `PREPARING` → verificar en BD que `cook_uuid`, `cook_name` y `preparing_at` se guardaron en `Order`.
3. Marcar como `READY` → verificar `ready_at`.
4. Ir a `/admin/analytics` → confirmar que "Cocinero A" aparece en la tabla de desempeño de cocina.
5. Verificar que el tiempo promedio de preparación es correcto (`ready_at - preparing_at`).
6. Verificar que la tabla "Velocidad por Platillo" muestra datos después de algunas órdenes completadas.
7. En el KDS, verificar que la tarjeta de la orden muestra el nombre del cocinero que la tomó.

### Automatizada (opcional)
- Prueba unitaria para `update_order_status()` → estado PREPARING graba `cook_uuid` si `cook_uuid` es None.
- Prueba unitaria → segunda transición PREPARING no sobreescribe `cook_uuid` ya guardado.
- Prueba unitaria para `update_order_status()` → estado DELIVERED **no** graba `cook_uuid` (solo `delivered_by`).
