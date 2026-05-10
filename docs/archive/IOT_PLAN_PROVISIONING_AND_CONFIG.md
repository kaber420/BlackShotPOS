# Plan de Aprovisionamiento y Seguridad: Blackshot TablePad

**Versión:** 1.3.0
**Estado:** Detalle de Flujos de Aprovisionamiento y Resiliencia

Este documento define el mecanismo pormenorizado de configuración, transición de estados de red y protección de parámetros para los terminales TablePad. El objetivo es un dispositivo autónomo, seguro y resiliente a fallos de red.

---

## 1. Métodos de Aprovisionamiento Inicial

El dispositivo entra en **Modo de Configuración** (escucha activa) si al encender detecta que no tiene credenciales válidas en su almacenamiento interno. 

Debe soportar dos vías simultáneas o priorizadas para recibir sus credenciales iniciales:

### A. Bluetooth (BLE)
*   **Activación:** Modo principal y prioritario. El dispositivo enciende la radio BLE y emite una señal (beacon) identificativa (ej. `BS-TP-XXXX`).
*   **Funcionamiento:** Una app móvil, panel web con WebBluetooth, o el mismo servidor POS (si tiene hardware BLE) transfiere el paquete de configuración encriptado.

### B. Access Point (AP) con Portal Cautivo
*   **Activación:** Método de respaldo (fallback). El TablePad crea su propia red WiFi (Modo AP), ej: `Blackshot-Config-XXXX`.
*   **Funcionamiento:** Al conectarse a esta red desde un móvil o PC, se intercepta la navegación y se despliega un formulario web local guiado para ingresar los datos manualmente.

---

## 2. Datos de Configuración (Estructura del `config.json`)

Los datos recibidos por BLE o Portal Cautivo se almacenarán localmente (`config.json` o NVRAM).

*   **Identidad de Red y Servidor:**
    *   **SSID:** Nombre de la red WiFi del restaurante (Público).
    *   **Server IP / Host:** Dirección del servidor POS al que conectarse (Público).
    *   **Puerto:** Puerto del servicio WebSocket (Público).
*   **Credenciales Sensibles (Cifradas):**
    *   **WiFi Password:** Encriptado en el almacenamiento.
    *   **Device Token:** Clave de acceso única del dispositivo. Encriptado en el almacenamiento.
    *   **Admin PIN (Password):** Contraseña requerida para permitir modificaciones a la configuración (cambiar WiFi, renovar token). Encriptado.
*   **Identidad Local (Offline Identity):**
    *   Campos base para inicialización visual rápida antes de conectar: `business_name` y `table_id_default`.
    *   **Propósito:** Mostrar una UI coherente (ej. "Mesa 12", "Mi Local") durante los segundos que tarda en encender y enlazar, en lugar de mostrar "Mesa ?".

---

## 3. Flujo Post-Configuración (Transición de Estado)

Un dispositivo aprovisionado correctamente no debe quedarse en modo configuración. El flujo es el siguiente:

1.  **Guardado:** El dispositivo recibe el payload de configuración (vía BLE o AP), lo valida estructuralmente y guarda los datos (encriptando password y token).
2.  **Transición de Red (AP -> STA):** 
    *   Se apagan los servicios de aprovisionamiento (BLE / AP Cautivo).
    *   El chip pasa a modo **Estación (STA)**.
3.  **Enlace (Handshake):**
    *   Se conecta al WiFi especificado.
    *   Inicia la conexión WebSocket hacia el `Server IP` usando su `Device Token` desencriptado en memoria.
4.  **Toma de Control:**
    *   Al conectar exitosamente, el Servidor POS asume el control total.
    *   El Servidor envía el evento `config` que sobreescribe la Identidad Local para asegurar que tiene los datos más recientes según el Panel Admin.

---

## 4. Resiliencia y Manejo de Fallos (Modo Diagnóstico)

Si el dispositivo pierde la conexión o falla el arranque, no debe quedar "inútil". Debe entrar en un modo que permita su reparación:

*   **Disparadores del Modo Fallo:**
    1.  Fallo en la conexión WiFi persistente (ej. cambio de contraseña del routeador).
    2.  No se puede alcanzar el servidor POS.
    3.  El Servidor POS rechaza la conexión por **Token Inválido o Revocado**.
*   **Acción del Dispositivo:**
    *   Se ilumina la interfaz indicando el error específico (ej. "Token Revocado", "Sin red").
    *   **Enciende automáticamente el Bluetooth (BLE)** (y opcionalmente el AP).
    *   Permite a un administrador conectarse para examinar el error, corregir un password mal tecleado, o sobreescribir el token si fue renovado desde el POS.

---

## 5. Seguridad Integral y Mantenimiento de Tokens

*   **Protección de Reconfiguración (Admin Password):** 
    *   Para evitar que cualquier persona que tenga acceso físico al dispositivo pueda reconfigurarlo (si lo roban o manipulan), el acceso al modo aprovisionamiento (vía BLE o AP) exigirá un **Password o PIN de Administración**.
    *   Cuando la App o Panel intente empujar una nueva configuración (cambio de SSID, nuevo token), deberá enviar primero este PIN. Si no coincide, el dispositivo rechaza los cambios.
*   **Cifrado Selectivo:** Solo los datos sensibles (Password WiFi, Token, y Admin PIN) son ilegibles si se extrae físicamente la memoria del dispositivo.
*   **Revocación y Renovación Remota:** 
    *   El ciclo de vida del token se gestiona desde el **Panel Admin** del POS.
    *   Si se sospecha compromiso, el admin revoca el token en el POS. 
    *   En su próximo latido o intento de conexión, el TablePad será rechazado, activará su alarma de desconexión y encenderá su BLE habilitando su reconfiguración (accesible solo mediante el Admin PIN).
