# Plan de Refactorización: División de Archivos Grandes (Borrador)

Este plan detalla la estrategia para dividir los archivos más extensos del proyecto Blackshot, mejorando la mantenibilidad, legibilidad y facilitando las pruebas unitarias.

## Archivos a Intervenir

1.  **Frontend**: `ProductModal.svelte` (~780 líneas)
2.  **Backend POS**: `inventory/service.py` (~600 líneas)
3.  **Backend POS**: `sales/order_service.py` (~540 líneas)
4.  **SaaS Central**: `main.py` (~340 líneas)

---

## 1. Refactorización de Frontend: `ProductModal.svelte`

El objetivo es extraer secciones lógicas en componentes independientes.

### [NEW] `bs_frontend/src/lib/components/product/`
- `ProductGeneralForm.svelte`: Manejará Nombre, Categoría, Precio Base, Stock Inicial y Descripción.
- `ProductNutritionForm.svelte`: Manejará los inputs de Proteínas, Calorías, Carbohidratos y Grasas.
- `ProductRecipeForm.svelte`: Manejará el editor de Markdown y la previsualización de instrucciones.
- `ProductVariantsManager.svelte`: Manejará la lista de tallas/variantes. Utilizará un sub-componente `VariantItem.svelte`.

### [MODIFY] `ProductModal.svelte`
- Actuará como orquestador, manteniendo el estado global del formulario (`formData`, `selectedVariants`) y comunicándose con los servicios de API.

---

## 2. Refactorización de Backend POS: `inventory/service.py`

Dividiremos este servicio monolítico en módulos dentro de un nuevo paquete.

### [NEW] `pos_core/inventory/services/`
- `category_service.py`: CRUD de categorías.
- `product_service.py`: CRUD de productos, variantes y medidas.
- `ingredient_service.py`: CRUD de ingredientes y conversión de unidades.
- `modifier_service.py`: CRUD de grupos y opciones de modificadores.
- `stock_service.py`: Lógica de depleción de inventario (anteriormente `process_inventory_depletion`).

---

## 3. Refactorización de Backend POS: `sales/order_service.py`

Actualmente `order_service.py` es un archivo de más de 540 líneas que maneja todo el ciclo de vida de una orden, los ítems, y las acciones complejas como cancelaciones y transferencias de mesa. Dividiremos sus responsabilidades en servicios más pequeños y cohesivos dentro del nuevo paquete `pos_core/sales/services/`.

### [NEW] `pos_core/sales/services/order_lifecycle_service.py`
Manejará el ciclo de vida principal (CRUD) y la actualización de estado de las órdenes.
- **Funciones a migrar**: `create_order`, `get_order_by_id`, `get_orders`, `get_kitchen_orders`, `get_order_with_relations`, `update_order_status`, `delete_order`.
- **Responsabilidad**: Gestionar el estado general de la orden e interactuar con `order_repo` para la persistencia. Coordinación básica del estado de la mesa al momento de la creación y notificación IoT.

### [NEW] `pos_core/sales/services/order_item_service.py`
Se enfocará exclusivamente en los ítems individuales de una orden.
- **Funciones a migrar**: `add_item_to_order`, `update_order_item_status`.
- **Responsabilidad**: Cálculo de precios considerando variantes y modificadores, actualización de estado para el KDS (Kitchen Display System), coordinación con el inventario para la depleción de stock, y recálculo dinámico del estado de la orden padre cuando sus ítems cambian.

### [NEW] `pos_core/sales/services/order_action_service.py`
Contendrá operaciones de negocio que implican efectos secundarios importantes (auditoría, manejo de mesas).
- **Funciones a migrar**: `cancel_order`, `cancel_order_item`, `transfer_order_table`.
- **Responsabilidad**: Ejecutar lógica de cancelación y propagarla a los ítems, coordinar la liberación u ocupación de mesas usando `table_service`, y registrar los cambios detallados en `audit_service`.

### [MODIFY] `pos_core/sales/routers/` (y otros importadores)
- Habrá que actualizar los imports en el router de ventas o cualquier otro archivo que actualmente importe desde `pos_core.sales.order_service` para que apunte a las nuevas ubicaciones en `pos_core.sales.services.*`.

---

## 4. Refactorización de SaaS Central: `main.py`

### [NEW] `saas_core/routers/`
- `dashboard.py`: Rutas `/` y `/api/stats`.
- `branches.py`: Rutas de gestión de sucursales.
- `products.py`: Rutas de catálogo global.
- `users.py`: Rutas de gestión de usuarios.
- `events.py`: Lógica de SSE (`/api/events/feed`).

---

## Plan de Verificación

### Pruebas de Integración
1.  Verificar que el POS siga permitiendo crear y editar productos con tallas y recetas.
2.  Validar que el inventario se descuente correctamente al completar una venta.
3.  Asegurar que el Panel Central del SaaS cargue todas las secciones correctamente.
