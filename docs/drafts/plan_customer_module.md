# Plan de Implementación: Módulo de Clientes Seguros y Portal Público

Este plan aborda la solicitud de extender el módulo de clientes actuales para soportar autenticación (login), funcionalidades de fidelidad, una arquitectura segura para un futuro Portal de Clientes Público, y **cifrado estricto de datos personales**.

## 1. Análisis de la Arquitectura Propuesta (Aislamiento de POS)

Tienes **absoluta razón**. Es una excelente decisión separar el Portal de Clientes (Público) del POS Core (Local). 

**¿Por qué es la mejor estrategia?**
1. **Resiliencia y Alta Disponibilidad (Offline-First):** El POS Core debe ser invulnerable a caídas de internet o ataques externos. Si el portal público sufre un ataque DDoS, el POS de la cafetería seguirá vendiendo y funcionando sin interrupciones.
2. **Seguridad (Aislamiento):** Al no exponer el POS local a internet público, reduces drásticamente la superficie de ataque. Las operaciones críticas quedan protegidas en la red local de la sucursal.
3. **Identidad Global (Omnicanalidad):** Si un cliente tiene puntos de fidelidad, la "fuente de la verdad" debe vivir en el **Central Core** (o una API Pública dedicada en la nube), no aislada en una sola sucursal.

### Arquitectura Recomendada
*   **Customer Portal (Frontend Web/App):** Una aplicación exclusiva para clientes (separada).
*   **Central Core (Backend Cloud):** El Customer Portal se conecta *únicamente* al Central Core para iniciar sesión, revisar historial, ver puntos y crédito.
*   **POS Core (Local):** Se sincroniza con el Central Core mediante el agente `bs_sync`. Permite buscar al cliente (vía código, QR, o datos parciales descifrados localmente) para aplicar puntos incluso sin internet.

---

## 2. Seguridad y Cifrado de Datos Personales (PII)

Para cumplir con el requerimiento de mantener privados los datos en caso de una vulneración de la base de datos (Data Breach), implementaremos **Cifrado en Reposo (Encryption at Rest) a nivel de aplicación**.

*   **Librería:** Usaremos la librería estándar `cryptography` (Fernet) de Python.
*   **Mecanismo:** Los campos `name`, `email` y `phone` se cifrarán antes de guardarse en la base de datos y se descifrarán al leerse en la memoria de la aplicación.
*   **Gestión de Claves:** La clave de cifrado simétrico (Master Key) se inyectará mediante Variables de Entorno (`.env`) y no estará guardada en el código ni en la base de datos. Si roban la base de datos (SQLite/PostgreSQL), los atacantes solo verán cadenas de texto ilegibles.

---

## 3. Cambios Propuestos en los Modelos de Datos

### A. En `pos_core/customers/models.py`
El modelo actual será actualizado para incorporar el cifrado de datos sensibles y campos de autenticación.

#### [MODIFY] `pos_core/customers/models.py`
*   `username: Optional[str] = Field(default=None, index=True, unique=True)`
*   `hashed_password: Optional[str] = Field(default=None)`
*   
*   **Datos Personales Cifrados (PII):**
    *   `encrypted_name: str`
    *   `encrypted_email: Optional[str]`
    *   `encrypted_phone: Optional[str]`
    *   `encrypted_telegram_id: Optional[str]`
    *   *(Nota: Se usarán `@property` getters/setters para manejar el cifrado).*
*   
*   **Fidelidad y Finanzas:**
    *   `credit_balance: float = Field(default=0.0)`
    *   `points: int = Field(default=0)`
    *   `tier: str = Field(default="regular")` # ej. bronze, silver, gold
*   
*   **Historial y Analíticas Agregadas:**
    *   `total_spent: float = Field(default=0.0)`
    *   `total_visits: int = Field(default=0)`
    *   `last_visit_at: datetime`
*   
*   **Preferencias y Consentimientos:**
    *   `accepts_marketing_email: bool = Field(default=False)`
    *   `accepts_marketing_telegram: bool = Field(default=False)`
    *   `custom_metadata: dict = Field(default={}, sa_type=JSON)` # Para guardar alergias, productos favoritos, etc.

### B. En `central_core/models.py`
#### [NEW] Modelo `GlobalCustomer`
```python
class GlobalCustomer(SQLModel, table=True):
    id: str = Field(primary_key=True) # Mismo UUID del POS
    username: Optional[str] = Field(default=None, unique=True, index=True)
    hashed_password: Optional[str] = None
    
    # Datos Personales Cifrados (PII)
    encrypted_name: str
    encrypted_email: Optional[str] = None
    encrypted_phone: Optional[str] = None
    encrypted_telegram_id: Optional[str] = None
    
    # Fidelidad y Finanzas
    points: int = Field(default=0)
    credit_balance: float = Field(default=0.0)
    tier: str = Field(default="regular")
    
    # Historial y Analíticas Agregadas
    total_spent: float = Field(default=0.0)
    total_visits: int = Field(default=0)
    last_visit_at: Optional[datetime] = None
    favorite_branch_id: Optional[str] = None
    
    # Preferencias y Consentimientos
    accepts_marketing_email: bool = Field(default=False)
    accepts_marketing_telegram: bool = Field(default=False)
    custom_metadata: dict = Field(default={}, sa_type=JSON)
    
    is_active: bool = Field(default=True)
```

---

## 4. Búsqueda con Datos Cifrados (Trade-off)

Al cifrar `name`, `email` y `phone` con un algoritmo seguro, **no podemos usar búsquedas SQL directas** como `WHERE name LIKE '%Juan%'`. 

**Estrategias de Búsqueda Recomendadas en POS:**
1.  **Identificador Directo:** Buscar por `username` exacto o escanear un Código QR (que contiene el UUID).
2.  **Búsqueda Determinista (Opcional):** Si se requiere buscar por teléfono exacto, se puede guardar un hash (SHA256) del teléfono como columna indexada. Esto permite buscar coincidencias exactas (`WHERE phone_hash = '...'`) sin revelar el número real en texto plano.

## 5. Fases de Ejecución Futura

1.  **Fase 1: Infraestructura de Seguridad.** Crear el módulo de criptografía, definir claves de entorno y probar cifrado/descifrado.
2.  **Fase 2: Modelos de Base de Datos.** Refactorizar `pos_core` y `central_core` para usar los campos `encrypted_X` y agregar atributos de crédito/puntos.
3.  **Fase 3: Rutas de Autenticación.** Crear endpoints de login para clientes en el Central Core.
4.  **Fase 4: Sincronización.** Ajustar el agente `bs_sync` para subir/bajar clientes globales.
