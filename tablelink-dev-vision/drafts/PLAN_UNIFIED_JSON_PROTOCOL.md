# Unificación de Protocolo JSON: Migración a ArduinoJson

Este plan detalla la migración del motor de JSON del simulador (x86) de `nlohmann/json` a `ArduinoJson`. El objetivo principal es asegurar que la lógica de procesamiento de datos sea **idéntica** entre el simulador y el firmware real del ESP32, eliminando riesgos de gestión de memoria (Heap Fragmentation) en el hardware físico.

## User Review Required

> [!IMPORTANT]
> **Cambio de Sintaxis**: La forma de acceder a los campos JSON cambiará ligeramente (de `obj["key"].get<int>()` a `obj["key"].as<int>()` o acceso directo). Esto afectará a `main.cpp` y `SocketController.cpp`.
> **Gestión de Memoria**: Pasaremos de una gestión dinámica (Heap) a una gestión por "Memory Pools" (`JsonDocument`). Esto es mucho más seguro para el ESP32 pero requiere definir tamaños máximos de buffer (ej. 2KB o 4KB).

## Proposed Changes

### [Componente] Dependencias y Build System

#### [MODIFY] [CMakeLists.txt](file:///home/kaber420/Documentos/proyectos/blackshot_iot/CMakeLists.txt)
- Eliminar la descarga de `nlohmann/json`.
- Agregar `FetchContent` para `ArduinoJson` (v7.0.4).
- Actualizar el enlazado (`target_link_libraries`) para usar la nueva librería.

### [Componente] Comunicación de Red

#### [MODIFY] [SocketController.cpp](file:///home/kaber420/Documentos/proyectos/blackshot_iot/src/Network/SocketController.cpp)
- Reemplazar `#include <nlohmann/json.hpp>` por `#include <ArduinoJson.h>`.
- Refactorizar el método `update()` para que la creación de mensajes de salida use `JsonDocument::serializeJson`.

### [Componente] Procesamiento Central (RTOS Parser)

#### [MODIFY] [main.cpp](file:///home/kaber420/Documentos/proyectos/blackshot_iot/src/main.cpp)
- Reemplazar el motor de parsing en el bucle principal.
- Eliminar las funciones lambda de "unwrap" complejas y sustituirlas por un flujo de procesamiento basado en `ArduinoJson` que sea compatible con ESP32.
- Implementar la lógica de "fallback" para campos faltantes usando la API nativa de `ArduinoJson` (`.as<T>()` o el operador `|`).

## Open Questions

> [!NOTE]
> **¿Tamaño del Buffer?**: Propongo un `JsonDocument` de 4096 bytes para el simulador y el hardware. Esto es suficiente para órdenes con hasta 15-20 platillos. ¿Consideras que necesitamos algo más grande para pedidos masivos?

## Verification Plan

### Automated/Manual Tests
- [ ] Ejecutar `cmake ..` y verificar que descarga `ArduinoJson` correctamente.
- [ ] Compilar el proyecto.
- [ ] Iniciar el simulador y verificar la conexión via WebSocket.
- [ ] Inyectar un mensaje `order_new` real desde el backend/estudio y verificar que la UI de LVGL se actualiza correctamente.
- [ ] Verificar que las acciones de la UI (llamar camarero, etc.) se envían correctamente al servidor.
