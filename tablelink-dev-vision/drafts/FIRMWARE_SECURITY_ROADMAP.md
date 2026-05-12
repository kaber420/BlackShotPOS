# Hoja de Ruta: Seguridad y Aprovisionamiento del Firmware
**Proyecto:** Blackshot IoT (TablePad)
**Estado:** Borrador de Arquitectura Permanente

Este documento detalla el plan para convertir el prototipo actual en un firmware comercialmente viable, seguro y f\xc3\xa1cil de configurar para el usuario final mediante una APK (App M\xc3\xb3vil).

---

## 1. Arquitectura de Seguridad (The Vault)
Para evitar que el hardware sea vulnerable si es robado o manipulado, dividiremos la informaci\xc3\xb3n en dos capas:

### Capa A: Almacenamiento No Vol\xc3\xa1til (NVS) Cifrado
*   **Contenidos:** SSID del WiFi, Contrase\xc3\xb1a del WiFi, Token del POS y Contrase\xc3\xb1a de Administrador.
*   **Implementaci\xc3\xb3n:** Usaremos el sistema **NVS (Non-Volatile Storage)** de Espressif con cifrado habilitado.
*   **Procedimiento:** Los datos sensibles NO aparecer\xc3\xa1n en archivos de texto planos ni en el `config.json`. Ser\xc3\xa1n guardados en una partici\xc3\xb3n binaria protegida por hardware.

### Capa B: Token de Seguridad Cifrado
*   Incluso dentro de la memoria protegida, el **Token** se almacenar\xc3\xa1 encriptado con un hash derivado de la **Contrase\xc3\xb1a de Administrador**.
*   Solo se desencriptar\xc3\xa1 en la memoria RAM vol\xc3\xa1til del terminal justo antes de iniciar el handshake del WebSocket.

---

## 2. El Ciclo de Vida: Estados del Dispositivo (State Machine)
El firmware se comportar\xc3\xa1 de forma distinta seg\xc3\xban su estado de vida:

### Fase 1: MODO SETUP (Primer Encendido)
Se activa autom\xc3\xa1ticamente si no hay credenciales v\xc3\xa1lidas.
1.  **BLE Adv:** El terminal empieza a anunciar su presencia por Bluetooth como "Blackshot-Setup-[ID]".
2.  **Conexi\xc3\xb3n APK:** El instalador abre la APK y se conecta al terminal.
3.  **Configuraci\xc3\xb3n:** Se env\xc3\xadan el SSID, el Password del WiFi, el Token y se define la Contrase\xc3\xb1a de Administrador.
4.  **Sellado:** El ESP32 valida la conexi\xc3\xb3n, guarda los datos en su "caja fuerte" y se reinicia.

### Fase 2: MODO OPERATIVO (Producci\xc3\xb3n)
1.  **Protecci\xc3\xb3n:** Al detectar credenciales v\xc3\xa1lidas, el terminal **desactiva el Bluetooth** y el modo Access Point (AP) para siempre (o hasta que se haga un Factory Reset f\xc3\xadsico).
2.  **Conexi\xc3\xb3n POS:** Se conecta directamente al WiFi y al servidor WebSocket usando el token blindado.
3.  **Config Din\xc3\xa1mica:** Lee el `config.json` para cargar temas, logos y nombres del restaurante (datos no sensibles).

---

## 3. Integraci\xc3\xb3n con la APK (Protocolo Bluetooth)
Dise\xc3\xb1aremos un **Servicio GATT** simplificado (el "buz\xc3\xb3n" de mensajes):

1.  **Canal 1 (WiFi)**: Para recibir el SSID y el Password.
2.  **Canal 2 (Identidad)**: Para recibir el Token y el Table ID.
3.  **Canal 3 (Seguridad)**: Para definir la Contrase\xc3\xb1a de Administrador.

---

## 4. Gesti\xc3\xb3n de JSON Coexistente
El archivo `config.json` seguir\xc3\xa1 existiendo pero su prop\xc3\xb3sito ser\xc3\xa1 exclusivamente est\xc3\xa9tico:
- **Desactivar AP:** Una bandera en el JSON puede forzar la desactivaci\xc3\xb3n del modo Setup si el administrador lo requiere por seguridad extrema.
- **Personalizaci\xc3\xb3n:** Etiquetas de botones, colores y tiempos de respuesta de la UI.

---

## 5. Pr\xc3\xb3ximos Pasos Técnicos
1.  **Refactor del Simulador:** Crear un "Mock" de la memoria NVS para que el simulador pueda testear estos estados.
2.  **Implementaci\xc3\xb3n de MbedTLS:** Incluir la librer\xc3\xada de cifrado para el manejo del token.
3.  **L\xc3\xb3gica de Reset:** Implementar un m\xc3\xa9todo (ej: presionar el bot\xc3\xb3n "M\xc3\x81S" por 10 segundos) para volver al Modo Setup si se pierde la contrase\xc3\xb1a.
