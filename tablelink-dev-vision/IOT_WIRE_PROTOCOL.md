# Protocolo de Comunicación Blackshot IoT (Wire Protocol)
**Versión:** 2.1.0 (Estabilizada)
**Estado:** Single Source of Truth para Firmware C++

Este documento describe el formato real de los mensajes JSON intercambiados entre el POS Blackshot y el hardware TablePad.

---

## 1. El Formato de "Sobre" (Envelope)
A diferencia de los eventos simples, el servidor a menudo envuelve los mensajes en capas de ruteo. El firmware **DEBE** ser capaz de desenvolver estas capas recursivamente.

### Estructura de Topic (Observada):
```json
{
  "topic": "iot_table_1",
  "data": {
    "event": "order_update",
    "data": {
      "order_id": 96,
      "status": "LISTO",
      "progress": 100
    }
  }
}
```
*Regla de Oro:* Si un objeto no tiene `event` pero tiene `data`, el parser debe entrar en `data` y re-evaluar.

---

## 2. Flujo de Handshake (Sincronización)

### 1. Conexión y Configuración (`config`)
Al conectar, el POS envía la identidad del dispositivo.
```json
{
  "event": "config",
  "data": {
    "business_name": "Blackshot Coffee",
    "table_id": 1
  }
}
```
*Nota:* `table_id` puede llegar como número (`1`) o string (`"01"`). El firmware debe convertirlo a string siempre.

### 2. Sincronización de Órdenes (`sync_orders`)
El hardware solicita el estado actual inmediatamente después del config.
**Salida (Hardware -> POS):**
```json
{ "action": "sync_orders" }
```
**Entrada (POS -> Hardware):** Puede ser un objeto único o un **Array []** de órdenes.

---

## 3. Eventos de Órdenes

### A. Nueva Orden (`order_new`)
```json
{
  "event": "order_new",
  "data": {
    "order_id": 97,
    "status": "EN COLA",
    "items": [
      { "name": "Latte", "qty": 1, "mod": false },
      { "name": "Panini", "qty": 1, "mod": true, "notes": "Sin cebolla" }
    ]
  }
}
```

### B. Actualización (`order_update`)
```json
{
  "event": "order_update",
  "data": {
    "order_id": 97,
    "status": "PREPARANDO",
    "progress": 50
  }
}
```

**Actualización de platillo individual (opcional):**
```json
{
  "event": "order_update",
  "data": {
    "order_id": 97,
    "item_index": 1,
    "status": "LISTO",
    "progress": 100
  }
}
```
- `item_index` es el índice base-0 del platillo dentro del array `items` de la `order_new` original.
- Si `item_index` **está presente** → solo ese platillo cambia de color/estado en la pantalla del comensal.
- Si `item_index` **está ausente** → todos los platillos de la orden se actualizan igual *(compatible con backends sin esta funcionalidad)*.

**Estados y Colores por platillo:**
- `EN COLA`: Amarillo `#FFCC00`
- `PREPARANDO`: Azul `#00AAFF`
- `LISTO`: Verde `#00FF88`
- `ENTREGADO`: Fuchsia/Rosa `#FF44AA` — muestra el color 4 segundos y desaparece automáticamente

---

## 4. Limpieza de Mesa

### A. Limpiar mesa completa (`clear_table`)
El POS envía este evento cuando la mesa es cobrada y desocupada. El firmware borra **todas** las órdenes de la pantalla, dejándola limpia para el próximo cliente.
```json
{ "event": "clear_table" }
```
Alias aceptado: `"table_cleared"` (ambos producen el mismo efecto).

### B. Eliminar una orden específica (`order_delivered`)
Si el POS maneja múltiples órdenes por mesa, puede eliminar solo una tarjeta:
```json
{
  "event": "order_delivered",
  "data": { "order_id": 97 }
}
```
*Nota: Este evento es diferente a `order_update` con `ENTREGADO`. `order_delivered` elimina el card inmediatamente. `order_update + ENTREGADO` muestra el color fuchsia 4 segundos y luego lo elimina automáticamente.*

---

## 5. Keep-Alive y Control

### Heartbeat (Aplicación)
El hardware envía un ping cada 25 segundos para mantener el túnel abierto en firewalls/routers.
```json
{ "action": "ping" }
```
El servidor responde con:
```json
{ "event": "pong" }
```

---

## 5. Acciones de Usuario (Botones)
Enviados cuando el comensal presiona botones en el Footer.

- **Llamar Mesero:** `{ "action": "call_waiter", "payload": "table_id" }`
- **Pedir Cuenta:** `{ "action": "request_bill", "payload": "table_id" }`

---

> [!TIP]
> **Robustez:** El firmware está diseñado para ignorar campos desconocidos. Puedes añadir metadatos en el POS (como fotos de productos o nombres de meseros) y el firmware seguirá funcionando sin cambios.
