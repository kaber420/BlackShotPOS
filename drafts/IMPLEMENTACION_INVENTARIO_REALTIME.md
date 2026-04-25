# Plan de Implementación: Inventario Real-Time

Este documento detalla los pasos para convertir el panel de inventario actual (que depende de refrescos manuales y actualizaciones de estado local) en un sistema reactivo y sincronizado en tiempo real a través de WebSockets.

## 1. Backend: Tópico de Inventario

Actualmente, el `pos_broadcaster` centralizado no tiene conocimiento del inventario.

### 1.1. Modificación en `pos_core/events/service.py`
- Añadir el tópico `"inventory"` a la lógica de `_fetch_topic_data`.
- Implementar la recuperación de datos: devolver la lista completa de ingredientes serializada con Pydantic (`IngredientRead`).

### 1.2. Disparadores (Triggers) de Broadcast
Es necesario invocar `trigger_broadcast("inventory")` en los siguientes puntos críticos:
- **`inventory/service.py`**: Al final de `update_ingredient`, `create_ingredient` y `delete_ingredient`.
- **`inventory/service.py`**: Al final de `process_inventory_depletion` (cuando se descuenta stock por ventas).
- **`inventory/service.py`**: Al final de `update_ingredient_stock` (entradas de mercancía).

## 2. Frontend: Sincronización Reactiva

### 2.1. Gestión del Socket (`pos_socket.svelte.ts`)
- Añadir una propiedad `$state` llamada `ingredients` (o similar) en el `PosSocketManager` para almacenar el snapshot global del inventario.
- Añadir el `case 'inventory'` en el handler de mensajes para actualizar este estado.

### 2.2. Componente de Ingredientes (`ingredients/+page.svelte`)
- **Suscripción**: En el `onMount`, suscribirse al tópico: `posSocket.subscribe('inventory')`.
- **Reactividad**: Reemplazar (o complementar) la carga inicial manual por una referencia reactiva a `posSocket.ingredients`.
- **Acciones Locales**: Mantener las actualizaciones optimistas (actualizar la UI antes de recibir el mensaje del socket) para mantener la sensación de "snappiness" que el usuario ya aprecia.

## 3. Beneficios Esperados
- **Visibilidad Multi-Terminal**: Si un cajero cobra una orden, el administrador verá bajar el stock de granos de café instantáneamente en su oficina.
- **Auditoría en Vivo**: Cualquier ajuste manual de stock se reflejará en todas las terminales conectadas.
- **Robustez**: Elimina la inconsistencia de datos donde el usuario cree tener stock disponible que ya fue vendido en otra terminal.

## 4. Pasos Técnicos Sugeridos (Orden de Ejecución)
1. Modificar `events/service.py` para soportar el tópico.
2. Inyectar `trigger_broadcast` en el `inventory/service.py`.
3. Actualizar el `PosSocketManager` en el frontend.
4. Conectar la vista de ingredientes al socket.
