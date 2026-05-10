# RFC: Desacoplamiento Final de Ventas y Mesas (EDA)

Este documento detalla la estrategia para eliminar las dependencias directas del módulo de Ventas hacia el módulo de Mesas, respetando íntegramente la lógica de negocio manual y el control del usuario sobre el estado de las mesas.

## 1. Objetivos
- **Desacoplamiento:** El módulo de Ventas no debe importar servicios ni modelos de Mesas.
- **Integridad de Negocio:** Mantener el control manual sobre la liberación de mesas. Pagar una orden **NO** libera la mesa automáticamente a menos que el usuario lo solicite.
- **Reactividad:** Utilizar el `InternalEventBus` para sincronizar los estados de las mesas basándose en intenciones del usuario.

## 2. Cambios en la Comunicación (Eventos)

### sales.payment_received (Actualización)
El payload del evento de pago incluirá el flag opcional `vacate_table`.
- Si `vacate_table` es `true`, el módulo de Mesas liberará la mesa.
- Si es `false` (por defecto), la mesa permanecerá ocupada.

### sales.order_transferred (Nuevo)
Se emitirá cuando una orden se mueva de una mesa a otra.
- **Payload:** `order_id`, `from_table_id`, `to_table_id`.
- **Reacción en Mesas:** El listener marcará la mesa origen como `Free` y la mesa destino como `Occupied`, preservando el tiempo de ocupación si es necesario.

### sales.order_cancelled / sales.order_deleted
El listener de Mesas ya captura estos eventos. Se eliminarán las llamadas redundantes en el código de Ventas.

## 3. Plan de Acción

### Fase 1: Módulo de Mesas (Listeners)
1. **[MODIFY] `pos_core/tables/listeners.py`**:
    - Agregar listener para `sales.payment_received` que verifique el flag `vacate_table`.
    - Agregar listener para `sales.order_transferred` para gestionar el cambio de estado de ambas mesas.

### Fase 2: Módulo de Ventas (Refactorización)
1. **[MODIFY] `pos_core/sales/payment_service.py`**:
    - Asegurar que el evento `sales.payment_received` pase el flag `vacate_table` (si se recibe desde el router).
2. **[MODIFY] `pos_core/sales/services/order_action_service.py`**:
    - Eliminar la importación de `pos_core.tables`.
    - En `cancel_order`, eliminar la llamada manual a `vacate_table_service`.
    - En `transfer_order_table`, eliminar la manipulación directa de modelos `Table` y emitir el evento `sales.order_transferred`.
3. **[MODIFY] `pos_core/sales/router.py`**:
    - En `pay_order`, eliminar la llamada directa a `table_service`. Pasar el flag `vacate_table` al `payment_service`.

## 4. Verificación
1. **Transferencia:** Mover una orden a otra mesa y verificar que la mesa anterior quede libre y la nueva ocupada.
2. **Pago sin Liberar:** Pagar una orden con `vacate_table=false` y verificar que la mesa siga `Occupied`.
3. **Pago con Liberación:** Pagar una orden con `vacate_table=true` y verificar que la mesa quede `Free`.
