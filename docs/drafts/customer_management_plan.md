# Documento de Diseño Técnico (RFC): Arquitectura de Gestión de Clientes y Carta Segura (Offline-First)

---

## 1. Introducción y Filosofía de Diseño

El propósito de este documento es definir la especificación técnica para separar las operaciones del Portal de Clientes y la gestión de identidad del backend de facturación física (**POS Core**). 

### 1.1 El Principio Offline-First
BlackShot está concebido para ser **Offline-First**. Una sucursal debe poder vender café, imprimir comandas y operar de manera local aunque no tenga conexión a internet o no esté registrada en un "Central Core". Por lo tanto, el sistema local debe ser autónomo y no delegar su lógica a servidores centrales en la nube a menos que sea opcional.

### 1.2 Análisis de Vulnerabilidades y Malas Prácticas del Sistema Actual
- **Riesgo Operativo (DDoS):** Actualmente, el POS local (`pos_core` corriendo en `main.py`) expone endpoints públicos a internet. Si un atacante ejecuta una denegación de servicio contra el inicio de sesión público, el bucle de eventos de FastAPI y la CPU de la computadora local se saturarán, impidiendo que el cajero físico cobre o que la cocina reciba comandas.
- **Hack del "Cliente de Bridge":** En `pos_core/customers/public_router.py`, el método `customer_login` auto-crea un registro falso (`CustomerCreate`) cada vez que un teléfono desconocido intenta loguearse. Esto expone la base de datos a inyecciones de registros basura, corrompe el conteo de clientes reales y representa un riesgo de seguridad severo.
- **Exposición de Datos Confidenciales:** El endpoint `/api/v1/pos/public/catalog` utiliza `.model_dump()` de SQLModel directamente sobre la base de datos transaccional, enviando al internet campos privados como `recipe_markdown` (recetas secretas) y `stock` (niveles de inventario físico).

---

## 2. Especificación de la Arquitectura Desacoplada

Para neutralizar estos riesgos y preservar la autonomía local, se establece una división física de servicios, base de datos e internet.

```mermaid
sequenceDiagram
    autonumber
    actor Cliente as Portal Svelte (Internet)
    participant PortalAPI as Servicio de Clientes (Puerto 8002)
    database ClientDB as DB Clientes (Aislada)
    participant POSCore as POS Core (Puerto 8000 / Red Local)
    database POSDB as DB POS (PostgreSQL Local)

    Cliente->>PortalAPI: POST /auth/register (Teléfono, Nombre, PIN)
    PortalAPI->>ClientDB: Guardar cliente (PIN Hasheado)
    PortalAPI-->>Cliente: Retorna JWT (Autenticación Completada)

    Cliente->>PortalAPI: GET /catalog (Header: Authorization Bearer)
    Note over PortalAPI: Valida JWT del Cliente
    PortalAPI->>POSCore: GET /api/v1/pos/public/catalog (HTTP Interno)
    POSCore->>POSDB: Consultar Categorías y Productos Activos
    POSDB-->>POSCore: Datos de productos
    Note over POSCore: Sanitiza datos (Censura Recetas y Stock)
    POSCore-->>PortalAPI: JSON Sanitizado (Categorías y Productos)
    PortalAPI-->>Cliente: Retorna Menú limpio y listo
```

### 2.1 POS Core (Entorno de Red Local y Facturación)
- **Base de Datos:** PostgreSQL (`blackshot_db`). Almacena inventario real, recetas secretas, compras, mesas y ventas físicas.
- **Seguridad de Red:** Bloqueado del internet público. Las peticiones externas son rechazadas por el cortafuegos perimetral del negocio. Solo acepta tráfico local (Wi-Fi de la cafetería) y peticiones originadas por la IP segura del *Servicio de Clientes*.

### 2.2 Servicio de Clientes (Backend Expuesto a Internet)
- **Tecnología:** Una aplicación independiente de FastAPI corriendo en el puerto `8002` (o desplegada en un VPS básico en la nube).
- **Base de Datos Aislada (`customer_portal.db`):** Base de datos SQLite o PostgreSQL aislada que solo almacena información del cliente para mitigar el radio de impacto ante un ciberataque:
  - Identificador único (UUID)
  - Teléfono (encriptado)
  - Nombre
  - PIN / Password (hasheado)
  - Puntos de lealtad acumulados
- **Función de Intermediario (Proxy Dinámico):** No guarda catálogos ni menús. Cuando un cliente autenticado solicita el menú, este backend realiza una llamada `fetch` interna y rápida al `pos_core` local (Puerto 8000), recupera el menú fresco y se lo devuelve al cliente.

---

## 3. Especificación de Base de Datos y Modelos

### 3.1 Base de Datos de Clientes (Servicio de Clientes - Puerto 8002)
```python
from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime

class PortalCustomer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: str = Field(index=True, unique=True) # UUID generado al registrarse
    phone: str = Field(unique=True, index=True) # Teléfono encriptado o texto plano limpio
    hashed_pin: str # PIN hasheado con bcrypt/argon2
    name: str # Nombre del cliente
    loyalty_points: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
```

### 3.2 Base de Datos del POS (POS Core - Puerto 8000)
El POS no guarda credenciales web. Solo tiene una tabla espejo de clientes locales para registrar a quién pertenece una venta:
```python
class Customer(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    uuid: str = Field(index=True, unique=True) # Mismo UUID sincronizado
    phone: str = Field(unique=True, index=True)
    name: str
    is_active: bool = Field(default=True)
```

---

## 4. Diseño del API y Endpoints

### 4.1 Servicio de Clientes (Puerto 8002)

#### `POST /api/v1/portal/auth/register`
- **Request:**
  ```json
  {
    "phone": "5551234567",
    "name": "Juan Pérez",
    "pin": "1234"
  }
  ```
- **Procesamiento:**
  1. Validar que el teléfono no esté registrado.
  2. Generar UUID único.
  3. Hashear el PIN.
  4. Guardar en `PortalCustomer`.
  5. Lanzar un hilo asíncrono o petición en segundo plano para notificar al POS Local (`POST /api/v1/pos/customers/sync`) que existe un nuevo cliente para que lo guarde en su tabla local de lealtad.
- **Response (JWT):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer"
  }
  ```

#### `POST /api/v1/portal/auth/login`
- **Request:**
  ```json
  {
    "phone": "5551234567",
    "pin": "1234"
  }
  ```
- **Procesamiento:**
  1. Buscar cliente por teléfono. Si no existe, devolver `401 Unauthorized` (eliminando la auto-creación).
  2. Verificar hash del PIN. Si falla, devolver `401 Unauthorized`.
- **Response:** Retorna JWT de acceso.

#### `GET /api/v1/portal/catalog`
- **Headers:** `Authorization: Bearer <JWT>`
- **Procesamiento:**
  1. Validar firma y caducidad del JWT.
  2. Realizar petición interna: `GET http://localhost:8000/api/v1/pos/public/catalog`.
  3. Retornar el JSON exacto recibido del POS.

---

## 5. Plan de Trabajo e Implementación Detallado

### Fase 1: Limpieza del Backend Local (`pos_core`)
1. **Archivo `pos_core/customers/public_router.py`**:
   - Borrar por completo el `mock_customer_in` y la auto-creación.
   - Si no existe el cliente, levantar una excepción clara:
     ```python
     raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="El teléfono no está registrado. Regístrate en el portal.")
     ```
2. **Sanitización del Endpoint de Catálogo Público (`pos_core/inventory/public_catalog_router.py`)**:
   - Asegurar que la purga de `recipe_markdown` y `stock` sea estricta.

### Fase 2: Construcción del Nuevo Servicio de Clientes (Puerto 8002)
1. Crear el directorio `bs_customer_api/`.
2. Escribir `bs_customer_api/main.py` con FastAPI, levantando los endpoints de `/auth/register`, `/auth/login` y `/catalog` descritos en la Sección 4.1.
3. Configurar su base de datos SQLite dedicada `customer_portal.db` para almacenar las credenciales web.
4. Implementar la llamada HTTP On-Demand hacia el puerto `8000` de `pos_core` para el catálogo.

### Fase 3: Integración del Portal de Clientes (Svelte)
1. **Página de Registro:** Crear `bs_customer_portal/src/routes/register/+page.svelte` con formulario de alta.
2. **Página de Login:** Modificar `bs_customer_portal/src/routes/login/+page.svelte` para que apunte al puerto `8002` de internet.
3. **Página del Menú:** Configurar `bs_customer_portal/src/routes/menu/+page.svelte` para consumir el endpoint `/api/v1/portal/catalog` del puerto `8002` enviando el token en los headers.

---

## 6. Pruebas y Validación de Seguridad
- **Prueba de Evasión de Registro:** Intentar loguearse con un número inexistente. Debe devolver `401 Unauthorized` de inmediato y no generar ninguna fila fantasma en las bases de datos.
- **Prueba de Fuga de Datos:** Consultar `/api/v1/portal/catalog` y auditar el JSON para confirmar que las llaves `recipe_markdown` y `stock` están ausentes en cada producto.
- **Prueba de Aislamiento:** Apagar el Servicio de Clientes (Puerto 8002) y simular un ataque. Confirmar que la API del POS local (Puerto 8000) responde a las solicitudes de venta física instantáneamente.
