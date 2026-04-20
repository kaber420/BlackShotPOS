# Borrador: Panel de Gestión de Dispositivos IoT

Este documento detalla el diseño y funcionamiento de la interfaz de gestión para dispositivos IoT (pantallas, botones, sensores) dentro del sistema Blackshot POS.

## 1. Ubicación y Acceso
Para facilitar la operación diaria, el panel tendrá dos puntos de entrada:
1.  **Panel de Administración**: `/admin/devices` para configuración global.
2.  **Menú del Avatar**: Acceso rápido en la cabecera del POS ("🔌 Gestionar Dispositivos").

### Lógica de Permisos
El sistema utilizará el permiso granular `can_manage_iot`. Esto permite que usuarios operativos (ej. encargado de piso o staff técnico) puedan re-vincular dispositivos o verificar su batería sin necesidad de ser administradores generales del sistema.

## 2. Características del Panel

### Dashboard de Salud (KPIs)
*   **Total Dispositivos**: Conteo general.
*   **Online / Offline**: Indicadores en tiempo real (vía WebSockets).
*   **Alertas Críticas**: Notificación si un dispositivo tiene batería baja o señal WiFi débil (RSSI < -80dBm).

### Lista de Dispositivos (Grid/Table)
Cada fila representará un hardware y mostrará:
*   **Nombre / Alias**: "Pantalla Mesa 5", "Sensor Refri 1".
*   **Estado**: Dot verde/rojo (Online/Offline). 
*   **Vinculación**: Mesa o área asociada.
*   **Tipo**: Badge indicando el tipo de chip o función (ESP32, Sensor Temp, etc).
*   **Última Conexión**: Tiempo relativo (ej: "hace 2 min").

### Modal de Gestión
Al hacer clic en un dispositivo, se abrirá un modal para:
*   **Renombrar**: Cambiar el alias del hardware.
*   **Re-Vincular**: Cambiar la `table_id` asociada mediante un dropdown.
*   **Seguridad**: Botón para "Invalidar Token" (genera uno nuevo y desconecta el actual).
*   **Ver Metadatos**: Datos técnicos (Versión de Firmware, Dirección MAC, Tiempo de actividad).

## 3. Flujo de Configuración (Provisionamiento)
El panel incluirá una herramienta para registrar nuevos dispositivos:
1.  **Generar Token**: Crea una nueva entrada en la BD y muestra el token de larga duración (LLT).
2.  **QR de Configuración**: Opcional. Genera un QR que el staff puede escanear (o que el dispositivo puede leer si tiene cámara, aunque inusual en ESP8266) para pasar la configuración.
3.  **Manual**: Copiar/Pegar el token en el Portal Cautivo del dispositivo.

## 4. Diseño Visual (Aesthetics)
*   **Dark Mode First**: Interfaz moderna con acentos en colores neón (azul para ESP32, verde para ESP8266).
*   **Micro-animaciones**: Transiciones suaves cuando un dispositivo pasa de offline a online.
*   **Glassmorphism**: Tarjetas con efecto de cristal para los indicadores de señal.

## 5. Implementación Técnica
*   **Backend**: Nuevo `admin_iot_router.py` para las operaciones CRUD y de estado.
*   **Frontend**: Uso de `iot_socket.svelte.ts` para recibir actualizaciones de salud de los dispositivos mientras el administrador tiene el panel abierto.
