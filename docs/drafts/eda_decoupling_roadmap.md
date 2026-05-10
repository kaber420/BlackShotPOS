# Roadmap: Desacoplamiento Total BlackShot (EDA)

Este documento define la estrategia para eliminar las dependencias cruzadas entre Ventas, Cocina e Inventario, siguiendo el principio de **Responsabilidad Única**.

## 1. Visión General: "Ventas solo hace Ventas"

Actualmente, el módulo de Ventas actúa como un "Cerebro" que intenta orquestar la cocina y el inventario. El objetivo es que cada módulo sea autónomo y reaccione a eventos.

### Responsabilidades por Dominio

| Dominio | Responsabilidad | Eventos que emite |
| :--- | :--- | :--- |
| **Ventas** | Gestión de la cuenta, precios, impuestos y pagos. | `sales.order_created`, `sales.payment_received`, `sales.order_cancelled` |
| **Cocina** | Preparación, tiempos, comandas e impresoras térmicas. | `kitchen.item_preparing`, `kitchen.item_ready` |
| **Inventario** | Control de existencias, recetas e insumos. | `inventory.stock_low`, `inventory.depleted` |

---

## 2. Estado de la Refactorización

### [COMPLETADO] Fase 1: Limpieza de API
- [x] Eliminar parámetros de cocina (`cook_uuid`, etc.) del Router de Ventas.
- [x] Restringir estados operativos en Ventas (bloqueo de `PREPARING` y `READY` vía API de Ventas).
- [x] Estandarizar auditoría mediante `actor_uuid`.

### [COMPLETADO] Fase 2: Desacoplamiento de Lógica (Cerebro vs Músculo)
- [x] **Eliminar Inventario de Ventas**: Quitar llamadas a `process_inventory_depletion` desde `order_item_service.py`.
- [x] **Cocina como Disparador**: Asegurar que `KitchenTicket` sea quien dispare el evento de inicio de producción.
- [x] **Inventario Reactivo**: Crear listener en Inventario que escuche a Cocina para descontar stock.

### [EN PROCESO] Fase 3: Limpieza y Consolidación de Analytics
- [ ] **Migrar Analytics**: Actualizar reportes para usar `KitchenTicket` en lugar de campos de Ventas.
- [ ] **Eliminar Campos Deprecados**: Borrar `cook_uuid`, `ready_at`, etc., de los modelos de Ventas.
- [ ] **Refactorizar Split**: Ajustar `split_order_items` para no depender de campos de cocina heredados.

---

## 3. Flujo de Eventos Final (Ejemplo)

1.  **Mesero crea orden:**
    - Ventas emite `sales.order_created`.
2.  **Cocinero inicia preparación (vía API de Cocina):**
    - Cocina emite `kitchen.item_preparing`.
    - **Inventario (Listener)**: Escucha el evento y descuenta insumos de la receta.
    - **Ventas (Listener)**: Escucha el evento y actualiza el estado visual del ítem a `PREPARANDO` (solo para el mesero).
3.  **Cocinero termina:**
    - Cocina emite `kitchen.item_ready`.
    - **Ventas (Listener)**: Actualiza el estado visual a `LISTO` y notifica al mesero (IoT/WS).

---

## 4. Por qué este es el camino correcto

- **Mantenibilidad**: Si cambias de impresoras térmicas, solo tocas el código de Cocina.
- **Rendimiento**: Las operaciones pesadas (como el cálculo de recetas en inventario) ocurren en segundo plano (vía listeners), no bloquean la venta.
- **Robustez**: Un error en el driver de la impresora no hará que la venta falle.
