# Plan de Refactorización Modular: Firmware IoT (Blackshot TablePad)

## 1. El Mito del "Código Espagueti" en C/C++
Es un mito común creer que C y C++ son lenguajes obsoletos y rígidos que obligan a tener archivos gigantes y desordenados. La realidad es que **C++ es pionero en la Programación Orientada a Objetos** e incluye un sistema extremadamente robusto de Clases y Archivos de Cabecera (`.h` y `.cpp`) que permite un nivel de modularidad increíble. El problema que experimentamos no fue culpa del lenguaje, sino de ir "parcheando" un prototipo sin definir primero la arquitectura.

## 2. Los Principios del Nuevo Firmware (Arquitectura Limpia)
Para evitar absolutamente que el ESP32 colapse y se "rompa" al añadir nuevas funciones, aplicaremos tres reglas profesionales:

1. **Separación de Responsabilidades:** El código que maneja los gráficos (LVGL) no debe tener idea de que existe el internet (WiFi/WebSockets). Y viceversa.
2. **Uso de Doble Núcleo (FreeRTOS Threads):** Aprovecharemos los dos cerebros del ESP32.
   - **Core 0 (Sistema/Red):** Se encargará de la conectividad (WiFi, reconexión automática, descifrar WebSockets).
   - **Core 1 (Interfaz Gráfica):** Se encargará estrictamente de renderizar a 60FPS constantes y leer el tacto.
3. **Comunicación por "Buzones Seguros" (Queues y Mutexes):** ¡Nunca más la red actualizará la pantalla directamente! La red empaquetará la nueva instrucción en un "buzón" (FreeRTOS Queue). La interfaz gráfica leerá ese buzón cuando esté libre y actualizará la pantalla de forma 100% segura.

## 3. Estructura de Directorios Desacoplada
Así luciría el código ordenado, donde cada componente es reemplazable sin romper nada:

```text
/firmware_iot
├── /src
│   ├── main.cpp                    # Solo arranca los servicios y los dos Núcleos (Threads).
│   ├── /Network
│   │   ├── WiFiManager.cpp         # Lógica de conexión a red
│   │   ├── SocketController.cpp    # Conexión pura con Blackshot POS
│   ├── /State
│   │   ├── AppState.cpp            # "La Memoria" global del ESP32 donde se guardan las órdenes
│   │   ├── EventBus.cpp            # El "Buzón" de FreeRTOS
│   ├── /UI
│   │   ├── UIManager.cpp           # Orquestador de LVGL
│   │   ├── DashboardView.cpp       # Pantalla que muesta las órdenes
│   │   ├── StylingAndThemes.cpp    # Para no tener colores hardcodeados, todo el diseño va aquí.
```

## 4. El Flujo de Ejecución Correcto (Ejemplo Vida Real)
¿Qué pasará cuando una orden se ponga "Lista"?
1. El backend envía al WebSocket: `{"action": "update", "order_id": 4, "state": "ready"}`.
2. `SocketController.cpp` (Corriendo en Núcleo 0) atrapa el JSON, pero **no** toca la pantalla. Se lo pasa a `EventBus.cpp`.
3. `DashboardView.cpp` (Corriendo en Núcleo 1), en su siguiente ciclo de dibujo (milisegundos después), nota que hay un mensaje en el Buzón. 
4. Lee de forma segura el estado "ready" y pinta la tarjeta de verde, sin crear choques de memoria (Guru Meditation Error).

## 5. Beneficios de esta Estructura
- **Cero crasheos inexplicables:** La memoria de la pantalla no volverá a pisarse con la red.
- **Tranquilidad al editar:** Si tú o la IA editan el color de un botón o cómo se alinea el texto en `DashboardView.cpp`, **es imposible** que esa edición rompa la conexión WiFi. Todo vive en aislamiento.
- **Preparación para Producción:** Así es como se construyen los Sistemas Embebidos de grado industrial y la electrónica comercial.
