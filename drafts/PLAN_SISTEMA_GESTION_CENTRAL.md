# 🌐 Plan: Sistema de Gestión Central (SaaS) y Multi-sucursal

Este documento define la arquitectura para el Panel Central que administrará múltiples sucursales de Blackshot POS, utilizando el **Bridge RS256** como protocolo de comunicación.

---

## 🏗️ 1. Arquitectura de Identidad: El "Virtual User"

Para que el sistema local (sucursal) pueda procesar peticiones del SaaS sin modificar toda su lógica de negocio, utilizaremos un mapeo de identidad.

### El concepto
Cuando llega una petición con el header `X-Blackshot-Bridge-Auth`, la dependencia de seguridad de la sucursal no devuelve un simple diccionario, sino un objeto **`BridgeUser`** que simula ser un usuario real.

| Propiedad | Valor / Origen | Razón |
| :--- | :--- | :--- |
| `id` | `uuid-saas-central` | ID fijo para identificar acciones del sistema central en DB. |
| `email` | `central@blackshot.app` | Aparecerá en los logs de auditoría locales. |
| `role` | `admin` | Otorga permisos totales de forma automática. |
| `is_bridge` | `True` | Flag para lógica específica (ej. ignorar límites de IP). |

### Impacto en Auditoría
Si el SaaS cambia el precio de un producto remotamente, el log de auditoría local registrará:
> *"Producto 'Espresso' modificado por central@blackshot.app via Remote Bridge"*

---

## 🔑 2. Aprovisionamiento (Enlace de Sucursales)

El proceso de añadir una sucursal al panel central debe ser seguro y sencillo:

1.  **Generación de Llaves**: El Panel Central genera un par de llaves RSA-256 específicas para la nueva sucursal (o usa una global, dependiendo de la escala).
2.  **Intercambio**: 
    *   El SaaS muestra la **Llave Pública** en formato PEM.
    *   El dueño la pega en la configuración de la sucursal local (o se inyecta via script de instalación).
3.  **Handshake**: 
    *   El SaaS envía un `PING` firmado.
    *   La sucursal valida y responde con sus metadatos (Nombre, Versión, Capacidad).
    *   Conexión establecida.

---

## 📊 3. Estrategia de Datos: Pull vs Push

### Modelo Pull (SaaS solicita)
*   **Uso**: Analíticas, Auditorías puntuales, Reportes Z.
*   **Mecánica**: El SaaS hace un fetch a la sucursal cuando el dueño abre el dashboard.
*   **Ventaja**: No requiere que la sucursal esté enviando datos constantemente, ahorrando ancho de banda.

### Modelo Push / Stream (Sucursal envía)
*   **Uso**: Monitor de ventas en vivo, alertas de stock bajo, KDS centralizado.
*   **Mecánica**:
    1.  **Handshake**: El SaaS conecta via `wss://` enviando un token firmado en los parámetros de la URL.
    2.  **Validación**: La sucursal verifica la firma y la fecha de creación (< 60s). Si es válida, eleva la conexión a WebSocket.
    3.  **Persistencia**: La conexión se mantiene abierta sin necesidad de re-firmar cada mensaje.
*   **Seguridad**: Si el socket se cierra, se requiere un **nuevo token** con timestamp actualizado para reconectar.

---

## 📡 4. Sistema de Eventos y Suscripciones (Bridge Streams)

Para no saturar la conexión de la sucursal, el SaaS utilizará un sistema de "Tópicos".

### Tópicos Disponibles
1.  `sales.live`: Notifica cada vez que una orden se marca como pagada.
2.  `inventory.alerts`: Notifica cuando un insumo baja del stock mínimo.
3.  `system.audit`: Stream de logs de acciones críticas (cancelaciones, reembolsos).
4.  `shifts.status`: Notifica aperturas y cierres de caja.

### Flujo de Suscripción
Al conectar, el SaaS puede enviar un mensaje de control:
```json
{
  "action": "subscribe",
  "topics": ["sales.live", "shifts.status"]
}
```
La sucursal filtrará sus broadcasts internos y solo enviará por el Bridge lo que el SaaS solicitó.

---

## ⚙️ 5. Gestión de Configuración Remota

El Panel Central podrá "empujar" configuraciones a las sucursales:

*   **Menús Globales**: El SaaS envía un JSON con los nuevos productos y precios. La sucursal actualiza su tabla `Product` local.
*   **Parámetros de Negocio**: Cambiar el `ticket_footer` o la tasa de impuestos de todas las sucursales con un solo click.
*   **Control de Versiones**: Forzar actualizaciones de software en las sucursales.

---

## 👥 6. Gestión de Staff y Usuarios (Sincronización)

El Panel Central permite gestionar el personal de todas las sucursales desde un solo lugar.

### Flujo de Creación de Usuario
1.  **Acción en SaaS**: El dueño crea un nuevo mesero en el Panel Central y selecciona a qué sucursales tiene acceso.
2.  **Comando Bridge**: El SaaS envía una petición `POST /api/v1/bridge/sync-user` (o similar) a cada sucursal seleccionada.
3.  **Persistencia Local**: La sucursal recibe los datos (Email, Rol, Password Hash) y los inserta en su tabla local de `users`.
4.  **Login Inmediato**: El mesero puede empezar a trabajar en la sucursal física usando las credenciales creadas en la nube.

### Control de Permisos Globales
*   **Baja Centralizada**: Si un empleado es despedido, el SaaS envía un comando de "Desactivar" a todas las sucursales. El Bridge local marca al usuario como `is_active = False` instantáneamente.
*   **Actualización de Roles**: Los cambios de rol (ej. de Mesero a Manager) se propagan desde el SaaS a las sucursales de forma atómica.

---

## 🛡️ 7. Consideraciones de Seguridad y Resiliencia

1.  **Offline-First**: La sucursal nunca debe depender del SaaS para operar. Si el SaaS se cae, la venta sigue. El Bridge es estrictamente para **gestión y monitoreo**, no para operación crítica.
2.  **Firmas por Comando**: Se recomienda que el JWT del Bridge incluya un hash del cuerpo del mensaje (`body_hash`) para evitar que alguien intercepte una petición y la modifique en el camino (aunque HTTPS ya protege esto, es una capa extra para SaaS industrial).
3.  **Rotación de Llaves**: Capacidad de invalidar la llave pública localmente si el dueño sospecha que su panel central fue comprometido.

---

## 📅 8. Roadmap Sugerido para este Plan

1.  **Fase A**: Implementar el objeto `BridgeUser` en el backend local.
2.  **Fase B**: Refactorizar routers locales para aceptar `require_staff_or_bridge`.
3.  **Fase C**: Crear el "Manager de Conexiones" en el proyecto SaaS (almacenamiento de IPs/URLs y llaves privadas).
4.  **Fase D**: Dashboard de agregación (Sumar ventas de Sucursal A + Sucursal B).
5.  **Fase E**: Implementar la sincronización bidireccional de usuarios y menús.
