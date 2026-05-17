# RFC-CAJA: Módulo de Gastos / Caja Chica — Plan de Implementación

> **Estado:** ✅ Completado (Fase 1 ✅ | Fase 2 ✅ | Fase 3 ✅)  
> **Prioridad:** P1  
> **Referencia Roadmap:** §3. Control Interno y Caja Chica  
> **Última actualización:** 2026-05-17

---

## 1. Contexto

El módulo de contabilidad actual permite registrar movimientos de caja (INCOME/EXPENSE/WITHDRAWAL) y cerrar turnos con Corte Z. Sin embargo, tiene gaps críticos que impiden su uso como herramienta real de control de gastos:

- El modelo `CashMovementCategory` existe pero es **código muerto** (sin CRUD, sin UI, sin seeds).
- ~~La tabla de movimientos del turno activo **no carga los datos** (falta `selectinload`).~~ ✅ Resuelto en Fase 1
- ~~La fórmula de "Ventas" en la card de efectivo es **incorrecta** (mezcla ventas con gastos).~~ ✅ Resuelto en Fase 1
- No hay desglose de gastos por categoría en el reporte del Corte Z.
- No se registra el nombre del usuario que ejecutó el movimiento en los reportes.

**Objetivo:** Completar el módulo para que un dueño/administrador pueda:
1. Registrar gastos operativos clasificados desde el POS.
2. Ver el historial de movimientos en tiempo real durante el turno.
3. Obtener un reporte de gastos desglosado por categoría en el Corte Z.

---

## 2. Cambios Propuestos

### Fase 1: Bugfixes Críticos (P0) — ✅ COMPLETADA (2026-05-17)

#### 2.1 — Cargar `movements` en `enrich_shift_data`

**Archivo:** `pos_core/accounting/service.py` → `enrich_shift_data()`

**Problema:** `shift.model_dump()` no incluye la relación `movements` porque no se carga con `selectinload`. La tabla de movimientos del frontend siempre aparece vacía.

**Solución:**
- Agregar query explícita de `CashMovement` para el shift.
- Incluir los movimientos serializados en el dict de respuesta.

```python
async def enrich_shift_data(session: AsyncSession, shift: Shift) -> dict:
    data = shift.model_dump()
    data["expected_cash"] = round(shift.expected_cash, 2)
    data["expected_card"] = round(shift.expected_card, 2)
    data["expected_transfer"] = round(shift.expected_transfer, 2)
    
    totals = await calculate_shift_totals(session, shift.id)
    data["withdrawals"] = round(totals["withdrawals"], 2)
    data["expenses"] = round(totals["expenses"], 2)
    data["incomes"] = round(totals["incomes"], 2)
    
    # ── NUEVO: Cargar movimientos del turno ──
    mov_stmt = select(CashMovement).where(CashMovement.shift_id == shift.id).order_by(CashMovement.timestamp.desc())
    mov_res = await session.execute(mov_stmt)
    movements = mov_res.scalars().all()
    data["movements"] = [
        {
            "id": m.id,
            "amount": m.amount,
            "type": m.type,
            "reason": m.reason,
            "category_id": m.category_id,  # Para fase 2
            "timestamp": m.timestamp.isoformat()
        } for m in movements
    ]
    
    return data
```

#### 2.2 — Corregir fórmula "Ventas" en el frontend

**Archivo:** `bs_frontend/src/routes/(app)/accounting/+page.svelte` L112

**Problema:** `expected_cash - initial_cash` incluye gastos/retiros restados, mostrando un número falso como "Ventas".

**Solución:** Usar los datos del reporte (`activeShiftReport.sales.cash`) que sí calcula ventas puras:

```svelte
<!-- Antes -->
Ventas: {formatCurrency(activeShift.expected_cash - activeShift.initial_cash)}

<!-- Después -->
Ventas: {formatCurrency(activeShiftReport?.sales?.cash ?? 0)}
```

Y agregar desglose de movimientos debajo:
```svelte
{#if activeShift.expenses > 0 || activeShift.withdrawals > 0}
    <span>•</span>
    <span class="text-error">Gastos: -{formatCurrency(activeShift.expenses)}</span>
    {#if activeShift.withdrawals > 0}
        <span>•</span>
        <span class="text-info">Retiros: -{formatCurrency(activeShift.withdrawals)}</span>
    {/if}
{/if}
```

#### 2.3 — Validación de monto en backend

**Archivo:** `pos_core/accounting/service.py` → `add_cash_movement()`

```python
if amount <= 0:
    raise HTTPException(status_code=422, detail="Amount must be greater than zero")
```

#### 2.4* — Fix adicional: Fórmula "Venta Total Bruta" (detectado en auditoría)

> **No documentado en el draft original.** Se detectó durante la auditoría de código.

**Archivo:** `bs_frontend/src/routes/(app)/accounting/+page.svelte` L132

**Problema:** La card "Venta Total Bruta" usaba `expected_cash + expected_card + expected_transfer - initial_cash`, que —al igual que el bug 2.2— incluye gastos y retiros ya restados del `expected_cash`, dando una cifra de venta inferior a la real.

**Solución:** Reemplazar con `activeShiftReport?.sales?.total ?? 0` que suma ventas puras de todos los métodos de pago.

#### Resumen de cambios Fase 1

| Archivo | Cambio | Líneas |
|---|---|---|
| `pos_core/accounting/service.py` | Query explícita de `CashMovement` en `enrich_shift_data()` | +19 líneas |
| `pos_core/accounting/service.py` | Guard `amount <= 0` → HTTP 422 en `add_cash_movement()` | +3 líneas |
| `bs_frontend/src/lib/api/shifts.ts` | `ShiftInfo` extendido con `movements[]`, `expenses`, `withdrawals`, `incomes`; `addCashMovement` type incluye `WITHDRAWAL` | +13 líneas |
| `bs_frontend/src/routes/(app)/accounting/+page.svelte` | Fórmula "Ventas" usa `activeShiftReport.sales.cash`; desglose Gastos/Retiros | +8 líneas |
| `bs_frontend/src/routes/(app)/accounting/+page.svelte` | Fórmula "Venta Total Bruta" usa `activeShiftReport.sales.total` | 1 línea |

---

### Fase 2: Categorías de Movimiento (P1) — ✅ COMPLETADA (2026-05-17)

#### 2.4 — CRUD de Categorías

**Archivo:** `pos_core/accounting/router.py` (agregar endpoints)

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/movement-categories` | Lista todas las categorías |
| `POST` | `/movement-categories` | Crea una nueva categoría |

**Schema nuevo:**

```python
class CreateMovementCategoryRequest(BaseModel):
    name: str
    type: CashMovementType
    description: Optional[str] = None
```

**Archivo:** `pos_core/accounting/service.py` (agregar funciones)

```python
async def get_movement_categories(session: AsyncSession) -> List[CashMovementCategory]:
    stmt = select(CashMovementCategory).order_by(CashMovementCategory.type, CashMovementCategory.name)
    result = await session.execute(stmt)
    return result.scalars().all()

async def create_movement_category(session: AsyncSession, name: str, type: CashMovementType, description: str = None) -> CashMovementCategory:
    cat = CashMovementCategory(name=name, type=type, description=description)
    session.add(cat)
    await session.commit()
    await session.refresh(cat)
    return cat
```

#### 2.5 — Actualizar `CashMovementRequest` y servicio

**Archivo:** `pos_core/accounting/router.py`

```python
class CashMovementRequest(BaseModel):
    amount: float
    type: CashMovementType
    reason: str
    category_id: Optional[int] = None  # ← NUEVO
```

**Archivo:** `pos_core/accounting/service.py` → `add_cash_movement()`
- Agregar parámetro `category_id: Optional[int] = None`
- Validar que la categoría exista si se proporciona
- Pasar al constructor de `CashMovement`

#### 2.6 — Seed de categorías iniciales

**Archivo:** `scripts/seeds/seed_data.py` (o nuevo `seed_movement_categories.py`)

```python
DEFAULT_CATEGORIES = [
    # Gastos
    {"name": "Compra de Insumos",     "type": "EXPENSE",    "description": "Compras de materia prima e ingredientes"},
    {"name": "Limpieza",              "type": "EXPENSE",    "description": "Productos y servicios de limpieza"},
    {"name": "Mantenimiento",         "type": "EXPENSE",    "description": "Reparaciones y mantenimiento de equipo"},
    {"name": "Propinas / Personal",   "type": "EXPENSE",    "description": "Pagos directos a empleados"},
    {"name": "Servicios",             "type": "EXPENSE",    "description": "Agua, luz, gas, internet"},
    {"name": "Varios / Emergencias",  "type": "EXPENSE",    "description": "Gastos no categorizados"},
    # Retiros
    {"name": "Retiro Parcial",        "type": "WITHDRAWAL", "description": "Retiro de seguridad del efectivo en caja"},
    # Ingresos
    {"name": "Fondo Extra",           "type": "INCOME",     "description": "Adición de efectivo al fondo de caja"},
    {"name": "Corrección",            "type": "INCOME",     "description": "Ajuste por error en conteo previo"},
]
```

#### 2.7 — Frontend: Selector de categoría en el modal

**Archivo:** `bs_frontend/src/lib/api/shifts.ts`

```typescript
export interface MovementCategory {
    id: number;
    name: string;
    type: 'INCOME' | 'EXPENSE' | 'WITHDRAWAL';
    description: string | null;
}

export async function getMovementCategories() {
    return await fetchApi<MovementCategory[]>('/api/v1/pos/sales/shifts/movement-categories');
}
```

**Archivo:** `bs_frontend/src/lib/components/accounting/CashMovementModal.svelte`

Cambios:
- Cargar categorías al montar con `getMovementCategories()`
- Filtrar categorías según el `type` seleccionado
- Agregar un `<select>` o botones de categoría entre el selector de tipo y el campo de monto
- Enviar `category_id` en el payload

```svelte
<!-- Nuevo selector de categoría (después del selector de tipo) -->
{#if filteredCategories.length > 0}
    <div class="form-control">
        <label class="label">
            <span class="label-text font-black text-xs uppercase tracking-widest opacity-60">Categoría</span>
        </label>
        <div class="flex flex-wrap gap-2">
            {#each filteredCategories as cat}
                <button 
                    class="btn btn-sm {selectedCategoryId === cat.id ? 'btn-primary' : 'btn-ghost'}"
                    onclick={() => selectedCategoryId = cat.id}
                >
                    {cat.name}
                </button>
            {/each}
        </div>
    </div>
{/if}
```

---

### Fase 3: Reportes y Visibilidad (P1) — ✅ COMPLETADA (2026-05-17)

#### 2.8 — Nombre del actor en movimientos

**Archivo:** `pos_core/accounting/service.py` → `get_shift_report()` y `enrich_shift_data()`

- Hacer join con `User` para obtener `display_name` del `user_id` de cada movimiento.
- Incluir `actor_name` en la serialización de movimientos.

```python
from pos_core.auth.models import User

# En la serialización de movimientos:
user = await session.get(User, m.user_id)
"actor_name": user.display_name if user else "Sistema"
```

#### 2.9 — Desglose de gastos en el Corte Z

**Archivo:** `pos_core/accounting/service.py` → `get_shift_report()`

Agregar sección `expense_summary` agrupada por categoría:

```python
# Agrupar movimientos por categoría
from collections import defaultdict
expense_by_category = defaultdict(float)
for m in movements:
    if m.type in (CashMovementType.EXPENSE, CashMovementType.WITHDRAWAL):
        cat_name = "Sin categoría"
        if m.category_id:
            cat = await session.get(CashMovementCategory, m.category_id)
            cat_name = cat.name if cat else "Sin categoría"
        expense_by_category[cat_name] += m.amount

# Incluir en la respuesta:
"expense_summary": [
    {"category": k, "total": round(v, 2)} 
    for k, v in sorted(expense_by_category.items(), key=lambda x: -x[1])
]
```

**Archivo:** `bs_frontend/src/routes/(app)/accounting/+page.svelte`

Agregar sección visual entre las cards de resumen y la tabla de movimientos:

- Barra horizontal por categoría con porcentaje del total de gastos
- Total general de gastos prominente

---

## 3. Archivos Afectados (Resumen)

### Backend
| Archivo | Acción |
|---|---|
| `pos_core/accounting/service.py` | MODIFY — enrich, add_movement, report |
| `pos_core/accounting/router.py` | MODIFY — nuevo schema, 2 endpoints nuevos |
| `pos_core/accounting/models.py` | SIN CAMBIOS (ya está listo) |
| `scripts/seeds/seed_data.py` | MODIFY — agregar seed de categorías |

### Frontend
| Archivo | Acción |
|---|---|
| `bs_frontend/src/lib/api/shifts.ts` | MODIFY — nuevo tipo + función API |
| `bs_frontend/src/lib/components/accounting/CashMovementModal.svelte` | MODIFY — selector de categoría |
| `bs_frontend/src/routes/(app)/accounting/+page.svelte` | MODIFY — fix fórmula + sección gastos |

---

## 4. Migración de Base de Datos

La tabla `cashmovementcategory` ya debería existir si los modelos se crearon con `create_all`. Si no:

```sql
CREATE TABLE IF NOT EXISTS cashmovementcategory (
    id SERIAL PRIMARY KEY,
    name VARCHAR UNIQUE NOT NULL,
    type VARCHAR NOT NULL,  -- 'INCOME', 'EXPENSE', 'WITHDRAWAL'
    description VARCHAR
);

-- La FK en cashmovment ya existe en el modelo
-- Solo verificar que la columna category_id esté en la tabla
ALTER TABLE cashmovement ADD COLUMN IF NOT EXISTS category_id INTEGER REFERENCES cashmovementcategory(id);
```

---

## 5. Plan de Ejecución

| Fase | Descripción | Estimado | Estado |
|---|---|---|---|
| **Fase 1** | Bugfixes (movements, fórmulas, validación) + fix adicional Venta Total | ~30 min | ✅ Completada 2026-05-17 |
| **Fase 2** | Categorías (CRUD, seed, UI selector) | ~1.5 hrs | ✅ Completada 2026-05-17 |
| **Fase 3** | Reportes (actor name, desglose en Corte Z) | ~1 hr | ✅ Completada 2026-05-17 |
| **Total** | | **~3 hrs** | ✅ |

### Orden de implementación:
1. ~~Fase 1.1 → Verificar que los movimientos ya aparecen en la tabla~~ ✅
2. ~~Fase 1.2 → Verificar que "Ventas" muestra el número correcto~~ ✅
3. ~~Fase 1.3 → Validación backend~~ ✅
4. ~~Fase 1.4* → Fix "Venta Total Bruta" (hallazgo de auditoría)~~ ✅
5. ~~Fase 2.6 → Seed primero (para tener datos)~~ ✅
6. ~~Fase 2.4 → CRUD endpoints~~ ✅
7. ~~Fase 2.5 → Actualizar request/servicio~~ ✅
8. ~~Fase 2.7 → UI del selector~~ ✅
9. ~~Fase 3.8 → Actor name~~ ✅
10. ~~Fase 3.9 → Desglose en Corte Z~~ ✅

---

## 6. Verificación

- [x] Registrar un gasto → aparece inmediatamente en la tabla de movimientos *(Fase 1 — enrich_shift_data)*
- [x] La card "Efectivo en Caja" muestra Ventas correctas (sin restar gastos) *(Fase 1 — activeShiftReport.sales.cash)*
- [x] La card "Venta Total Bruta" muestra ventas reales *(Fase 1 — activeShiftReport.sales.total)*
- [x] El modal muestra categorías filtradas por tipo *(Fase 2)*
- [x] El Corte Z incluye sección de desglose de gastos *(Fase 3)*
- [x] Los movimientos muestran quién los registró *(Fase 3)*
- [x] Enviar `amount: -50` al API → retorna 422 *(Fase 1 — guard clause)*
- [x] La fórmula `Efectivo Esperado = Fondo + Ventas - Gastos - Retiros` cuadra *(Fase 1 — desglose visual)*
