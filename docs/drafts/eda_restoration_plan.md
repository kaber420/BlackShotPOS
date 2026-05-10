# Plan Maestro de Restauración Técnica: Arquitectura EDA (Ventas <-> Cocina)

Este documento detalla la estrategia técnica para corregir la ruptura del flujo operativo entre el módulo de Ventas y el Kitchen Display System (KDS). El objetivo es alcanzar un estado de **Desacoplamiento Puro** donde el sistema sea resiliente, reactivo y libre de dependencias circulares.

---

## 1. Diagnóstico Técnico del Estado de Falla

Actualmente, el sistema sufre de un "Silencio de Eventos". Aunque el servidor arranca, la cadena de ejecución se rompe en uno de estos tres puntos:
1. **Emisión Fallida**: `order_item_service` emite el evento pero el `InternalEventBus` no lo propaga por falta de registro del listener.
2. **Procesamiento Ciego**: El listener `on_items_added` recibe el evento pero falla silenciosamente al intentar crear tickets para productos sin un `production_area_id` explícito en BD.
3. **Falta de Notificación UI**: Los tickets se crean en BD pero el canal de WebSocket `kitchen_orders` no recibe la señal de `trigger_broadcast`.

---

## 2. Fase 1: Blindaje del Motor de Eventos y Registro

Para que la arquitectura EDA funcione, los listeners deben estar "vivos" antes de que caiga la primera orden.

### Acciones:
- **Verificación de Carga de Módulos**: Asegurar que `main.py` importe `pos_core.kitchen.listeners` de forma explícita para que los decoradores `@event_handler` se ejecuten y registren en el bus.
- **Auditoría de Payloads**: Implementar un middleware de logging en `pos_core/events/service.py` que imprima cada evento emitido y cuántos suscriptores lo han recibido. Esto nos permitirá ver en tiempo real si `sales.items_added` está llegando a Cocina.

---

## 3. Fase 2: Restauración de la Lógica de Cocina (KDS)

El corazón del fallo está en cómo Cocina interpreta lo que viene de Ventas sin tener relaciones ORM.

### Cambios en `pos_core/kitchen/services.py`:
- **Inyección de Dependencia de Sesión**: Asegurar que `create_tickets_for_order` use una sesión fresca y maneje sus propios commits para evitar colisiones con la transacción de Ventas.
- **Lógica de Ruteo Tolerante**:
  - Si un producto no tiene `production_area_id`, se consultará el área de su categoría padre.
  - Si aún así no hay área, se registrará un `WARNING` en lugar de abortar silenciosamente, facilitando el debugging.
- **Garantía de Real-time**: Insertar `await trigger_broadcast("kitchen_orders", db=session)` inmediatamente después de `session.commit()` al crear tickets.

### Cambios en `pos_core/kitchen/listeners.py`:
- **Desempaquetado Seguro**: Corregir definitivamente el conflicto de `order_id` filtrando el diccionario `payload` antes de pasarlo a los servicios de cocina.
- **Contexto de Ejecución**: Envolver las llamadas en bloques `try...except` que capturen errores de base de datos para evitar que un evento mal formado "mate" el hilo del Event Bus.

---

## 4. Fase 3: El Ciclo de Retroalimentación (Ventas <-> Cocina)

Garantizar que la pantalla de Ventas vea el progreso de la Cocina.

### Acciones:
1. **Eventos de Estado de Ticket**: Cuando un ticket cambia a `PREPARING` o `READY`, Cocina DEBE emitir eventos (`kitchen.ticket_updated`).
2. **Listener en Ventas**: Implementar (o restaurar) un listener en el dominio de Ventas que escuche estos cambios y actualice el `status` de los `OrderItems` correspondientes.
3. **Notificación Dual**: Cada cambio en Cocina debe disparar:
   - `trigger_broadcast("kitchen_orders")` -> Para el KDS.
   - `trigger_broadcast("recent_orders")` -> Para que el mesero vea que su orden ya está lista.

---

## 5. Fase 4: Verificación y Validación de Datos

Antes de entregar, realizaremos estas pruebas de estrés técnico:

1. **Prueba de Consistencia de Modelos**:
   - Ejecutar script que valide que NO existen importaciones de `pos_core.accounting` dentro de `pos_core.sales` y viceversa.
2. **Prueba de Flujo Completo (Simulation Script)**:
   - Crear una orden vía SQL puro.
   - Simular la emisión del evento `sales.items_added`.
   - Verificar que aparezcan filas en la tabla `kitchenticket`.
   - Verificar que el contador de mensajes en el WebSocket aumente.

---

## 6. Fases de Ejecución Cronológica

1. **Fase A (Inmediata)**: Reparar el registro de listeners y el ruteo de áreas de producción en `kitchen/services.py`.
2. **Fase B (Estabilidad)**: Implementar el sistema de logs de eventos para confirmar que la comunicación fluye.
3. **Fase C (Sincronización)**: Restaurar los broadcasts cruzados para que ambas pantallas (Ventas y KDS) se actualicen al unísono.
4. **Fase D (Cierre)**: Limpieza de código muerto y verificación final de desacoplamiento.

---

## Preguntas Abiertas para el Usuario
- ¿Existen productos en tu base de datos actual que NO tengan asignada un Área de Producción ni una Categoría con Área? Si es así, ¿deberían mostrarse en algún "Área General" o simplemente ignorarse?
- ¿Deseas que los estados `PREPARING` y `READY` de Cocina se reflejen visualmente en la lista de "Órdenes Recientes" de los meseros de inmediato?
