# Borrador: Plan de Arquitectura IoT Nativa (Sin Puente)

Este plan define la transición de un sistema de simulación basado en puentes UDP a una arquitectura de software profesional donde el dispositivo (ESP32 o Simulador C++) se comunica de forma nativa y directa con el servidor POS.

## 1. Visión Técnica
Eliminar por completo el `iot_bridge.py`. El software del dispositivo debe ser el propietario de su comunicación. El "Simulador" dejará de ser un juguete y se convertirá en un **Gemelo Digital** que ejecuta el mismo código de red que el hardware real.

## 2. Componentes del Software (C++/LVGL)

### A. Capa de Red Nativa (WebSocket)
- **Librería**: Integración de `ixwebsocket`. Es ideal porque permite compilar el mismo código en Linux/Windows (para desarrollo) y en el ESP32.
- **Handshake de Identidad**: El dispositivo iniciará la conexión a `ws://[IP]:8400/api/v1/pos/ws/iot?token=[TOKEN]`.
- **Mocking de Identidad**: Para la simulación en PC, el software aceptará argumentos `--token` y `--mac` para simular que es un dispositivo específico registrado en el POS.

### B. Gestor de Eventos JSON
- El software procesará directamente los mensajes JSON del servidor.
- **Protocolo Minimalista**:
    - `{"ev": "prep", "msg": "..."}` -> Disparar estado de preparación en UI.
    - `{"ev": "rdy", "msg": "..."}` -> Disparar estado de "Listo" (animaciones/sonido).
- **Tráfico Saliente**: El dispositivo podrá enviar acciones como `{"action": "call_waiter"}` directamente al servidor.

## 3. Cambios en el Repositorio

#### [MODIFY] [CMakeLists.txt](file:///home/kaber420/Documentos/proyectos/blackshot/blackshot_ui_sdk/CMakeLists.txt)
- Añadir `ixwebsocket` como dependencia (vía subdirectorio o ExternalProject).
- Configurar flags de compilación para soporte de hilos (necesario para el cliente WS).

#### [REPLACE] [main.cpp](file:///home/kaber420/Documentos/proyectos/blackshot/blackshot_ui_sdk/src/main.cpp)
- **Eliminar**: Sockets UDP, `bind`, `recvfrom`.
- **Implementar**: `WebSocketClient` con callback de mensajes que actualice la interfaz LVGL de forma asíncrona.

#### [DELETE] [iot_bridge.py](file:///home/kaber420/Documentos/proyectos/blackshot/blackshot_ui_sdk/iot_bridge.py)
- Eliminación física del intermediario.

## 4. Plan de Validación
1.  **Conexión Directa**: Ejecutar el simulador `BlackshotUISDK` y verificar que aparece "Online" en el panel de gestión del POS inmediatamente.
2.  **Prueba de Flujo**: Marcar una orden como "Lista" en el POS y confirmar que el simulador C++ recibe el JSON y actualiza la pantalla sin latencia ni puentes.
3.  **Prueba de Identidad**: Correr dos instancias del simulador con tokens distintos y verificar que cada uno recibe solo sus propios mensajes.

---
**Nota**: Este plan garantiza que el software que desarrolles en tu PC sea 99% idéntico al que subirás al ESP32, cumpliendo con la visión de un desarrollo profesional y sin datos basura.
