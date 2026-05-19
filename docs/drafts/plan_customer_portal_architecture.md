# Especificación Técnica y Arquitectónica: Portal de Clientes (Carta Digital Interactiva)

Este documento detalla la arquitectura de red, el modelo de datos unificado, el flujo de autenticación y la seguridad para el **Portal de Clientes** de Blackshot POS. El objetivo es estructurar una experiencia interactiva basada en la **Carta Digital**, integrada localmente en el ecosistema de la sucursal, garantizando alta disponibilidad offline y seguridad perimetral local.

---

## 1. Visión del Producto: La Carta Interactiva

El portal de clientes es una extensión directa de la experiencia de compra de la cafetería. Su diseño está optimizado para dispositivos móviles bajo un esquema *Mobile-First*.

### 1.1 Comportamiento y UX
*   **Identidad Visual Compartida:** Reutilización de los componentes visuales de `bs_frontend` (como grids de productos, variantes y animaciones de Svelte 5 runes) para garantizar una experiencia fluida e idéntica a la del punto de venta.
*   **Búsqueda y Exploración:** Filtros interactivos por categorías y barra de búsqueda reactiva local para localizar productos instantáneamente.
*   **Perfil Privado:** Un área exclusiva donde el cliente visualiza:
    *   Su saldo a favor y puntos de lealtad acumulados.
    *   Su **Código QR de Lealtad** único para que el cajero lo escanee en la terminal física de cobro.
    *   Sus preferencias de consumo (alergias, favoritos, notas de preparación automáticas).

---

## 2. Arquitectura de UI y Red (Despliegue Local Unificado)

Para maximizar la simplicidad operativa y eliminar dependencias de internet en la mesa de los clientes, adoptamos una **arquitectura LAN de base única**.

```
                       [ RED LOCAL / WI-FI DE LA SUCURSAL ]
                       
  +------------------+                    +------------------------------------+
  |  Celular Cliente  | <--- HTTPS ---->  |           Servidor Local           |
  |  (Portal Svelte)  |                   |  (Puerto 8000 - Blackshot POS Core)|
  +------------------+                    +------------------------------------+
                                                            |
                                               [ Base PostgreSQL Local ]
                                               (Clientes y Ventas Unificados)
```

### 2.1 Aislamiento en el Mismo Hardware
1.  **`bs_frontend` (Puerto 5173 / Local):** Interfaz dedicada estrictamente al Staff (Caja, Pantalla de Cocina, Gestión de Inventario).
2.  **`bs_customer_portal` (Puerto 5174 / Local):** Interfaz dedicada al cliente, servida estáticamente. Consume únicamente la API pública del POS Core.
3.  **`pos_core` (FastAPI - Puerto 8000):** El motor unificado. Sirve tanto al staff como a los clientes mediante políticas de enrutamiento y dependencias de tokens separadas.

### 2.2 Ventajas del Despliegue de Red Local
*   **Indestructible ante Caídas de Internet:** Si la conexión a internet de la sucursal falla, el portal de clientes sigue operando al 100% de velocidad local para cualquiera conectado al Wi-Fi de la cafetería.
*   **Inmunidad a Ataques Externos (DDoS):** Al no exponer puertos a la WAN pública, el servidor físico local es invisible y totalmente inaccesible desde el exterior del local.

---

## 3. Modelo de Autenticación Unificado (Username + Password + UUID)

Los clientes y el staff coexisten en la misma base de datos física local (`blackshot_db`), pero bajo esquemas de tablas, privilegios y tokens totalmente separados. La autenticación de clientes se desvincula por completo del teléfono para evitar bloqueos si el usuario cambia de número.

### 3.1 Mecanismo de Identificación
*   **Identificador de Acceso:** El cliente utiliza un **Nombre de Usuario (`username`)** único y una **Contraseña (`password`)** robusta para autenticarse.
*   **Clave Persistente (UUID):** El identificador inalterable del cliente es su `id` (UUID). Este es el valor codificado en el token JWT y el usado para relacionar todas sus órdenes en caja.
*   **Datos Personales Cifrados (PII):**
    *   El Nombre (`encrypted_name`), Teléfono (`encrypted_phone`) y Email (`encrypted_email`) se cifran simétricamente en reposo (AES/Fernet).
    *   El número de teléfono es totalmente secundario y opcional. No tiene ningún impacto en las credenciales de inicio de sesión.
*   **Almacenamiento de Contraseña:** La contraseña se hashea usando **Argon2** en el campo `hashed_password` de la base de datos de la sucursal.
*   **Emisión de Tokens:** Al validar el username y el hash de la contraseña, el backend emite un JWT exclusivo para clientes (`role="customer"`) con el UUID en el campo `sub`.

### 3.2 Flujo de Rutas Públicas (Prefijo `/api/v1/public`)
*   `POST /api/v1/public/customers/auth/register`: Registra un cliente de forma local usando username, password, nombre y teléfono opcional, y devuelve su token.
*   `POST /api/v1/public/customers/auth/login`: Valida las credenciales de `username` y `password` contra la base de datos local y devuelve el token de acceso JWT.
*   `GET /api/v1/public/catalog`: Devuelve la carta sin información de negocio sensible. Requiere token de cliente.

---

## 4. Aislamiento Físico y de Privilegios

La seguridad perimetral de la API se garantiza a través de la inyección de dependencias estrictas en FastAPI:

*   **`get_current_staff_user`:** Valida que el token JWT contenga un rol de empleado administrativo/caja. Protege rutas sensibles de administración (`/api/v1/pos/sales/*`, `/api/v1/pos/inventory/*`). Un token de cliente recibirá un `403 Forbidden` inmediato si intenta acceder aquí.
*   **`get_current_customer`:** Valida que el token contenga el rol de cliente. Otorga acceso exclusivamente al portal de la carta (`/api/v1/public/catalog`) y a la información personal del cliente autenticado (`/api/v1/public/customers/me`).
