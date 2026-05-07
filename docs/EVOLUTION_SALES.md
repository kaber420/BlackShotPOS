# Evolución de Módulo: Ventas (Event-Driven)

## 1. Responsabilidad Reducida (Single Responsibility)
El módulo de Ventas se enfocará únicamente en gestionar el ciclo de vida de la orden y los pagos. Ya no será el orquestador que "limpia mesas" o "descuenta stock" manualmente.

## 2. Emisión de Eventos
Cada acción exitosa en ventas ahora emitirá un evento al `InternalEventBus`:

- **Crear Orden**: Emite `sales.order_created`.
- **Registrar Pago**: Emite `sales.payment_received`.
- **Finalizar Servicio**: Si el usuario lo indica, emite `table.vacate_requested`.
- **Cambiar Estado (KDS)**: Emite `sales.order_status_changed`.

## 3. Beneficios
- **Código Limpio**: Se eliminan las importaciones de `inventory_service`, `table_service` y `shift_service`.
- **Velocidad**: Las peticiones de venta responden más rápido al delegar los efectos secundarios a otros módulos de forma asíncrona.
- **Auditoría**: Cada evento emitido puede ser capturado automáticamente por el sistema de logs.
