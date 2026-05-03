# 🌉 Plan: Autenticación Dual & El Bridge (SaaS -> Local)

Este documento define la implementación técnica para permitir que el Panel Central (SaaS) se comunique de forma segura con las sucursales locales, conviviendo con la autenticación de staff existente.

## 🎯 Objetivo
Permitir el acceso a la API de la sucursal mediante dos vías:
1.  **Staff Local:** Vía Cookies/JWT (gestionado por FastAPI Users).
2.  **Manager Remoto (Bridge):** Vía header `X-Blackshot-Bridge-Auth` firmado con RS256.

---

## 🔒 Seguridad (RS256)

Utilizaremos criptografía asimétrica para garantizar que solo el Panel Central pueda enviar comandos a la sucursal.

| Elemento | Ubicación | Función |
| :--- | :--- | :--- |
| **Llave Privada** | Panel Central (SaaS) | Firma los tokens de comando. **Nunca sale del servidor central.** |
| **Llave Pública** | Sucursal (Base de Datos) | Verifica que la firma sea auténtica. Es segura de almacenar en DB. |

### Estructura del Token Bridge (JWT)
El header `X-Blackshot-Bridge-Auth` contendrá un JWT con:
- `iss`: "blackshot-central"
- `sub`: ID de la sucursal.
- `iat`: Timestamp de emisión.
- `exp`: Expiración corta (ej. +60 segundos) para evitar ataques de repetición.
- `cmd`: El comando o permiso que se está ejerciendo.

---

## 🛠️ Componentes a Implementar

### 1. Extensión de Configuración (`BusinessSettings`)
Añadir a la base de datos:
- `bridge_enabled`: Booleano para activar/desactivar el acceso remoto.
- `bridge_public_key`: El bloque de texto PEM de la llave pública.

### 2. Validador de Seguridad (`pos_core/auth/bridge.py`)
Un servicio que:
1.  Extraiga el header.
2.  Cargue la llave pública desde la caché de configuración.
3.  Valide el JWT usando la librería `python-jose` o `PyJWT`.

### 3. Dependencia Dual (`require_staff_or_bridge`)
Una función de FastAPI que actúe como "puerta lógica OR":
- Si `fastapi_users.current_user` es válido -> **OK**.
- Si `bridge.validate_request` es válido -> **OK**.
- Si ambos fallan -> **401 Unauthorized**.

---

## 📈 Flujo de una Petición Remota

1.  El **Panel Central** genera un comando (ej: "Obtener reporte de ventas").
2.  El Panel firma el comando con su **Llave Privada**.
3.  La **Sucursal** recibe la petición.
4.  El middleware de la sucursal lee su propia DB, saca la **Llave Pública** y verifica la firma.
5.  Si es válida, la sucursal ejecuta la petición y devuelve los datos al Panel.

---

---

## 📡 Datos en Tiempo Real (WebSockets)

Para monitoreo en vivo (ver órdenes caer al instante), el Bridge utiliza el token de corta duración solo como un "Apretón de Manos" (Handshake):

1.  **Conexión**: El Panel Central inicia la conexión WebSocket hacia la sucursal.
2.  **Validación**: Envía el token firmado (`X-Blackshot-Bridge-Auth`) en los parámetros de la URL o en el primer mensaje.
3.  **Persistencia**: La sucursal valida el token. Si es auténtico y tiene < 60s, la conexión se mantiene **abierta indefinidamente**.
4.  **Re-validación**: Si la conexión se corta, el Panel debe generar un **nuevo token** con el timestamp actual para reconectar.

---

## ✅ Beneficios
1.  **Flexibilidad:** El dueño puede ver sus ventas desde su casa sin necesidad de estar logueado como un empleado local.
2.  **Seguridad:** Aunque alguien robe la base de datos de la sucursal, no puede "hackear" el sistema central porque no tiene la llave privada.
3.  **Protección contra Replay Attacks:** El límite de 60 segundos asegura que los tokens interceptados queden obsoletos casi instantáneamente.
4.  **Cero Configuración de Red:** Al usar este Bridge, podemos integrar túneles (como Cloudflare o Ngrok) de forma segura.