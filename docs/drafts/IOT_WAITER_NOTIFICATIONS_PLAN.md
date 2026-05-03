# Plan de Enrutamiento de Notificaciones: TablePad a Mesero

**Estado:** Borrador de Arquitectura (Backend & Frontend)
**Versión:** 1.0.0

Este plan detalla cómo procesar las interacciones críticas del comensal desde el ESP32 ("Llamar Mesero" / "Pedir Cuenta") para que lleguen directa y exclusivamente al mesero responsable de la mesa.

---

## 1. El Concepto y Flujo de Interacción

Cuando el comensal pulsa una acción en el TablePad, no queremos que todos los dispositivos del restaurante suenen. Queremos un enrutamiento inteligente:

1.  **Emisión (TablePad):** El dispositivo envía `{"action": "call_waiter"}` vía WebSocket.
2.  **Enrutamiento (Backend):** El servidor POS identifica a qué mesa pertenece ese dispositivo, busca si hay una orden activa y **quién es el mesero (`user_id`)** que la abrió o la está atendiendo.
3.  **Entrega (Frontend SvelteKit):** El servidor emite un evento WebSocket dirigido específicamente a la sesión/dispositivo del mesero responsable.
4.  **Confirmación (Acción UI):** La mesa afectada en la vista del mesero empieza a parpadear o muestra una alerta llamativa. El mesero toca la advertencia para "marcar como atendida", se envía una señal (ACK) al servidor y la alerta desaparece.

---

## 2. Requerimientos de Backend (Python/FastAPI)

### A. Modificación del Router IoT (`pos_core/iot/router.py`)
Actualmente los comandos como `call_waiter` y `request_bill` envían broadcasts genéricos.
*   **Cambio a realizar:** Al recibir la acción, consultar la base de datos para obtener la orden activa de `table_id`.
*   Extraer `order.user_id` (el mesero creador).

### B. Eventos Dirigidos (Targeted Events)
*   **Broadcaster Mejorado:** Actualmente usamos canales globales (ej. `dashboard_stats`). Necesitamos introducir canales privados para usuarios (ej. `user_events_15` donde 15 es el ID del mesero) o emitir payloads que incluyan `"target_user_id": X` que el frontend sepa filtrar.
*   **Estados de Servicio (Notificación Persistente):** Idealmente, el aviso no debe ser solo visual efímero, sino registrarse en la BD (ej. en una tabla ligera de "Asistencias" o en un campo metadata de la Tabla/Orden) por si el mesero recarga la página.

---

## 3. Requerimientos de Frontend (SvelteKit)

### A. Interfaz del Map de Mesas / Tablero
*   **Estado Visual Reactivo:** Las mesas tendrán estados UI adicionales: `needs_waiter` (Amarillo parpadeante) y `needs_bill` (Azul parpadeante).
*   **Recepción de WebSocket:** El listener global del mesero escuchará eventos `waiter_called` o `bill_requested`. Si el `target_user_id` coincide con el suyo (o es Admin), la UI de la mesa entra en estado de alerta.

### B. Funcionalidad de Acknowledge (Acuse de Recibo)
*   **Interacción UI:** Al tocar la mesa parpadeante, aparecerá un tooltip o botón rápido: "Marcar como Atendido".
*   **Llamada al API:** Al pulsarlo, hace POST/WebSocket notificando que la solicitud de asistencia fue resuelta.
*   **Side-effect:** Detiene el parpadeo localmente y emite evento para que, si el mesero tiene otras tablets abiertas, también se limpie la alerta.

---

## 4. Fases de Implementación Sugeridas

1.  **Fase 1: Enrutamiento Lógico (Backend)**
    *   Modificar `pos_core/iot/router.py` para obtener el mesero asignado.
    *   Ajustar el payload del evento WS para incluir `{"target_user_id": 5, "type": "call_waiter", "table_id": 3}`.
2.  **Fase 2: Alertas Reactivas (Frontend)**
    *   Crear los efectos de parpadeo (CSS pulse animations) en los componentes de la mesa.
    *   Hacer que el frontend escuche los nuevos eventos enruteados.
3.  **Fase 3: Flujo de Acknowledge**
    *   Crear un endpoint para limpiar el estado de alerta.
    *   Conectar el toque de la mesa al cerrado de la notificación.
    *   (Opcional) Hacer que el TablePad muestre un "Mesero avisado" en lugar de solo desaparecer.

---
> [!NOTE]
> **Casos Excepcionales:** ¿Qué pasa si una mesa necesita ayuda pero no hay ninguna orden activa (acaban de sentarse)?
> *Decisión Táctica:* Si no hay un mesero activo asignado, la advertencia deberá enrutarse a un canal global de **"Todos los Meseros"**. Así, cualquier mesero disponible podrá ver el parpadeo de la mesa, acercarse a tomar la orden inicial, y al hacerlo pasará a ser el mesero responsable de futuras alertas.
