# Especificaci\xc3\xb3n de Protocolo Nativo: TablePad SDK
**Versi\xc3\xb3n:** 2.0.1 (Premium)
**Estado:** Single Source of Truth

Este documento define el esquema exacto de los objetos JSON que deben viajar por el WebSocket. 

---

## 1. Estructura de Mensajes Entrantes (POS \xe2\x86\x92 TablePad)

### A. Nueva Orden (`order_new`)
Crea una tarjeta de pedido en la pantalla del comensal.

```json
{
  "event": "order_new",
  "data": {
    "order_id": 2048,
    "table_id": 4,
    "status": "EN COLA",
    "progress": 0,
    "items": [
      {
        "name": "Pizza Pepperoni",
        "qty": 1,
        "mod": false
      },
      {
        "name": "Coca Cola",
        "qty": 2,
        "mod": true,
        "notes": "Con mucho hielo"
      }
    ]
  }
}
```

#### Detalle de Campos:
- `items`: Array de objetos. Cada objeto **DEBE** tener `name` (string) y `qty` (int). 
- `mod`: Boolean. Si es `true`, el terminal marcar\xc3\xa1 el item con un indicador visual de "Personalizado".
- `notes`: String opcional para instrucciones especiales.

---

### B. Actualizaci\xc3\xb3n de Estado (`order_update`)
Dispara la animaci\xc3\xb3n de color y la barra de progreso.

```json
{
  "event": "order_update",
  "data": {
    "order_id": 2048,
    "status": "LISTO",
    "progress": 100
  }
}
```
*Estados válidos:* `EN COLA` (Amarillo), `PREPARANDO` (Azul), `LISTO` (Verde), `ENTREGADO` (Rosa).

---

### D. Mensaje Genérico (`msg`)
Para notificaciones breves o alertas al sistema.

```json
{
  "event": "msg",
  "data": {
    "message": "Mesero en camino",
    "eta": 2
  }
}
```
*   `eta`: Minutos estimados opcionales.

---

### C. Gesti\xc3\xb3n de Sistema (`system`)
Eventos administrativos y de red.

**1. Ping/Pong (Keep-Alive)**
```json
{ "event": "pong" }
```

**2. Error de Autenticaci\xc3\xb3n (`auth_error`)**
Si el token enviado por el TablePad es inv\xc3\xa1lido, el POS env\xc3\xada:
```json
{
  "event": "system_error",
  "data": {
    "code": "AUTH_FAILED",
    "message": "Token de terminal inv\xc3\xa1lido o expirado"
  }
}
```

---

## 2. Estructura de Mensajes Salientes (TablePad \xe2\x86\x92 POS)

### A. Acciones del Cliente (`action`)
Se env\xc3\xadan cuando el usuario interact\xc3\xbaa con el TablePad.

```json
{
  "action": "call_waiter", "payload": "mesa_4"
}
```
```json
{
  "action": "request_bill", "payload": "mesa_4"
}
```

### B. Sincronización de Estado (`sync_orders`)
Solicita al servidor todas las órdenes activas de la mesa. Útil tras una reconexión.

```json
{
  "action": "sync_orders"
}
```
*Respuesta:* El servidor enviará múltiples eventos `order_new` (uno por cada orden activa).

### C. Reporte de Estado (`heartbeat`)
El dispositivo reporta su salud cada 5 minutos (ajustable).

```json
{
  "action": "heartbeat",
  "data": {
    "uptime": 12000,
    "rssi": -45,
    "free_heap": 240000
  }
}
```

---

> [!IMPORTANT]
> **Extensibilidad**: El terminal ignorar\xc3\xa1 cualquier clave JSON que no reconozca. Esto permite que el POS env\xc3\xade metadatos adicionales sin romper la interfaz del TablePad.

> [!CAUTION]
> **Orden de Mensajes**: El TablePad asume que el `order_id` es \xc3\xbanico por sesi\xc3\xb3n. Si el POS recicla IDs de orden muy r\xc3\xa1pido, podr\xc3\xadan ocurrir colisiones visuales.
