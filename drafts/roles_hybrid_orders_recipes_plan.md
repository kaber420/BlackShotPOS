# Plan de Implementación: Roles, Permisos Granulares, Gestión Híbrida y Recetario Markdown

**Fecha:** 2026-04-15  
**Proyecto:** BlackShot POS  
**Estado:** BORRADOR v2 — pendiente de aprobación

---

## Cambio de Enfoque respecto a v1

La v1 proponía roles rígidos. Esto no cubre la realidad operativa:

> *"Un mesero toma pedidos y los manda a cocina — eso siempre. ¿Puede cobrar? Eso depende del restaurante."*

La solución correcta es: **Roles como presets de permisos + permisos individuales toggleables por usuario**, almacenados en el campo `metadata` JSON que ya existe en la tabla `users` de `omni_auth`.

---

## Arquitectura: Roles + Permisos Granulares

### Concepto

```
┌─────────────────────────────────────────────────────────┐
│                  USUARIO: Juan (waiter)                 │
├─────────────────────────────────────────────────────────┤
│  ROLE PRESET → "waiter"                                 │
│  Otorga por defecto:                                    │
│    ✅ can_take_orders   ✅ can_send_to_kitchen           │
│    ✅ can_view_orders   ✅ can_manage_tables             │
│    ❌ can_charge        ❌ can_manage_kitchen_status     │
├─────────────────────────────────────────────────────────┤
│  PERMISO OVERRIDE (en metadata JSON):                   │
│    "permissions": { "can_charge": true }               │
│  → Resultado: Juan SÍ puede cobrar en su tablet        │
└─────────────────────────────────────────────────────────┘
```

El **rol define el preset base**. Los **permisos en `metadata`** pueden activar o desactivar capacidades específicas sobre ese preset. Un admin puede cambiar permisos individuales desde el panel de usuarios sin cambiar el rol.

---

## Permisos del Sistema

| Permiso | Descripción |
|---|---|
| `can_take_orders` | Usar el POS para crear órdenes y agregar ítems |
| `can_send_to_kitchen` | Enviar comandas a cocina |
| `can_charge` | Procesar pagos y cobrar órdenes |
| `can_manage_kitchen_status` | Avanzar estados de ítems (Pendiente→Preparando→Listo) |
| `can_view_orders` | Ver la lista de órdenes recientes |
| `can_manage_tables` | Ver y administrar el tablero de mesas |
| `can_view_kitchen` | Acceder a la pantalla de Cocina (KDS) |
| `can_manage_menu` | Editar productos, categorías, recetas |
| `can_manage_inventory` | Gestionar ingredientes y stock |
| `can_manage_users` | Crear/editar usuarios y sus permisos |
| `can_manage_shifts` | Abrir y cerrar turnos de caja |
| `can_view_reports` | Ver reportes de ventas y estadísticas |

---

## Presets por Rol (Valores por Defecto)

| Permiso | `admin` | `manager` | `cashier` | `kitchen` | `waiter` |
|---|:---:|:---:|:---:|:---:|:---:|
| `can_take_orders` | ✅ | ✅ | ✅ | ❌ | ✅ |
| `can_send_to_kitchen` | ✅ | ✅ | ✅ | ❌ | ✅ |
| `can_charge` | ✅ | ✅ | ✅ | ❌ | **❌** |
| `can_manage_kitchen_status` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `can_view_orders` | ✅ | ✅ | ✅ | ✅ | ✅ |
| `can_manage_tables` | ✅ | ✅ | ✅ | ❌ | ✅ |
| `can_view_kitchen` | ✅ | ✅ | ✅ | ✅ | ❌ |
| `can_manage_menu` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `can_manage_inventory` | ✅ | ✅ | ❌ | ❌ | ❌ |
| `can_manage_users` | ✅ | ❌ | ❌ | ❌ | ❌ |
| `can_manage_shifts` | ✅ | ✅ | ✅ | ❌ | ❌ |
| `can_view_reports` | ✅ | ✅ | ✅ | ❌ | ❌ |

> **Nota clave sobre `waiter`:**
> - ✅ Toma pedidos y los manda a cocina (es su función principal)
> - ❌ No cobra por defecto — se activa desde el panel de admin si el restaurante lo necesita (pago tableside con tablet + impresora térmica)
> - ❌ No ve ni gestiona estados de cocina — eso es de cocina/cajero

> **Caso de uso: barra de café sin separación de roles**
> Asignar rol `cashier` a la persona. Un cajero tiene todos los permisos operativos: toma pedidos, manda a cocina, avanza estados de preparación y cobra — todo desde una sola pantalla.

---

## Dónde se Almacenan los Permisos

### `omni_auth.db` → tabla `users` → columna `metadata` (TEXT/JSON)

Esta columna **ya existe** en el esquema actual. Se usa como storage JSON libre. Se guarda así:

```json
{
  "permissions": {
    "can_charge": true,
    "can_view_kitchen": true
  }
}
```

Solo se almacenan los **overrides** respecto al preset del rol. Si un permiso no está en `metadata.permissions`, se usa el valor del preset del rol. Esto mantiene el storage mínimo.

### Flujo de resolución de permisos (backend y frontend)

```
effective_permission(perm) =
  metadata.permissions[perm]   // Override explícito (mayor prioridad)
  ?? ROLE_PRESETS[role][perm]  // Default del preset del rol
  ?? false                     // Denegado si no definido
```

---

## Cambios Propuestos — Detalle por Fase

---

### FASE 1 — Constantes de Roles y Presets (Backend)

#### [NEW] `pos_core/roles.py`

```python
from typing import Dict, Set

class PosRole:
    ADMIN   = "admin"
    MANAGER = "manager"
    CASHIER = "cashier"
    KITCHEN = "kitchen"
    WAITER  = "waiter"

# Permisos disponibles en el sistema
class Permission:
    TAKE_ORDERS          = "can_take_orders"
    SEND_TO_KITCHEN      = "can_send_to_kitchen"
    CHARGE               = "can_charge"
    MANAGE_KITCHEN_STATUS = "can_manage_kitchen_status"
    VIEW_ORDERS          = "can_view_orders"
    MANAGE_TABLES        = "can_manage_tables"
    VIEW_KITCHEN         = "can_view_kitchen"
    MANAGE_MENU          = "can_manage_menu"
    MANAGE_INVENTORY     = "can_manage_inventory"
    MANAGE_USERS         = "can_manage_users"
    MANAGE_SHIFTS        = "can_manage_shifts"
    VIEW_REPORTS         = "can_view_reports"

# Presets por rol — valores por defecto
ROLE_PRESETS: Dict[str, Dict[str, bool]] = {
    PosRole.ADMIN: {p: True for p in vars(Permission).values() if not p.startswith("_")},
    PosRole.MANAGER: {
        Permission.TAKE_ORDERS: True,
        Permission.SEND_TO_KITCHEN: True,
        Permission.CHARGE: True,
        Permission.MANAGE_KITCHEN_STATUS: True,
        Permission.VIEW_ORDERS: True,
        Permission.MANAGE_TABLES: True,
        Permission.VIEW_KITCHEN: True,
        Permission.MANAGE_MENU: True,
        Permission.MANAGE_INVENTORY: True,
        Permission.MANAGE_USERS: False,
        Permission.MANAGE_SHIFTS: True,
        Permission.VIEW_REPORTS: True,
    },
    PosRole.CASHIER: {
        Permission.TAKE_ORDERS: True,
        Permission.SEND_TO_KITCHEN: True,
        Permission.CHARGE: True,
        Permission.MANAGE_KITCHEN_STATUS: True,
        Permission.VIEW_ORDERS: True,
        Permission.MANAGE_TABLES: True,
        Permission.VIEW_KITCHEN: True,
        Permission.MANAGE_MENU: False,
        Permission.MANAGE_INVENTORY: False,
        Permission.MANAGE_USERS: False,
        Permission.MANAGE_SHIFTS: True,
        Permission.VIEW_REPORTS: True,
    },
    PosRole.KITCHEN: {
        Permission.TAKE_ORDERS: False,
        Permission.SEND_TO_KITCHEN: False,
        Permission.CHARGE: False,
        Permission.MANAGE_KITCHEN_STATUS: True,
        Permission.VIEW_ORDERS: True,
        Permission.MANAGE_TABLES: False,
        Permission.VIEW_KITCHEN: True,
        Permission.MANAGE_MENU: False,
        Permission.MANAGE_INVENTORY: False,
        Permission.MANAGE_USERS: False,
        Permission.MANAGE_SHIFTS: False,
        Permission.VIEW_REPORTS: False,
    },
    PosRole.WAITER: {
        Permission.TAKE_ORDERS: True,
        Permission.SEND_TO_KITCHEN: True,
        Permission.CHARGE: False,         # Toggle activo desde admin si se necesita
        Permission.MANAGE_KITCHEN_STATUS: False,
        Permission.VIEW_ORDERS: True,
        Permission.MANAGE_TABLES: True,
        Permission.VIEW_KITCHEN: False,
        Permission.MANAGE_MENU: False,
        Permission.MANAGE_INVENTORY: False,
        Permission.MANAGE_USERS: False,
        Permission.MANAGE_SHIFTS: False,
        Permission.VIEW_REPORTS: False,
    },
}

def resolve_permissions(role: str, metadata_permissions: dict) -> Dict[str, bool]:
    """
    Combina el preset del rol con los overrides individuales del usuario.
    Los overrides en metadata tienen prioridad absoluta sobre el preset.
    """
    base = ROLE_PRESETS.get(role, {}).copy()
    base.update(metadata_permissions)  # Override explícito gana
    return base
```

---

### FASE 2 — Endpoint `/_auth/me` Extendido + Endpoint de Permisos

#### [MODIFY] `omni_auth/api.py`

Actualizar el endpoint `/me` para devolver permisos efectivos:

```python
@router.get("/me")
async def get_current_user(user_info: dict = Depends(verify_omni_token)):
    import json
    from pos_core.roles import resolve_permissions
    
    # Leer metadata del usuario desde la BD
    user = database.get_user(user_uuid=user_info["user_uuid"])
    metadata = json.loads(user.get("metadata") or "{}")
    metadata_permissions = metadata.get("permissions", {})
    
    effective_permissions = resolve_permissions(
        user_info["role"], metadata_permissions
    )
    
    return {
        "uuid": user_info["user_uuid"],
        "username": user_info["username"],
        "role": user_info["role"],
        "is_elevated": user_info.get("is_elevated", False),
        "permissions": effective_permissions,
    }
```

Agregar nuevo endpoint para actualizar permisos específicos de un usuario:

```python
@router.patch("/users/{user_uuid}/permissions")
async def update_user_permissions(
    user_uuid: str,
    body: dict,  # {"can_charge": true, "can_view_kitchen": false}
    user_info: dict = Depends(verify_omni_token)
):
    """Actualiza permisos individuales de un usuario. Solo admin."""
    if user_info["role"] != "admin":
        raise HTTPException(status_code=403, detail="Solo admins pueden editar permisos.")
    
    import json
    user = database.get_user(user_uuid=user_uuid)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    
    metadata = json.loads(user.get("metadata") or "{}")
    if "permissions" not in metadata:
        metadata["permissions"] = {}
    metadata["permissions"].update(body)
    
    database.update_user_metadata(user_uuid, json.dumps(metadata))
    return {"status": "ok", "permissions": metadata["permissions"]}
```

#### [MODIFY] `omni_auth/database.py`

Agregar función `update_user_metadata`:

```python
def update_user_metadata(user_uuid: str, metadata_json: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET metadata = ? WHERE uuid = ?",
        (metadata_json, user_uuid)
    )
    conn.commit()
    conn.close()
```

---

### FASE 3 — Estado Global con Permisos (Frontend)

#### [MODIFY] `bs_frontend/src/lib/app_state.svelte.ts`

```typescript
export const appState = $state({
    currentTheme: 'corporate',
    isLoggedIn: false,
    cart: [] as any[],
    activeTable: null as any | null,
    activeOrder: null as any | null,
    activeShift: null as any | null,
    // Nuevo: datos del usuario autenticado
    userRole: null as string | null,
    userName: null as string | null,
    userUuid: null as string | null,
    permissions: {} as Record<string, boolean>,
});

/**
 * Inicializa el estado de auth llamando a /_auth/me
 * Esto carga el rol, nombre y permisos efectivos del servidor.
 */
export async function initAuth() {
    const token = localStorage.getItem('X-Omni-Token');
    if (!token) return;
    try {
        const res = await fetch('/_auth/me', {
            headers: { 'X-Omni-Token': token }
        });
        if (!res.ok) { appState.isLoggedIn = false; return; }
        const data = await res.json();
        appState.isLoggedIn  = true;
        appState.userRole    = data.role;
        appState.userName    = data.username;
        appState.userUuid    = data.uuid;
        appState.permissions = data.permissions ?? {};
    } catch {
        appState.isLoggedIn = false;
    }
}

// ── Helpers de permisos (usar en cualquier componente) ─────────────────────
export const can = {
    takeOrders:         () => appState.permissions['can_take_orders']          ?? false,
    sendToKitchen:      () => appState.permissions['can_send_to_kitchen']       ?? false,
    charge:             () => appState.permissions['can_charge']                ?? false,
    manageKitchenStatus:() => appState.permissions['can_manage_kitchen_status'] ?? false,
    viewOrders:         () => appState.permissions['can_view_orders']           ?? false,
    manageTables:       () => appState.permissions['can_manage_tables']         ?? false,
    viewKitchen:        () => appState.permissions['can_view_kitchen']          ?? false,
    manageMenu:         () => appState.permissions['can_manage_menu']           ?? false,
    manageInventory:    () => appState.permissions['can_manage_inventory']      ?? false,
    manageUsers:        () => appState.permissions['can_manage_users']          ?? false,
    manageShifts:       () => appState.permissions['can_manage_shifts']         ?? false,
    viewReports:        () => appState.permissions['can_view_reports']          ?? false,
};
```

---

### FASE 4 — Layout y Navegación por Permisos

#### [MODIFY] `bs_frontend/src/routes/(app)/+layout.svelte`

```typescript
// En onMount, después de checkActiveShift:
await initAuth();  // carga permisos reales desde /_auth/me
```

Actualizar `navLinks` para ser dinámico:
```typescript
// Navlinks condicionados — computado reactivamente
let navLinks = $derived([
    can.takeOrders()    && { name: 'POS',        href: '/' },
    can.manageTables()  && { name: 'Mesas',       href: '/tables' },
    can.viewOrders()    && { name: 'Órdenes',     href: '/orders' },
    can.viewKitchen()   && { name: 'Cocina',      href: '/kitchen' },
    can.manageMenu()    && { name: 'Menú',        href: '/menu' },
    can.manageInventory() && { name: 'Inventario', href: '/admin/inventory/ingredients' },
    can.manageShifts()  && { name: 'Caja',        href: '/admin/corte' },
].filter(Boolean));
```

Mostrar nombre real del usuario en el avatar dropdown:
```svelte
<span class="font-black text-lg">{appState.userName ?? 'Usuario'}</span>
<span class="text-xs opacity-50 uppercase tracking-widest">{appState.userRole}</span>
```

---

### FASE 5 — Órdenes Híbridas con Permisos

#### [MODIFY] `bs_frontend/src/routes/(app)/orders/+page.svelte`

```typescript
import { can, appState } from '$lib/app_state.svelte';
```

Re-agregar `handleItemAdvance` y proteger con `can.manageKitchenStatus()`:

```svelte
{#if can.manageKitchenStatus() && !isFinished && (item.status === 'PENDING' || item.status === 'PREPARING')}
    <button
        class="btn btn-xs rounded-full px-2 h-5 min-h-0 {item.status === 'PENDING' ? 'btn-warning btn-outline' : 'btn-primary'}"
        onclick={() => handleItemAdvance(order, item)}
        id="advance-item-{item.id}"
    >
        {item.status === 'PENDING' ? '▶' : '✓'}
    </button>
{/if}
```

Ocultar botón "Cobrar" si no tiene permiso:
```svelte
{#if can.charge() && (order.status === 'READY' || ...)}
    <!-- Botones de cobro -->
{/if}
```

---

### FASE 6 — Panel de Gestión de Permisos (Admin)

#### [NEW] `bs_frontend/src/routes/(app)/admin/users/+page.svelte`

Vista de administración de usuarios con toggles de permisos:

- Lista de usuarios con nombre, rol y badge de estado
- Al expandir un usuario: panel de permisos con toggles (checkboxes o `<input type="checkbox">`)
- Cada toggle llama a `PATCH /_auth/users/{uuid}/permissions` con `{ [permiso]: true/false }`
- Los permisos que coinciden con el preset del rol se muestran en gris ("por defecto del rol"); los overrides se resaltan en azul

---

### FASE 7 — `recipe_markdown` en Productos

#### [MODIFY] `pos_core/inventory/models.py`

Agregar a `ProductBase`:
```python
recipe_markdown: Optional[str] = Field(
    default=None,
    description="Instrucciones de preparación en formato Markdown"
)
```

#### [NEW] `scripts/migrate_add_recipe.py`

```python
import sqlite3, os
db_path = os.path.join(os.path.dirname(__file__), '..', 'pos_database.db')
conn = sqlite3.connect(db_path)
try:
    conn.execute("ALTER TABLE product ADD COLUMN recipe_markdown TEXT")
    conn.commit()
    print("✅ Columna recipe_markdown añadida.")
except sqlite3.OperationalError as e:
    print(f"ℹ️  {e}")
finally:
    conn.close()
```

#### [MODIFY] `pos_core/sales/service.py`

En `format_order_json()`:
```python
"product": {
    "id": item.product.id,
    "name": item.product.name,
    "recipe_markdown": item.product.recipe_markdown,
} if item.product else None,
```

#### [MODIFY] `bs_frontend/src/routes/(app)/kitchen/+page.svelte`

Instalar dependencia:
```bash
cd bs_frontend && npm install marked
```

Agregar modal y botón `📖 Receta` en cada ítem de cocina (solo si `item.product.recipe_markdown` existe).

#### [MODIFY] `bs_frontend/src/routes/(app)/menu/+page.svelte`

Editor Markdown split-view con preview en tiempo real para el campo `recipe_markdown`.

---

## Orden de Ejecución

```
FASE 1: roles.py + constantes de permisos               ~20 min
FASE 2: omni_auth /me extendido + endpoint permisos      ~40 min
FASE 3: app_state con permisos + helper can.*            ~30 min
FASE 4: Layout dinámico por permisos                     ~30 min
FASE 5: Órdenes híbridas protegidas por can.*            ~20 min
FASE 6: Panel admin de usuarios/permisos                 ~60 min
FASE 7A: Migración SQLite + models.py + service.py       ~15 min
FASE 7B: Modal de receta en Cocina                       ~30 min
FASE 7C: Editor Markdown en Menú                         ~45 min
─────────────────────────────────────────────────────────────────
Total estimado:                                         ~4h 50min
```

---

## Archivos a Crear / Modificar

| Archivo | Cambio |
|---|---|
| `pos_core/roles.py` | **NUEVO** — constantes de roles, presets, `resolve_permissions()` |
| `omni_auth/api.py` | **MODIFICAR** — `/me` extendido, `PATCH /users/{uuid}/permissions` |
| `omni_auth/database.py` | **MODIFICAR** — `update_user_metadata()` |
| `pos_core/inventory/models.py` | **MODIFICAR** — campo `recipe_markdown` |
| `pos_core/sales/service.py` | **MODIFICAR** — serializar `recipe_markdown` |
| `scripts/migrate_add_recipe.py` | **NUEVO** — migración SQLite |
| `bs_frontend/src/lib/app_state.svelte.ts` | **MODIFICAR** — permisos, `initAuth()`, `can.*` |
| `bs_frontend/src/routes/(app)/+layout.svelte` | **MODIFICAR** — `initAuth()`, nav dinámico, username real |
| `bs_frontend/src/routes/(app)/orders/+page.svelte` | **MODIFICAR** — botones condicionados a `can.*` |
| `bs_frontend/src/routes/(app)/kitchen/+page.svelte` | **MODIFICAR** — botón 📖 + modal receta |
| `bs_frontend/src/routes/(app)/menu/+page.svelte` | **MODIFICAR** — editor Markdown con preview |
| `bs_frontend/src/routes/(app)/admin/users/+page.svelte` | **NUEVO** — panel de gestión de usuarios + permisos |
| `bs_frontend/package.json` | **MODIFICAR** — agregar `marked` |
