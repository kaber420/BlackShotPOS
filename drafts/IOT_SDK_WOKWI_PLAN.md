# Plan de Diseño: IoT SDK Independiente (Wokwi Engine)

Este plan propone la creación de un SDK de desarrollo separado del repositorio principal del POS, diseñado específicamente para hardware ESP32 y utilizando **Wokwi** como motor de simulación electrónica.

## 1. Visión: Hardware Auténtico en Entorno Virtual
A diferencia de un simulador web, este SDK utiliza la emulación de arquitectura de silicio de Wokwi. Esto permite probar el firmware real (pines, buses I2C/SPI, memoria) sin tener el hardware físico en la mano.

## 2. Estructura del Proyecto (`iot_sdk/`)
El SDK residirá en un directorio independiente con la siguiente estructura:

*   `firmware/`: Código fuente principal (MicroPython).
    *   `bs_client.py`: Librería core para la conexión segura con Blackshot POS (WebSockets).
    *   `main.py`: Lógica de arranque y bucle de eventos.
    *   `templates/`: Lógica de renderizado para diferentes pantallas.
*   `sim/`: Configuraciones de Wokwi.
    *   `oled_ssd1306/`: Configuración `diagram.json` para pantallas monocromáticas (128x64).
    *   `tft_ili9341/`: Configuración `diagram.json` para pantallas a color (320x240).
*   `wokwi.toml`: Configuración para ejecución mediante `wokwi-cli` o extensión de VS Code.

## 3. Soporte de Pantallas y Plantillas

| Driver | Pantalla | Resolución | Características Simu |
| :--- | :--- | :--- | :--- |
| **SSD1306** | OLED 0.96" | 128x64 | Texto rápido, bajo refresco, estilo retro. |
| **ILI9341** | TFT 2.4" | 320x240 | Color total, iconos de estado, barra de progreso. |
| **ST7789** | TFT 1.3" | 240x240 | Alta densidad, ideal para notificaciones circulares. |

## 4. Flujo de Desarrollo con Wokwi
1.  **Edición**: Se modifica el código en la carpeta `firmware/`.
2.  **Simulación**: Se abre el proyecto en el simulador de Wokwi.
3.  **Conexión**: El simulador usa la red del equipo para conectar al backend local de Blackshot (`ws://10.0.2.2:8000` en Wokwi).
4.  **Validación**: Se observa el comportamiento real del bus I2C/SPI y cómo se dibuja píxel a píxel en la pantalla emulada.

## 5. Próximos Pasos
1.  Crear la estructura inicial del directorio `iot_sdk/`.
2.  Implementar la librería `bs_client.py` optimizada para el protocolo minimalista del POS.
3.  Proporcionar el archivo `diagram.json` "Gold Standard" que sirva de base para todas las futuras pantallas de Blackshot.

---
Este enfoque cumple con la necesidad de un "SDK aparte" y utiliza herramientas open-source/Wokwi para garantizar que lo que se ve en el simulador sea 100% trasladable al hardware real.
