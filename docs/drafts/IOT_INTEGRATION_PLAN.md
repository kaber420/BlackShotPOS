# Borrador: Integración IoT (ESP32/ESP8266) - Ecosistema de Dispositivos (v2)

Este documento detalla el plan arquitectónico para integrar múltiples tipos de dispositivos IoT (pantallas, botones, sensores) en Blackshot. Se enfoca en una solución escalable, segura (Long-Lived Tokens) y operativa mediante permisos granulares.

## 1. Motivación y Casos de Uso
*   **Experiencia del Cliente**: Notificaciones en tiempo real del estado de la orden ("Preparando", "Listo para entrega").
*   **Eficiencia Operativa**: Reducción de la carga de los meseros; el cliente puede solicitar la cuenta o asistencia con un botón físico.
*   **Gestión Centralizada**: Monitoreo de la salud de todos los dispositivos desde el Panel Admin.

## 2. Soporte Multi-Hardware (Dual-Chip)
El sistema está diseñado para ser agnóstico al hardware mediante una capa de abstracción en el firmware:
*   **ESP8266**: Solución de bajo costo. Limitada a comunicación WiFi y configuración vía Portal Cautivo (SoftAP).
*   **ESP32**: Solución Premium. Soporta WiFi + Bluetooth Low Energy (BLE) para un provisionamiento más rápido y seguro.

## 3. Provisionamiento y Seguridad (Zero-Touch Logic)
Para evitar la codificación rígida (hardcoding) de credenciales:
1.  **Portal de Configuración (SoftAP)**: Si el dispositivo no tiene red, crea una red WiFi abierta (ej: `Blackshot-Config`). Al conectarse, una interfaz web permite ingresar el SSID, Password y el Token del Dispositivo.
2.  **Bluetooth Prov (ESP32 only)**: Configuración opcional mediante una futura App móvil.
3.  **Seguridad a Nivel de Token**: Cada dispositivo tiene un Long-Lived Token (LLT) único. El servidor rechaza cualquier conexión con tokens inválidos o revocados.

## 4. Arquitectura de Datos (IoT Management)

### Modelo de Dispositivo (`IoTDevice`)
*   `device_id`: ID único de hardware (MAC Address).
*   `chip_type`: `ESP8266` | `ESP32` | `Other`.
*   `firmware_version`: Versión actual para seguimiento de actualizaciones.
*   `table_id`: Mesa vinculada (opcional para sensores ambientales).
*   `last_seen`: Timestamp del último latido (heartbeat).
*   `status`: `online` | `offline`.
*   `metadata`: JSON con métricas dinámicas (RSSI, Batería, Temperatura, etc).

## 5. Panel de Control y Acceso Rápido
Se implementará una sección dedicada en `/admin/devices`. Sin embargo, para agilizar la operación, se habilitará un acceso directo en el **Menú del Avatar de Usuario** condicionado al permiso `can_manage_iot`.

Este panel permitirá:
*   **Inventario Vivo**: Lista de dispositivos con indicadores visuales de salud y tipo.
*   **Asignación Dinámica**: Vincular dispositivos a mesas o zonas específicas.
*   **Acciones Remotas**: Reiniciar conexión, revocar tokens o actualizar configuraciones.

## 6. Flujo de Comunicación (WebSockets)
1.  **POS -> Servidor**: Cambio de estado (Order READY).
2.  **Servidor -> IoT**: El Broadcaster identifica qué dispositivos están suscritos a la mesa de la orden y envía un payload minimalista (`{"ev": "rdy", "msg": "Café listo"}`).
3.  **IoT -> Servidor**: Latidos cada 60s con metadatos de salud y batería.

## 7. Pasos a Seguir
*   **Fase 1**: Expandir modelos de base de datos para registrar metadatos de chips.
*   **Fase 2**: Desarrollar el Panel de Administración de Dispositivos en el Frontend.
*   **Fase 3**: Crear el SDK de firmware (C++/Arduino) con soporte para Portal Cautivo y BLE.
