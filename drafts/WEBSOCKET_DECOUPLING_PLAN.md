# Borrador: Desacoplamiento de WebSockets en Blackshot POS

Este documento detalla el plan para mover la lógica de comunicación en tiempo real a un módulo centralizado (`pos_core/events/`). El objetivo es eliminar dependencias circulares y mejorar la robustez de la sincronización en tiempo real.

## 1. Motivación
Actualmente, el WebSocket está acoplado al módulo de ventas (`pos_core/sales/`). Esto causa problemas de importación circular cuando otros módulos (como `tables` o `inventory`) necesitan notificar cambios. Además, un fallo en la serialización de un tópico puede afectar la estabilidad de toda la conexión.

## 2. Nueva Estructura del Módulo de Eventos

Crearemos un nuevo paquete `pos_core/events/`:

### `pos_core/events/manager.py`
Contendrá la clase `PubSubManager` (evolución de `broadcaster.py`).
- Manejo de conexiones por tópico.
- Función de `broadcast` segura con `jsonable_encoder` de FastAPI para evitar errores de serialización.

### `pos_core/events/service.py`
Contendrá la función `trigger_broadcast(topic: str)`.
- Esta función centraliza la recolección de datos frescos de la base de datos para cada tópico sustantivo (mesas, órdenes, cocina).
- Desacopla la base de datos de los routers de venta.

### `pos_core/events/router.py`
Contendrá el endpoint único `@router.websocket("/ws/pos")`.
- Implementará el handshake inicial, autenticación y gestión de suscripciones.

## 3. Pasos de la Implementación

### Fase 1: Creación del Módulo de Eventos
1.  Crear `pos_core/events/__init__.py`.
2.  Implementar `manager.py` moviendo la lógica de `broadcaster.py`.
3.  Implementar `service.py` con las funciones que recuperan el estado actual para cada tópico.
4.  Implementar `router.py` con el endpoint de WebSocket.

### Fase 2: Refactorización de Ventas
1.  Eliminar el endpoint `/ws/pos` de `pos_core/sales/router.py`.
2.  Eliminar la función `broadcast_updates` de `pos_core/sales/router.py`.
3.  Sustituir las llamadas a `asyncio.create_task(broadcast_updates())` por `asyncio.create_task(trigger_broadcast("nombre_topico"))`.
4.  Eliminar `pos_core/sales/broadcaster.py`.

### Fase 3: Integración
1.  Actualizar `main.py` para incluir el nuevo `events_router`.
2.  Verificar que los prefijos de las rutas y tags de documentación sean correctos.

## 4. Beneficios
- **Cero Dependencias Circulares**: Los módulos de negocio notifican eventos, no gestionan sockets.
- **Robustez**: La serialización segura evita que una fila de BD corrupta tire el WebSocket.
- **Mantenibilidad**: Es sencillo añadir nuevos tópicos de actualización (ej. inventario bajo).

## 5. Verificación
- Abrir múltiples pestañas del POS.
- Realizar acciones en Mesas, Cocina y Órdenes.
- Confirmar que los cambios se reflejan instantáneamente sin refrescar.
- Simular errores de serialización para confirmar que el log atrapa el error sin cerrar el socket.
