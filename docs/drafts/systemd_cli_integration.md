# Plan: Integración de Gestión de Servicios Systemd en el CLI

Este documento detalla el plan para integrar la gestión de servicios de sistema (systemd) directamente en la herramienta de línea de comandos `blackshot`. Esto permitirá que el POS se configure y se gestione de forma automática, optimizando el uso de recursos en dispositivos como SBC (Raspberry Pi/Orange Pi).

## Objetivos
- Eliminar la necesidad de scripts externos o rutas hardcodeadas manualmente.
- Permitir la auto-configuración del entorno detectando automáticamente la ubicación del proyecto y el entorno virtual (`.venv`).
- Facilitar la activación dinámica del **Sync Agent** solo cuando sea necesario.
- Optimizar el consumo de RAM al ejecutar la aplicación de forma nativa.

## Cambios Propuestos

### 1. Módulo de Lógica: `pos_core/setup.py`
Se añadirá la función `manage_systemd_services(action)` que contendrá la lógica pesada:
- **Detección de Rutas:** Uso de `os.getcwd()` y `sys.executable` para garantizar que los servicios apunten al lugar correcto.
- **Generación de Archivos:** Creación de archivos `.service` temporales y su movimiento a `/etc/systemd/system/` mediante comandos de sistema.
- **Gestión de Permisos:** Uso de `sudo` para operaciones que requieren privilegios de root.

### 2. Interfaz de Comandos: `pos_core/cli.py`
Se añadirá un nuevo subcomando `service` con las siguientes opciones:
- `blackshot service install`: Genera e instala los archivos `blackshot-pos.service` y `blackshot-sync.service`.
- `blackshot service uninstall`: Elimina los servicios del sistema.
- `blackshot service start`: Habilita e inicia el servicio del POS.
- `blackshot service stop`: Detiene el servicio.
- `blackshot service status`: Muestra el estado actual mediante `systemctl`.

## Estructura del Servicio Generado
El servicio utilizará los siguientes parámetros dinámicos:
- **User:** El usuario actual del sistema.
- **WorkingDirectory:** La carpeta raíz donde se ejecuta el comando `install`.
- **ExecStart:** El binario de Python dentro del `.venv` del proyecto.
- **EnvironmentFile:** El archivo `.env` local para cargar toda la configuración.

## Plan de Verificación
1. **Instalación:** Ejecutar `blackshot service install` y verificar que el archivo `/etc/systemd/system/blackshot-pos.service` contenga las rutas correctas.
2. **Arranque:** Ejecutar `blackshot service start` y verificar que el API responda en el puerto configurado.
3. **Persistencia:** Reiniciar la SBC y verificar que el servicio inicie automáticamente.
4. **Logs:** Validar que los logs se capturen correctamente con `journalctl`.

---
> [!IMPORTANT]
> Este enfoque mantiene la lógica de negocio separada de la infraestructura, permitiendo que Blackshot sea "agnóstico" a su ubicación física en el disco.
