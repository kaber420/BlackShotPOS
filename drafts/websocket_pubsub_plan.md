# Plan de Implementación: Migración a WebSockets Pub/Sub

Este plan detalla los pasos para reemplazar el esquema actual de polling (con `setInterval` y un WebSocket exclusivo de cocina de notificación global) por una arquitectura unificada de WebSockets que utilizará un patrón Publicador/Suscriptor (Pub/Sub).

## User Review Required

El cambio de Websockets alterará fundamentalmente la manera en la que la información en vivo fluye de la BD hacia las tres vistas principales del Frontend. Por favor revisa este plan que fue diseñado a la medida de tu backend (FastAPI).

## Proposed Changes

### Backend (FastAPI)
---

#### [MODIFY] [pos_core/sales/broadcaster.py](file:///home/kaber420/Documentos/proyectos/blackshot/pos_core/sales/broadcaster.py)
Reemplazar la clase `OrderBroadcaster` (basada en `asyncio.Condition`) por una clase nueva `PubSubManager`.
- Contendrá un diccionario mapeando topics a WebSockets: `active_connections: dict[str, list[WebSocket]]`.
- Disponer de métodos `connect()`, `disconnect()` y `broadcast(topic, message)` para despachar payloads JSON solamente a las conexiones interesadas.

#### [MODIFY] [pos_core/sales/router.py](file:///home/kaber420/Documentos/proyectos/blackshot/pos_core/sales/router.py)
Unificar todos los endpoints de tiempo real bajo uno genérico.
- Remplazar `@router.websocket("/ws/kitchen")` por `@router.websocket("/ws/pos")`.
- Implementar la lógica del handshake: al conectarse el cliente, el backend esperará recibir un mensaje initial tipo `{"action": "subscribe", "topic": "kitchen_orders"}` y luego usará `manager.connect(websocket, topic)`.
- Modificar los endpoints `POST /orders`, `POST /orders/{id}/items`, `PATCH /orders/{id}/status` y `POST /orders/{id}/payments`. Luego de efectuar la mutación a persistencia, los endpoints recavarán la información representativa y llamarán proactivamente `await manager.broadcast("kitchen_orders", ...)` y/o `await manager.broadcast("dashboard_stats", ...)`.

### Frontend (Svelte)
---

#### [MODIFY] [bs_frontend/src/routes/(app)/+page.svelte](file:///home/kaber420/Documentos/proyectos/blackshot/bs_frontend/src/routes/(app)/+page.svelte)
Vista principal / Tablero de Operaciones.
- Eliminar por completo la función cíclica `setInterval(loadStats, 30000)`.
- Conectar un WebSocket al montar el componente a `/ws/pos`. En el `onopen`, enviar mensaje de suscripción: `{ action: "subscribe", topic: "dashboard_stats" }`.
- Reaccionar a mensajes JSON recibidos y actualizar `preparingCount`, `readyCount` de forma limpia.

#### [MODIFY] [bs_frontend/src/routes/(app)/orders/+page.svelte](file:///home/kaber420/Documentos/proyectos/blackshot/bs_frontend/src/routes/(app)/orders/+page.svelte)
Vista de Comandas/Listado Histórico.
- Eliminar el polling actual `setInterval(loadOrders, 15000)`.
- Conectar WebSocket al montar, suscribirse al topic `recent_orders`.

#### [MODIFY] [bs_frontend/src/routes/(app)/kitchen/+page.svelte](file:///home/kaber420/Documentos/proyectos/blackshot/bs_frontend/src/routes/(app)/kitchen/+page.svelte)
Vista de Cocina (KDS).
- Cambiar URL apuntada de `/ws/kitchen` al endpoint unificado `/ws/pos`. 
- Establecer suscripción explícita `{ action: "subscribe", topic: "kitchen_orders" }`.
- Ahora recibirá directamente arrays en `onmessage` sin que él pida nada ni ocurra `router` polling indirecto.

## Open Questions

1. En el Dashboard tienes rotando un "Producto Estrella (Semana / Hoy)". Esa estadística es local del cliente calculada tras recibir todas las órdenes. Con la migración, la lógica pesada sería lo ideal que lo calcule FastAPI y solo pase un JSON pequeño, ¿estás de acuerdo en que modifiquemos la forma en la que se calcula el producto estrella para que lo mande FastAPI directamente?
2. ¿Estás listo para aprobar y que comencemos la migración?

## Verification Plan
1. Correr el backend Uvicorn y monitorear la consola, debiéndose constatar que a los minutos ya **NO existan reportes asiduos** de `INFO GET /api/v1/pos/orders`.
2. Generar órdenes desde la vista principal de POS y verificar que la de Cocina, abierta en una pestaña o PC alterna, destelle con la nueva orden **al instante**, puramente a través del marco de trabajo WebSocket Pub/Sub.
