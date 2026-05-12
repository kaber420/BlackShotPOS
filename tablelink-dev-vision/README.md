# Blackshot UI SDK (Open Source)

Este es un entorno de desarrollo de interfaces de usuario (UI) de alto rendimiento para los dispositivos de Blackshot, basado en **LVGL (v9+)** y **SDL2**.

## Requisitos Previos

Este SDK es una aplicación nativa que corre en tu PC. Necesitas instalar las dependencias de desarrollo de SDL2:

*   **Linux (Ubuntu/Debian)**:
    ```bash
    sudo apt install libsdl2-dev cmake build-essential
    ```
*   **macOS**:
    ```bash
    brew install sdl2 cmake
    ```

## Cómo empezar

1.  **Clonar el Repositorio**:
    ```bash
    git clone https://github.com/tu-usuario/blackshot-iot-sdk.git
    ```

2.  **Configurar Build**:
    ```bash
    mkdir build && cd build
    cmake ..
    ```

3.  **Compilar y Ejecutar**:
    ```bash
    make -j4
    ./BlackshotUISDK
    ```

## Desarrollo y Personalización
*   **Temas**: Edita `src/ui/themes.h` para cambiar colores, radios de borde y opacidades de forma global.
*   **Lógica**: Edita `src/ui/blackshot_ui.cpp` para crear nuevos widgets.
*   **Portabilidad**: Cualquier código en `src/ui/` es **100% compatible** con el hardware de Blackshot (ESP32).

## Licencia
Este proyecto está bajo la licencia **GNU Affero General Public License v3.0 (AGPLv3)**. Consulta el archivo [LICENSE](LICENSE) para más detalles.

---
**Nota:** Este SDK es independiente y permite iteraciones de UI extremadamente rápidas sin cables ni flasheos.
