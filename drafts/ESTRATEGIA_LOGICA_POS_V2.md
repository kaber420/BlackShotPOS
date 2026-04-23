# 🧠 Estrategia de Evolución Lógica y Flujo: Blackshot POS

Este documento detalla las recomendaciones críticas de lógica de negocio y arquitectura necesarias para transformar Blackshot POS de un MVP funcional a un sistema de grado industrial (SaaS-ready).

---

## 1. Integridad Financiera y Flexibilidad (Crítico)

### 1.1 Pagos Parciales y Gestión de Saldo
**Problema:** Actualmente la orden se marca como `is_paid=True` con un solo registro de pago, sin validar el total.
*   **Solución:** Eliminar el flag `is_paid` y sustituirlo por una propiedad calculada (o campo persistente) de `balance_due`.
*   **Impacto Técnico:**
    *   **DB:** Añadir `total_amount` a la tabla `Order` (como snapshot para evitar recalcular con precios que pueden cambiar).
    *   **Service:** `payment_service` debe permitir múltiples registros en la tabla `Payment` hasta que `sum(payments.amount) >= order.total_amount`.

### 1.2 Gestión de Impuestos (IVA/Taxes)
**Problema:** No hay desglose fiscal, lo que impide generar tickets legales.
*   **Solución:** Añadir `tax_rate` a nivel de Categoría o Producto.
*   **Impacto Técnico:**
    *   **DB:** `tax_amount` en `OrderItem` y `Order`.
    *   **Logic:** El `subtotal` debe ser `quantity * unit_price`, y el `total` debe ser `subtotal + tax_amount`.

### 1.3 Propinas (Tips)
**Problema:** Las propinas se mezclan con el ingreso o no se registran.
*   **Solución:** Campo `tip_amount` en la tabla `Payment`.
*   **Impacto Técnico:** El reporte Z (cierre de caja) debe separar `Total Ventas` de `Total Propinas` para la conciliación.

---

## 2. Resiliencia y Modo Offline (Operativo)

### 2.1 Estrategia de Sincronización "Local-First"
**Problema:** Si el internet falla en una tablet, el mesero no puede tomar pedidos.
*   **Propuesta:** Implementar un **Service Worker** en SvelteKit y usar **IndexedDB** para el carrito.
*   **Flujo:**
    1. El frontend guarda el pedido localmente con un `local_id` (UUID).
    2. Intenta enviarlo al backend.
    3. Si falla (408/503), lo marca como "Pendiente de Sincronización".
    4. Un proceso en segundo plano reintenta el envío cuando detecta conectividad.

---

## 3. Inventario Avanzado (Control de Pérdidas y Precisión)

### 3.1 Registro de Merma (Waste Management)
**Problema:** El inventario solo baja por ventas, ignorando errores o productos caducados.
*   **Solución:** Crear una tabla `InventoryAdjustment` o `WasteLog`.
*   **Impacto Técnico:**
    *   **Modelo:** `id, ingredient_id, quantity, reason (Waste, Error, Expired), actor_uuid, timestamp`.
    *   **Service:** Nueva función `record_waste()` que descuenta stock fuera del flujo de ventas.

### 3.2 Alertas de Stock Crítico
**Problema:** El usuario solo se entera de que no hay leche cuando intenta vender un latte.
*   **Solución:** Sistema de triggers en `inventory_service`. Cuando un stock baja del `minimum_stock`, emitir un evento vía WebSocket a todos los usuarios con rol `admin` o `manager`.

### 3.3 Conversiones Multi-Unidad y Medidas Personalizadas
**Problema:** Llevar el inventario en unidades base como mililitros o gramos genera números muy grandes y difíciles de leer (ej. 24,000 ml de leche de almendras). Esto complica el agregar medidas a recetas y opciones.
*   **Solución:** Implementar un sistema selector de unidades donde el usuario elige explícitamente la unidad de medida (kg, g, L, ml, oz) tanto al agregar stock como al crear recetas.
*   **Impacto Técnico:**
    *   **Backend (Base de Datos):** El inventario siempre se mantiene y descuenta en la unidad mínima o base (`ml` o `g`) para máxima precisión en las recetas.
    *   **Gestión de Inventario (Frontend):** Al agregar o consultar stock, el usuario tendrá un selector (dropdown) para elegir si está viendo/ingresando en `L`, `ml`, `kg`, `g`, o `oz`. El sistema convertirá explícitamente el valor ingresado a la unidad base antes de guardarlo.
    *   **Recetas:** Al armar una receta, el chef podrá seleccionar la unidad deseada de un dropdown (ej. `2 L`, `200 ml`, `8 oz` para vasos tipo americano) y el backend se encargará de hacer la equivalencia exacta para restar la cantidad correcta de la unidad base del inventario.

---

## 4. Flujos de Trabajo en Piso (User Experience)

### 4.1 Transferencia de Mesas
**Problema:** Imposibilidad de mover clientes de lugar sin cancelar la orden.
*   **Solución:** Función `transfer_order(order_id, new_table_id)`.
*   **Lógica:** Validar que la nueva mesa esté `Libre`, mover el `table_id` de la orden y actualizar los estados físicos de ambas mesas (Vacante -> Ocupada / Ocupada -> Vacante).

### 4.2 Control de Tiempos (Hold & Fire)
**Problema:** Todo lo que se pide se envía a cocina de inmediato.
*   **Solución:** Estado `ON_HOLD` para ítems de la orden.
*   **Flujo:** El mesero marca la comida como `HOLD`. Cocina no la ve o la ve en gris. Cuando el cliente termina la entrada, el mesero pulsa "FIRE" y el estado cambia a `PENDING` para cocina.

---

## 5. Arquitectura SaaS (Escalabilidad)

### 5.1 Aislamiento de Cuentas (Multi-tenancy)
**Problema:** Actualmente todos los datos viven en un "mismo saco".
*   **Propuesta:** Añadir `account_id` (o `org_id`) a cada tabla principal.
*   **Impacto:** Es una cambio estructural masivo pero necesario. 
    *   Cada query debe incluir un `.where(model.account_id == current_account)`.
    *   Uso de `Middleware` en FastAPI para extraer el `account_id` del token JWT (Kinde) e inyectarlo en el contexto de la base de datos.

---

## 📝 Priorización Sugerida

| Prioridad | Tarea | Razón |
| :--- | :--- | :--- |
| **P0** | **Lógica de Saldo (Partial Payments)** | Es vital para la integridad del dinero y reportes de caja. |
| **P1** | **Registro de Merma** | Sin esto, el módulo de inventario es una simulación, no una herramienta real. |
| **P1** | **Transferencia de Mesas** | Es la funcionalidad más solicitada por meseros en operación real. |
| **P2** | **Impuestos y Propinas** | Necesario para la formalización del negocio (Tickets). |
| **P3** | **Modo Offline** | Complejidad técnica alta, se puede posponer hasta tener una beta estable. |
| **P4** | **Multi-tenancy** | implementarlo después será 10x más difícil, pero no se tiene pensado implementar, esto es una herramienta para restaurantes y cafeterías, no una plataforma de SaaS. |
