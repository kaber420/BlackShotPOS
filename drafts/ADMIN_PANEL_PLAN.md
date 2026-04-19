# Plan: Panel de Administración de Negocio

**Proyecto:** BlackShot POS  
**Estado:** BORRADOR — pendiente de aprobación  
**Fecha:** 2026-04-19  

---

## Problema

No existe un panel de administración centralizado. Lo que hay hoy:

| Ruta | Qué hace | Problema |
|---|---|---|
| `/admin/corte` | Cierra el turno activo | Sin historial — el corte desaparece |
| `/admin/analytics` | 3 KPIs del día actual | Datos efímeros, sin períodos, sin desglose |
| `/admin/users` | Lista de usuarios | Solo existencia, sin paneles admin reales |

**El dueño del negocio no puede responder preguntas básicas:**
- ¿Cuánto vendí esta semana?
- ¿El corte del martes pasado tuvo faltante o sobrante?
- ¿Qué mesero vendió más en el mes?
- ¿Cuántos cortes llevo este mes?

---

## Solución: `/admin` como portal de gestión

Crear una ruta `/admin` que funcione como **dashboard central** con navegación por secciones.  
Las rutas existentes (`/admin/corte`, `/admin/analytics`, etc.) se refactorizan o absorben en este panel.

### Mapa de navegación del panel admin

```
/admin                        ← Dashboard de negocio (KPIs, gráficas)
/admin/shifts                 ← Historial de todos los cortes (NUEVO)
/admin/shifts/[id]            ← Detalle auditables de un corte específico (NUEVO)
/admin/corte                  ← El corte actual (ya existe, se mantiene igual)
/admin/analytics              ← Analíticas (ya existe, se amplía)
/admin/users                  ← Usuarios y permisos (ya existe)
/admin/audits                 ← Log de auditoría (ya existe)
```

---

## Cambios Propuestos por Capa

---

### FASE 1 — Backend: Historial de Cortes

#### 1.1 — `GET /api/v1/pos/shifts/` — Listado de todos los cortes

**Archivo:** `pos_core/sales/shifts_router.py` (**MODIFICAR**)

Un endpoint que devuelve todos los turnos (no solo el activo), con totales precalculados para mostrar en la lista sin tener que cargar cada reporte.

```python
from sqlmodel import select
from .models import Shift, ShiftStatus

@router.get("/")
async def api_list_shifts(
    session: AsyncSession = Depends(get_session),
    user=Depends(require_role(["admin", "manager"])),
):
    """Lista todos los turnos (activos y cerrados) con totales básicos."""
    stmt = select(Shift).order_by(Shift.start_time.desc())
    result = await session.execute(stmt)
    shifts = result.scalars().all()

    out = []
    for shift in shifts:
        # Obtener totales de pagos de este turno
        pay_stmt = select(Payment).join(Order).where(Order.shift_id == shift.id)
        pay_res = await session.execute(pay_stmt)
        payments = pay_res.scalars().all()

        total = sum(p.amount for p in payments)
        cash  = sum(p.amount for p in payments if p.method == PaymentMethod.CASH)
        card  = sum(p.amount for p in payments if p.method == PaymentMethod.CARD)
        transfer = sum(p.amount for p in payments if p.method == PaymentMethod.TRANSFER)

        # Contar órdenes
        order_stmt = select(func.count(Order.id)).where(Order.shift_id == shift.id)
        order_res = await session.execute(order_stmt)
        order_count = order_res.scalar() or 0

        out.append({
            "id": shift.id,
            "status": shift.status,
            "start_time": shift.start_time.isoformat(),
            "end_time": shift.end_time.isoformat() if shift.end_time else None,
            "initial_cash": shift.initial_cash,
            "expected_cash": shift.expected_cash,
            "actual_cash": shift.actual_cash,
            "difference": shift.difference,
            "total_sales": total,
            "cash": cash,
            "card": card,
            "transfer": transfer,
            "orders_count": order_count,
        })
    return out
```

#### 1.2 — `GET /api/v1/pos/shifts/{shift_id}/report` — Ya existe

El endpoint de reporte por turno ya existe en `shifts_router.py`. Solo hay que asegurarse de que incluya también las órdenes del turno (lista resumida) para el detalle de auditoría:

**Extender `get_shift_report()` en `shifts_service.py`** para incluir:

```python
# Al final del return en get_shift_report()
"orders": [
    {
        "id": o.id,
        "type": o.type,
        "status": o.status,
        "total": sum(p.amount for p in o.payments),
        "created_at": o.created_at.isoformat(),
        "waiter_name": o.waiter_name,  # disponible tras el plan de meseros
        "items_count": len(o.items),
    }
    for o in orders_in_shift
]
```

Agregar el query de órdenes del turno en `shifts_service.py`:

```python
# En get_shift_report(), antes del return
from sqlalchemy.orm import selectinload
orders_stmt = (
    select(Order)
    .where(Order.shift_id == shift_id)
    .options(selectinload(Order.payments), selectinload(Order.items))
    .order_by(Order.created_at)
)
orders_res = await session.execute(orders_stmt)
orders_in_shift = orders_res.scalars().all()
```

---

### FASE 2 — Backend: Dashboard de Negocio

#### 2.1 — Extender `analytics_router.py`

**Archivo:** `pos_core/sales/analytics_router.py` (**MODIFICAR**)

Agregar endpoint `/analytics/business-summary` con filtro por período:

```python
from datetime import date, datetime, timedelta
from fastapi import Query

@router.get("/business-summary")
async def get_business_summary(
    period: str = Query("today", description="today | week | month | custom"),
    from_date: Optional[date] = Query(None),
    to_date: Optional[date] = Query(None),
    db: AsyncSession = Depends(get_session),
    user=Depends(require_role(["admin", "manager"])),
):
    """
    Resumen de negocio configurable por período.
    period: 'today', 'week', 'month', o 'custom' (requiere from_date + to_date).
    """
    now = datetime.utcnow()

    if period == "today":
        start = datetime.combine(now.date(), datetime.min.time())
        end = now
    elif period == "week":
        start = datetime.combine(now.date() - timedelta(days=now.weekday()), datetime.min.time())
        end = now
    elif period == "month":
        start = datetime.combine(now.date().replace(day=1), datetime.min.time())
        end = now
    elif period == "custom" and from_date and to_date:
        start = datetime.combine(from_date, datetime.min.time())
        end = datetime.combine(to_date, datetime.max.time())
    else:
        raise HTTPException(status_code=400, detail="Período inválido. Use: today, week, month, o custom con from_date/to_date.")

    # Ventas totales en el período
    stmt_sales = (
        select(func.sum(Payment.amount), func.count(Payment.id))
        .join(Order)
        .where(Payment.timestamp >= start, Payment.timestamp <= end)
    )
    res = await db.execute(stmt_sales)
    total_sales, total_payments = res.one()
    total_sales = total_sales or 0.0

    # Órdenes por estado
    stmt_orders = (
        select(Order.status, func.count(Order.id))
        .where(Order.created_at >= start, Order.created_at <= end)
        .group_by(Order.status)
    )
    res_orders = await db.execute(stmt_orders)
    orders_by_status = {row[0].value: row[1] for row in res_orders.all()}

    # Ventas por método de pago
    stmt_methods = (
        select(Payment.method, func.sum(Payment.amount))
        .where(Payment.timestamp >= start, Payment.timestamp <= end)
        .group_by(Payment.method)
    )
    res_methods = await db.execute(stmt_methods)
    by_method = {row[0].value: row[1] for row in res_methods.all()}

    # Cortes de caja en el período
    stmt_shifts = (
        select(func.count(Shift.id))
        .where(Shift.start_time >= start, Shift.status == ShiftStatus.CLOSED)
    )
    res_shifts = await db.execute(stmt_shifts)
    closed_shifts_count = res_shifts.scalar() or 0

    return {
        "period": period,
        "from": start.isoformat(),
        "to": end.isoformat(),
        "total_sales": round(total_sales, 2),
        "orders_by_status": orders_by_status,
        "by_payment_method": by_method,
        "closed_shifts_count": closed_shifts_count,
    }
```

---

### FASE 3 — Frontend: Ruta `/admin` (Dashboard Central)

**Archivo:** `bs_frontend/src/routes/(app)/admin/+page.svelte` (**NUEVO**)

Esta página es el punto de entrada del panel admin. Muestra:
1. KPIs del período seleccionado
2. Accesos rápidos a cada sección
3. Últimos cortes de caja (preview)

#### Estructura del componente

```svelte
<script lang="ts">
    import { onMount } from 'svelte';
    import { fetchApi } from '$lib/api';

    type Period = 'today' | 'week' | 'month';
    let period: Period = $state('today');
    let summary: any = $state(null);
    let recentShifts: any[] = $state([]);
    let loading = $state(true);

    onMount(async () => {
        await loadData();
    });

    async function loadData() {
        loading = true;
        try {
            [summary, recentShifts] = await Promise.all([
                fetchApi(`/api/v1/pos/analytics/business-summary?period=${period}`),
                fetchApi('/api/v1/pos/shifts/'),
            ]);
            // Solo mostrar los últimos 5
            recentShifts = recentShifts.slice(0, 5);
        } finally {
            loading = false;
        }
    }

    $effect(() => {
        // Recargar cuando cambiar el período
        void period;
        loadData();
    });
</script>

<!-- período selector: Hoy | Semana | Mes -->
<!-- KPI cards: Ventas, Órdenes, Cortes cerrados, Cancelaciones -->
<!-- Accesos rápidos: Corte de Caja, Historial, Analíticas, Usuarios -->
<!-- Tabla: Últimos 5 cortes con estado y diferencia -->
```

#### KPI Cards a mostrar

| Card | Dato | Color |
|---|---|---|
| 💰 Ventas Totales | `summary.total_sales` | Verde |
| 📋 Órdenes | suma de `orders_by_status` | Azul |
| ✂️ Cortes Cerrados | `summary.closed_shifts_count` | Violeta |
| ❌ Cancelaciones | `orders_by_status.CANCELLED` | Rojo |

#### Accesos Rápidos (grid 2x2 o 4 columnas)

```
┌─────────────────┬─────────────────┐
│  💵 Corte       │  📋 Historial   │
│  de Caja        │  de Cortes      │
├─────────────────┼─────────────────┤
│  📈 Analíticas  │  👥 Usuarios    │
│  de Ventas      │  y Permisos     │
└─────────────────┴─────────────────┘
```

#### Tabla de últimos cortes (preview)

Columnas: `#ID | Fecha | Duración | Total Ventas | Diferencia | Estado`

---

### FASE 4 — Frontend: Historial de Cortes `/admin/shifts`

**Archivo:** `bs_frontend/src/routes/(app)/admin/shifts/+page.svelte` (**NUEVO**)

Vista completa del historial de todos los cortes de caja.

#### Diseño

```
┌─────────────────────────────────────────────────┐
│  Historial de Cortes de Caja                    │
│  [Filtro por estado: Todos / Abiertos / Cerrados│
├─────────────────────────────────────────────────┤
│  #1  | Lun 14 Abr | 08:00 - 16:00 | $4,520 | ✅ │
│  #2  | Mar 15 Abr | 08:00 - 15:45 | $3,200 | ⚠️ │  ← diferencia
│  #3  | Mié 16 Abr | 07:55 - ...   | $1,800 | 🟡 │  ← abierto
└─────────────────────────────────────────────────┘
```

Cada fila es clickeable → navega a `/admin/shifts/[id]` para ver el detalle auditado.

Código base (fetch + tabla):

```typescript
let shifts: ShiftRow[] = $state([]);
let filterStatus: 'all' | 'OPEN' | 'CLOSED' = $state('all');

let filtered = $derived(
    filterStatus === 'all'
        ? shifts
        : shifts.filter(s => s.status === filterStatus)
);

onMount(async () => {
    shifts = await fetchApi('/api/v1/pos/shifts/');
});
```

---

### FASE 5 — Frontend: Detalle de Corte `/admin/shifts/[id]`

**Archivo:** `bs_frontend/src/routes/(app)/admin/shifts/[id]/+page.svelte` (**NUEVO**)

Vista de **auditoría completa** de un corte histórico.

#### Secciones

1. **Header:** ID del corte, fechas de apertura/cierre, duración
2. **Resumen financiero:** Fondo inicial, ventas por método, caja esperada vs. real, diferencia (color coded)
3. **Tabla de órdenes del turno:** todas las órdenes procesadas en ese turno, con total por orden y estado
4. **Botón imprimir** → genera una vista de impresión limpia (como el Reporte Z existente)

```svelte
<script lang="ts">
    import { page } from '$app/state';
    import { fetchApi } from '$lib/api';
    import { onMount } from 'svelte';

    let report: any = $state(null);
    const shiftId = $derived(Number(page.params.id));

    onMount(async () => {
        report = await fetchApi(`/api/v1/pos/shifts/${shiftId}/report`);
    });
</script>

{#if report}
    <!-- Header -->
    <!-- Tarjetas: Fondo | Ventas Efectivo | Caja Esperada | Real | Diferencia -->
    <!-- Desglose: Tarjeta, Transferencia, Total General -->
    <!-- Tabla órdenes del turno -->
    <!-- Botón imprimir -->
{/if}
```

---

### FASE 6 — Actualizar `/admin/analytics` (ampliar período)

**Archivo:** `bs_frontend/src/routes/(app)/admin/analytics/+page.svelte` (**MODIFICAR**)

En lugar de solo mostrar "hoy", agregar el **selector de período** que conecta con el nuevo endpoint `/analytics/business-summary`:

```svelte
<!-- Tabs: Hoy | Esta Semana | Este Mes | Personalizado -->
```

Agregar también el historial de cortes como widget en esta página (o enlazar al `/admin/shifts`).

---

### FASE 7 — Agregar sección admin al layout de navegación

**Archivo:** `bs_frontend/src/routes/(app)/+layout.svelte` (**MODIFICAR**)

Agregar un link a `/admin` en el menú dropdown del usuario (ya existen links a sub-rutas, falta el panel principal):

```svelte
{#if can.viewReports() || can.manageShifts() || can.manageUsers()}
    <li><a href="/admin">🏠 Panel Admin</a></li>
    <li class="menu-title"><span>Admin</span></li>
{/if}
```

---

## Orden de Ejecución y Checklist

```
FASE 1: Backend — listar todos los shifis + extender reporte   ~30 min
FASE 2: Backend — endpoint business-summary con períodos       ~30 min
FASE 3: Frontend — /admin (dashboard central)                  ~90 min
FASE 4: Frontend — /admin/shifts (historial)                   ~60 min
FASE 5: Frontend — /admin/shifts/[id] (auditoría de corte)     ~60 min
FASE 6: Frontend — ampliar /admin/analytics con períodos       ~30 min
FASE 7: Frontend — actualizar nav layout                       ~10 min
─────────────────────────────────────────────────────────────────────
Total estimado:                                               ~5h 10min
```

### Checklist para el desarrollador

**Backend**
- [ ] **F1.1** — Agregar `GET /shifts/` (listado completo con totales) en `shifts_router.py`
- [ ] **F1.2** — Extender `get_shift_report()` en `shifts_service.py` para incluir lista de órdenes del turno
- [ ] **F2** — Agregar `GET /analytics/business-summary?period=` en `analytics_router.py`

**Frontend**
- [ ] **F3** — Crear `bs_frontend/src/routes/(app)/admin/+page.svelte` (dashboard)
- [ ] **F4** — Crear `bs_frontend/src/routes/(app)/admin/shifts/+page.svelte` (historial)
- [ ] **F5** — Crear `bs_frontend/src/routes/(app)/admin/shifts/[id]/+page.svelte` (detalle auditable)
- [ ] **F6** — Modificar `/admin/analytics` para soportar selector de período
- [ ] **F7** — Agregar link a `/admin` en navbar dropdown

---

## Qué queda para después (siguiente plan)

Una vez que el panel admin exista, el plan de eficiencia de meseros (`WAITER_EFFICIENCY_PLAN.md`) se implementa agregando:
- Una sección "Desempeño de Equipo" dentro de `/admin` 
- Un endpoint backend `GET /analytics/waiters/performance` (ya documentado en ese plan)

---

## Advertencias

> [!WARNING]
> **`/admin/corte` sigue igual** — no se toca. Sigue siendo la página para hacer el corte del turno activo. El historial va en `/admin/shifts`.

> [!IMPORTANT]
> **Verificar el prefix del router de shifts** — en el entry point del backend confirmar con qué prefijo está montado `shifts_router` (probablemente `/api/v1/pos/shifts`). El frontend usa ese path.

> [!NOTE]
> **El endpoint `GET /shifts/` no existía** — solo existía `GET /shifts/active` y `GET /shifts/{id}/report`. El nuevo endpoint de listado es nuevo.

---

## Verificación Manual

1. Ir a `/admin` → ver KPIs del día
2. Cambiar período a "Semana" → ver que los totales cambian
3. Ir a `/admin/shifts` → ver la lista de todos los cortes históricos
4. Hacer click en un corte → ver el detalle completo con todas las órdenes de ese turno
5. Verificar que el corte del día anterior es auditable
6. Confirmar que la diferencia (faltante/sobrante) se muestra con el color correcto
