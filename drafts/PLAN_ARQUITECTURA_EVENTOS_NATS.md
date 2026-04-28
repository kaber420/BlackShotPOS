# 🚀 Plan: Arquitectura Distribuidora de Eventos (NATS + JetStream)

Este documento define la transición de una comunicación REST directa a un modelo de mensajería asíncrona y resiliente, optimizado para sucursales con conectividad intermitente (Offline-First).

---

## 🏗️ 1. Infraestructura: El Sistema Nervioso Central

Utilizaremos **NATS Server** con la funcionalidad de **JetStream** activada.

*   **Despliegue**: Contenedor Docker en el servidor central (donde vive el SaaS).
*   **Protocolo**: Binario sobre TCP (puerto 4222).
*   **Seguridad**: Autenticación vía Tokens o Usuarios/Contraseñas por sucursal + Encriptación TLS.

---

## 📦 2. Lado Sucursal (POS): Resiliencia Local

Para garantizar que ninguna venta se pierda, implementaremos el **Outbox Pattern**.

### A. Tabla `SyncQueue` (SQLite)
Cada cambio importante (venta, gasto, auditoría) genera una entrada aquí:
| Campo | Tipo | Descripción |
| :--- | :--- | :--- |
| `id` | UUID | Identificador único del evento. |
| `topic` | String | Ejemplo: `sales.new`, `inventory.low`. |
| `payload` | JSON | Los datos del objeto a sincronizar. |
| `status` | Enum | `pending`, `processing`, `synced`, `failed`. |
| `attempts` | Integer | Contador de reintentos. |

### B. NATS Agent (Background Worker)
Un proceso asíncrono en la sucursal que realiza tres tareas:
1.  **Drain Queue**: Lee `SyncQueue`, publica en NATS y marca como `synced`.
2.  **Command Listener**: Escucha en `branch.[ID].commands` para recibir actualizaciones (ej: "Actualizar Precios").
3.  **Heartbeat**: Envía un "ping" cada 30-60 segundos con el estado de salud del sistema.

---

## 🌐 3. Lado SaaS (Control): Gestión Global

El Panel Central deja de ser un servidor pasivo para ser un **consumidor de eventos**.

### A. Dashboard en Tiempo Real
El backend del SaaS se suscribe a `branches.*.sales.new`. Cada vez que una sucursal vende, el dashboard se actualiza instantáneamente vía SSE o WebSockets internos del SaaS.

### B. Persistencia con JetStream (Acknowledge)
Cuando el SaaS envía una configuración (ej: "Menú de Verano"), lo publica en un **Stream persistente**.
*   Si la sucursal está desconectada, NATS guarda el mensaje.
*   En cuanto la sucursal vuelve, "consume" el mensaje y actualiza su DB local.
*   El SaaS recibe una confirmación (ACK) de que la sucursal ya aplicó el cambio.

---

## 🛠️ 4. Tecnologías Recomendadas (Stack Python)

*   **Broker**: [NATS Server](https://nats.io/) (Docker).
*   **Cliente Python**: [`nats-py`](https://github.com/nats-io/nats.py) (Asíncrono y ultra-rápido).
*   **Serialización**: JSON (estándar) o MessagePack (si se busca extrema eficiencia).

---

## 📅 5. Roadmap de Implementación

1.  **Fase 1**: Crear la tabla `SyncQueue` y la lógica de encolado en `pos_core`.
2.  **Fase 2**: Implementar el `NATS Agent` básico para envío de "Pings" y estado de salud.
3.  **Fase 3**: Migrar el flujo de ventas para que use la cola de sincronización.
4.  **Fase 4**: Refactorizar `saas_core/manager.py` para que envíe comandos vía NATS en lugar de REST.
5.  **Fase 5**: Dashboard de analíticas globales alimentado por el flujo de eventos en vivo.

---

## 🛡️ 6. Ventajas sobre el modelo actual

1.  **Adiós a los WAF/Firewalls**: No necesitas abrir puertos en los locales. La conexión es saliente.
2.  **Escalabilidad**: Un solo servidor NATS puede gestionar miles de conexiones con una fracción de la RAM que usarían WebSockets.
3.  **Integridad**: El Outbox Pattern asegura que si el POS guardó la venta, tarde o temprano llegará a la nube.
