# Plan de Implementación: Estandarización de FRONTEND_PORT

Este documento define la estrategia para migrar la configuración de red de BlackShot POS hacia un modelo basado en variables de entorno explícitas, eliminando dependencias de puertos de desarrollo y facilitando la integración con Proxies Reversos y túneles de Cloudflare.

## 1. Problema Actual
Actualmente, la lógica de descubrimiento de red en `pos_core/setup.py` utiliza puertos hardcodeados (`5173` para desarrollo y `8000` para API). Esto genera:
- Inconsistencias al desplegar en producción (donde el puerto suele ser 80 o 443).
- Dificultad para configurar Proxies Reversos de forma automatizada.
- Falta de control granular sobre los orígenes de CORS permitidos.

## 2. Solución Propuesta
Introducir la variable `FRONTEND_PORT` como un estándar dentro del ecosistema BlackShot. Esto permite que la API sepa exactamente en qué puerto está corriendo el cliente sin tener que "adivinar" o forzar configuraciones manuales complejas.

### 2.1 Cambios en el Entorno (`.env`)
Se añadirán y asegurarán las siguientes variables:
- `PORT`: Puerto de escucha de la API (Binding).
- `FRONTEND_PORT`: Puerto de origen del cliente (CORS).
- `HOST`: IP específica de binding para seguridad estricta.

### 2.2 Lógica de Automatización (`setup.py`)
El script de configuración se actualizará para:
1.  **Detección:** Si `FRONTEND_PORT` no existe, se creará con el valor `80` (Estándar de producción).
2.  **Generación de Orígenes:** Al autorizar una IP o Dominio, el sistema construirá la Whitelist de CORS usando exclusivamente estas variables:
    *   `http://{IP}:{FRONTEND_PORT}`
    *   `http://{IP}:{PORT}` (para llamadas directas a la API)

## 3. Arquitectura de Red Resultante

### Escenario A: Acceso Directo (SBC)
- API Escucha en: `192.168.1.50:8000`
- Frontend corre en: `192.168.1.50:80`
- **Configuración:** `PORT=8000`, `FRONTEND_PORT=80`, `HOST=192.168.1.50`.

### Escenario B: Proxy Reverso (Nginx) + Cloudflare
- API Escucha en: `127.0.0.1:8000`
- Proxy Escucha en: `192.168.1.50:80`
- **Configuración:** `PORT=8000`, `FRONTEND_PORT=80`, `HOST=127.0.0.1`.
- **CORS:** El origen autorizado será `http://192.168.1.50` (puerto 80 implícito).

## 4. Plan de Acción
1.  **Modificar `pos_core/setup.py`:** Actualizar `_ensure_secure_tokens` y `check_and_prompt_ip`.
2.  **Actualizar `.env.example`:** Reflejar las nuevas variables para futuros despliegues.
3.  **Sincronizar el CLI:** Asegurar que `blackshot run` lea estas variables de forma prioritaria.

---
**Estado:** Pendiente de Aprobación
**Fecha:** 2026-05-16
