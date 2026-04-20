# Blackshot IoT SDK (v1.0)

Este es el entorno de desarrollo y simulación para los dispositivos IoT (pantallas de mesa) del ecosistema Blackshot POS.

## Estructura
*   `firmware/`: Contiene el código MicroPython que se ejecuta en el ESP32.
*   `sim/`: Archivos `diagram.json` para cargar en Wokwi.

## Cómo empezar en Wokwi
1.  Entra en [Wokwi.com](https://wokwi.com) y crea un nuevo proyecto de **ESP32 MicroPython**.
2.  **Hardware**: Copia el contenido de `sim/oled/diagram.json` (o `tft`) en la pestaña `diagram.json` de Wokwi.
3.  **Librerías**: Crea una carpeta llamada `lib` en Wokwi y sube los archivos de `firmware/lib/`.
4.  **Código**: Pega el contenido de `firmware/main.py` en el archivo `main.py` de Wokwi.
5.  **Configuración**: 
    *   Asegúrate de cambiar `DEVICE_TOKEN` en `main.py` por un token válido generado en el POS.
    *   Si usas el simulador web, asegúrate de que tu backend sea accesible (puedes usar un túnel como ngrok y cambiar `SERVER_HOST`).

## Pruebas de Funcionamiento
*   Al iniciar, el dispositivo mostrará "Blackshot IoT".
*   Si la conexión es exitosa, cambiará a "CONECTADO" (en OLED).
*   Cuando marcas una orden como "READY" en el POS, el simulador recibirá el evento y mostrará la notificación en pantalla durante 5 segundos.

---
**Nota:** El SDK está diseñado para ser independiente del repositorio del POS. Si deseas moverlo a un repositorio separado, simplemente copia esta carpeta completa.
