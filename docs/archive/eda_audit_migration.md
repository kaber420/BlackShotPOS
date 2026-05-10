# RFC: Migración de Auditoría a Event-Driven Architecture (EDA)

Este documento detalla la estrategia para desacoplar el módulo de Auditoría del flujo transaccional principal de la aplicación, utilizando el `InternalEventBus` para capturar acciones sensibles de forma asíncrona.

## 1. Problema Actual
Actualmente, el registro de auditoría en `pos_core/audit/service.py` es **síncrono** y comparte la sesión de base de datos con la lógica de negocio (Sales, Inventory, etc.). 
- **Acoplamiento:** Los servicios de negocio deben conocer explícitamente el servicio de auditoría.
- **Riesgo de Bloqueo:** Un fallo en la escritura del log de auditoría podría revertir una transacción de venta legítima.
- **Rendimiento:** Añade latencia a la transacción principal al realizar inserciones adicionales en el mismo hilo/sesión.

## 2. Propuesta: Auditoría Reactiva
Transformar el módulo de Auditoría en un consumidor pasivo de eventos.

### Cambios en Infraestructura
- **Audit Listener:** Crear `pos_core/audit/listeners.py` que se suscriba a todos los eventos que requieran auditoría.
- **Metadata Enriquecida:** Asegurar que todos los eventos publicados en el `event_bus` incluyan en su payload o metadatos:
    - `actor_uuid` / `actor_name`
    - `reason` (en caso de cancelaciones o ajustes)
    - `target_id` y `target_type` (si no son deducibles del tópico)

### Flujo de Trabajo
1. **Suscripción:** El listener de auditoría se suscribe a tópicos como:
    - `sales.order_cancelled`
    - `sales.payment_received` (para pagos de alto monto o anulaciones)
    - `inventory.stock_adjusted`
    - `catalog.product_price_changed`
2. **Procesamiento:** El listener extrae la información del evento y utiliza una sesión de base de datos independiente (vía `async_session_maker`) para persistir el `AuditLog`.

## 3. Plan de Implementación

### Fase 1: Preparación de Eventos
- Revisar que `event_bus.publish` en todos los módulos pase el `actor_uuid`.
- Estandarizar el campo `reason` en eventos de anulación.

### Fase 2: Implementación del Listener
- **[NEW] `pos_core/audit/listeners.py`**:
    - Implementar manejadores para cada evento crítico.
    - Mapear el tópico del evento a una `AuditCategory`.

### Fase 3: Refactorización de Servicios (Limpieza)
- Eliminar las llamadas directas a `audit_service.log_action` en:
    - `pos_core/sales/services/order_action_service.py`
    - `pos_core/inventory/services/adjustment_service.py`
- Eliminar la dependencia de `session` en la auditoría si se opta por un trabajador totalmente independiente.

## 4. Verificación
- Simular una cancelación de orden.
- Verificar en los logs que el listener de auditoría se disparó.
- Validar que el registro en la tabla `auditlog` se creó correctamente con todos los datos (actor, motivo, etc.).
