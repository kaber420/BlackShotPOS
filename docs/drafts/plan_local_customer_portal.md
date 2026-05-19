# Especificación Técnica: Portal de Clientes Local (Fase 1)

Este documento define la arquitectura lógica, el modelo de datos y el flujo de autenticación para el **Portal de Clientes Local** de Blackshot POS. Se descarta cualquier lógica de sincronización multi-sucursal (el Bridge) o exposición externa en esta fase, centrándose exclusivamente en un despliegue **100% local, offline-first y unificado en la base de datos PostgreSQL de la sucursal**.

---

## 1. Visión Técnica y Enrutamiento de Red

El portal de clientes es una Single Page Application (SPA) optimizada para dispositivos móviles. Los clientes se conectan al Wi-Fi del local, escanean el código QR de la mesa y abren el portal estático en su navegador.

### 1.1 Esquema de Puertos y Comunicación
*   **`bs_frontend` (Puerto 5173):** Interfaz exclusiva del Staff (Caja, Cocina, Reportes). Aislada en la intranet del personal.
*   **`bs_customer_portal` (Puerto 5174 / Servidor Estático):** Interfaz pública del cliente. 
*   **`pos_core` (Puerto 8000):** Único backend y entrada de red local. 
    *   El portal estático del cliente en el celular realiza peticiones `fetch()` locales directamente a la IP del servidor en el puerto `8000`.
    *   Toda la comunicación de red del cliente se agrupa bajo el prefijo seguro `/api/v1/public/...`.

---

## 2. Modelo de Datos Unificado (PostgreSQL)

Los clientes se registran y validan directamente contra la tabla `Customer` en la base PostgreSQL de la sucursal (`blackshot_db`). La lógica de datos mapea exactamente el código existente en `models.py`:

```
  [ Campo de Login ] ---->  username (Texto plano, índice único, index=True)
  [ Campo de Pass ]  ---->  hashed_password (Argon2 para contraseñas de portal)
  [ Identidad ]      ---->  id (UUID primario, inalterable y persistente)
  [ Datos PII ]      ---->  encrypted_name, encrypted_phone (Cifrado simétrico AES/Fernet)
  [ Tarjeta QR ]     ---->  loyalty_code (8 caracteres hexadecimales únicos de lealtad)
  [ Preferencias ]   ---->  custom_metadata (JSON para alergias, notas de preparación)
```

### 2.1 Reglas de Privacidad y PII
*   **Username:** No va cifrado ya que es el identificador lógico único de la cuenta.
*   **Datos Sensibles (PII):** El Nombre (`encrypted_name`) y el Teléfono (`encrypted_phone`) se cifran simétricamente en reposo para proteger la privacidad. El número de teléfono es opcional y no tiene ninguna relación con las credenciales de inicio de sesión.
*   **Búsqueda Rápida de Staff:** La columna `phone_hash` (SHA256 determinista) se usa exclusivamente para que los empleados busquen rápidamente a un cliente en la caja física, sin impactar la lógica de autenticación del portal.

---

## 3. Flujo Lógico de Endpoints Públicos (`/api/v1/public`)

La autenticación y consumo del portal se realiza de forma directa mediante la API expuesta en `pos_core/customers/public_router.py`:

> [!IMPORTANT]
> **Regla Operativa Crítica:** El portal de clientes **no permite el auto-registro**. El alta de nuevos clientes es gestionada de manera exclusiva por el personal (Staff) físicamente en la caja o terminal del local (`bs_frontend`). Esto previene el registro de cuentas basura/spam y mantiene el control absoluto del catálogo de fidelidad.

### 3.1 Inicio de Sesión (`POST /api/v1/public/customers/auth/login`)
*   **Entrada:** `{ username, password }`
*   **Lógica en el Servidor:**
    1. Busca el registro por el `username` directo en PostgreSQL (`CustomerService.get_by_username`).
    2. Si el usuario no existe, rebota con `401 Unauthorized`.
    3. Verifica la contraseña enviada contra `hashed_password` usando `CryptoService.verify_password`.
    4. Si es válida, devuelve un JWT firmado con el UUID. El navegador del celular del cliente guarda este token en `localStorage` bajo `customer_token`.

### 3.3 Consulta de Perfil (`GET /api/v1/public/customers/me`)
*   **Cabecera:** `Authorization: Bearer <JWT>`
*   **Lógica en el Servidor:**
    1. La dependencia de FastAPI `get_current_customer` valida el JWT del cliente y extrae su UUID.
    2. Lee el registro de PostgreSQL. Los decoradores `@property` descifran en memoria el Nombre y Teléfono al vuelo.
    3. Devuelve los datos financieros reales del cliente (`points`, `credit_balance`, `loyalty_code`, `custom_metadata`) mapeados en el esquema `CustomerRead`.
    4. El Svelte del cliente recibe el JSON y genera en pantalla el código QR usando la API nativa de renderizado de QR a partir de su `loyalty_code`.

### 3.4 Actualizar Preferencias (`PATCH /api/v1/public/customers/me/preferences`)
*   **Cabecera:** `Authorization: Bearer <JWT>`
*   **Entrada:** `{ custom_metadata: dict }`
*   **Lógica en el Servidor:**
    1. Extrae el UUID del cliente del JWT.
    2. Actualiza el campo `custom_metadata` en PostgreSQL (alergias, notas de preparación, café favorito).
    3. Devuelve la ficha del cliente actualizada.

---

## 4. Aislamiento Físico y de Privilegios de APIs

El sistema implementa dos barreras de seguridad infranqueables para evitar que los clientes interfieran con la operación del Punto de Venta:

1.  **Tokens Totalmente Incompatibles:** Los tokens JWT de clientes son firmados y validados con algoritmos y llaves totalmente distintos a los tokens del personal del local (`fastapi_users`).
2.  **Dependencia Exclusiva `get_current_active_user`:** Todas las rutas del Staff (`/api/v1/pos/sales/*`, `/api/v1/pos/inventory/*`) exigen esta dependencia. Si recibe un token JWT de cliente, FastAPI-Users no lo reconocerá (no existe un empleado con ese token) y rechazará la petición con un `401 Unauthorized` de inmediato.
3.  **Dependencia Exclusiva `get_current_customer`:** Las rutas del cliente (`/api/v1/public/...`) exigen esta dependencia. Protege la información privada para garantizar que un cliente solo pueda leer y modificar su propio UUID.
