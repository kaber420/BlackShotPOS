# Especificaciones de Hardware: Blackshot IoT
**Guía para Constructores y Diseñadores**

Para que el ecosistema Blackshot sea consistente, recomendamos el siguiente "Gold Standard" de hardware. Estas especificaciones garantizan compatibilidad total con la librería **Blackshot UI SDK**.

---

## 1. Unidad de Procesamiento (MCU)
Recomendamos el **ESP32-S3** por su soporte nativo de USB, mayor memoria PSRAM y excelente manejo de pantallas mediante su interfaz LCD periférica.

*   **Modelo:** ESP32-S3-WROOM-1 (N16R8 recomendado - 16MB Flash / 8MB PSRAM).
*   **Voltaje de entrada:** 3.3V - 5V.
*   **Conectividad:** Wi-Fi 2.4GHz (802.11 b/g/n) + Bluetooth 5 (LE).

---

## 2. Pantalla y Táctil
El SDK está optimizado para pantallas con drivers comunes integrados en LVGL.

*   **Resolución ideal:** 320x480 (3.5 pulgadas) o 240x320 (2.8 pulgadas).
*   **Driver LCD:** ILI9488, ST7789 o ST7796.
*   **Tipo de Táctil:** Capacitivo (GT911 o FT6236) para una experiencia "premium" sin presión.

---

## 3. Fabricación de Carcasas (Enclosures)
Dado que el proyecto se enfoca en "Artículos Inteligentes" (servilleteros, robots), la estética es fundamental.

*   **Tecnología recomendada:** Impresión 3D de **Resina (SLA/DLP)**.
    *   *¿Por qué?* Permite paredes delgadas, roscas integradas y una superficie lisa que se puede pintar o dejar traslúcida para efectos de luz (Glow-through).
*   **Material:** Resina estándar o "Tough" (resistente a impactos) para entornos de restaurante.

---

## 4. Diagrama de Conexión Típico (Muestra)
| Componente | Pin ESP32-S3 | Nota |
| :--- | :--- | :--- |
| **LCD_MOSI** | GPIO 13 | Bus SPI |
| **LCD_SCK** | GPIO 12 | Bus SPI |
| **LCD_CS** | GPIO 10 | Chip Select |
| **TOUCH_SDA** | GPIO 4 | Bus I2C |
| **TOUCH_SCL** | GPIO 5 | Bus I2C |

---

## 5. Próximos Pasos (Modelos 3D)
Próximamente publicaremos los archivos **STL y STEP** base para que puedas modificarlos en Fusion 360 y crear tus propios diseños de:
1.  **Nexus Holder:** Servilletero con pantalla inclinada.
2.  **Cubit Robot:** Un asistente de escritorio cúbico.
