# Diseño EDA: Subsistema de IoT (TablePads)

Este documento describe cómo el módulo de IoT se integra en la arquitectura orientada a eventos (EDA) de Blackshot.

## 1. El Rol de IoT en el Bus de Eventos

A diferencia de la UI Web (que recibe snapshots completos de datos), los dispositivos IoT son **consumidores de eventos específicos** con recursos limitados. Su lógica se basa en reaccionar a cambios puntuales en el ciclo de vida de la atención.

## 2. Matriz de Suscripciones

El módulo IoT escuchará los siguientes tópicos para coordinar la respuesta del hardware:

| Tópico | Evento | Acción en Hardware |
| :--- | :--- | :--- |
| `tables.vacated` | Mesa liberada | **Reset**: Limpia la pantalla, borra órdenes locales y detiene alertas activas. |
| `tables.status_changed` | Cambio a 'Reserved' | **Bloqueo**: Muestra mensaje de "MESA RESERVADA" y deshabilita botones de pedido. |
| `sales.order_created` | Nueva orden en mesa | **Init**: Muestra el número de orden y cambia el estado a "Enviado". |
| `kitchen.item_ready` | Platillo/Bebida lista | **Notificación**: Activa Buzzer/LED y muestra mensaje "¡Listo para recoger!". |
| `kitchen.item_preparing`| Inicio de preparación | **Feedback**: Muestra barra de progreso o mensaje "Preparando...". |
| `sales.order_cancelled` | Orden cancelada | **Alerta**: Notifica al cliente y vuelve al estado de espera. |

## 3. Flujo de Información (Ejemplo: Café Listo)

1. **Cocina**: El barista marca el ticket como "Listo".
2. **Evento**: El servicio de cocina publica `kitchen.item_ready` con `order_id` y `table_id`.
3. **IoT Listener**: Detecta el evento, busca si hay un WebSocket activo para esa `table_id`.
4. **WebSocket**: Envía el comando binario o JSON `{"event": "rdy"}` al ESP32.
5. **Hardware**: El dispositivo vibra y muestra "Café Americano LISTO".

## 4. Acciones desde el Hardware (Upstream)

Cuando el cliente interactúa con el dispositivo, el flujo es el inverso, pero siempre mediado por eventos:

1. **Botón [Mesero]**: Se envía `action: call_waiter` vía WebSocket.
2. **IoT Handler**: Publica evento interno `iot.waiter_requested`.
3. **Dashboard UI**: Un listener de la UI Web escucha `iot.waiter_requested` y hace parpadear la mesa en el mapa del administrador.

## 5. Ventajas de este Diseño

- **Desacoplamiento**: El módulo de cocina no sabe que existe un hardware IoT; solo publica que la comida está lista.
- **Eficiencia**: Solo enviamos al dispositivo lo que realmente necesita procesar.
- **Extensibilidad**: Si añadimos una App de Clientes, esta escuchará los mismos eventos que el IoT, sin cambiar una sola línea de código en el núcleo.
