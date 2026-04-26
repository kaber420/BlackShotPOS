# 📋 Plan de Implementación Maestro: Autenticación Distribuida (FastAPI Users)

Este documento detalla los pasos técnicos exactos para la migración de `omni_auth` a `FastAPI Users`, garantizando que la arquitectura sea compatible con el sistema de **Bridge Distribuido** y **Gerentes Regionales**, según lo definido en la [Estrategia de Autenticación](file:///home/kaber420/Documentos/proyectos/blackshot-refactor/drafts/STRATEGY_LOCAL_DISTRIBUTED_AUTH.md).

---

## ⚠️ Consideraciones Críticas

> [!IMPORTANT]
> **Eliminación de `omni_auth/`**: Se borrará el módulo completo. No se migrarán datos de `omni_auth.db` (SQLite) a menos que se solicite un script de migración. Se asume un re-sembrado de usuarios (re-seeding).

> [!TIP]
> **Preparación RS256**: Aunque usaremos un secreto simple para empezar, la estructura de archivos en `pos_core/auth/` estará lista para inyectar llaves públicas/privadas para el Bridge sin cambiar la lógica de negocio.

---

## 🛠️ Fase 1: Limpieza y Dependencias

1.  **Actualizar `pyproject.toml`**:
    - Añadir: `fastapi-users[sqlalchemy]>=12.1.2`, `passlib[argon2]`, `python-jose[cryptography]`.
    - Eliminar: `omni_auth` de `tool.setuptools.packages`.
2.  **Eliminar Código Antiguo**:
    - Borrar físicamente el directorio `omni_auth/`.
    - En `main.py`, eliminar:
      ```python
      from omni_auth.api import router as auth_router # ELIMINAR
      ...
      app.include_router(auth_router, prefix="/api", tags=["Auth"]) # ELIMINAR
      ```

---

## 🏗️ Fase 2: Motor de Identidad (Backend)

### 2.1 Modelos de Datos (`pos_core/auth/models.py`)
Definiremos un modelo `User` que herede de `SQLModel` y el mixin de `FastAPI Users`:

```python
class User(SQLModel, SQLAlchemyBaseUserTable[UUID], table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    # Campos base (email, hashed_password, is_active, etc. vienen de SQLAlchemyBaseUserTable)
    
    # --- CAMPOS BRIDGE (DISTRIBUIDO) ---
    organization_id: str = Field(index=True, description="ID de la sucursal/organización")
    is_remote: bool = Field(default=False, description="¿Es un usuario de gestión regional/remota?")
    external_id: Optional[str] = Field(default=None, description="ID del usuario en el Panel Central")
    metadata: dict = Field(default_factory=dict, sa_column=Column(JSON))
```

### 2.2 Base de Datos y Manager (`pos_core/auth/db.py` & `manager.py`)
- Configurar `SQLAlchemyUserDatabase` usando la sesión asíncrona de `pos_core/database.py`.
- Implementar `UserManager` heredando de `BaseUserManager`.
- Configurar el hashing **Argon2id** (ganador de PHC) para máxima seguridad.

### 2.3 Estrategia y Transporte (`pos_core/auth/backend.py`)
- **Transporte**: `CookieTransport` con `cookie_name="bs_auth"`, `cookie_httponly=True`, `cookie_samesite="lax"`.
- **Estrategia**: `JWTStrategy` con un secreto seguro y tiempo de expiración de 24h.

---

## 🔗 Fase 3: Integración y Rutas (`pos_core/auth/router.py`)

Se crearán los siguientes endpoints unificados bajo el prefijo `/api/auth`:

1.  **Auth (JWT/Cookie)**: `/login` y `/logout`.
2.  **Register**: `/register` (solo habilitado para administradores locales).
3.  **Users**: `/me` (perfil actual) y `/{id}` (gestión por administradores).

**Modificación en `main.py`**:
```python
from pos_core.auth.router import auth_router, user_router
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(user_router, prefix="/api/users", tags=["Users"])
```

---

## 🖥️ Fase 4: Frontend (SvelteKit)

1.  **`bs_frontend/src/lib/api.ts`**:
    - Inyectar `credentials: 'include'` en el objeto de configuración de `fetch` para que el navegador envíe la cookie `bs_auth` automáticamente.
2.  **Gestión de Estado (Svelte 5)**:
    - Crear un archivo `src/lib/stores/auth.svelte.ts` que use `$state` para mantener el `currentUser`.
    - Implementar lógica de "Auto-login" que verifique `/api/users/me` al cargar la aplicación.

---

## ✅ Plan de Verificación (Checklist)

- [ ] **Seguridad Pasiva**: Confirmar en DevTools que la cookie `bs_auth` no es accesible vía JavaScript (`HttpOnly`).
- [ ] **Hash Argon2**: Verificar en SQLite que las contraseñas guardadas empiecen con `$argon2id$`.
- [x] **Distributed Ready**: Verificar en DB que un usuario puede tener `is_remote=True` y un `external_id`.
- [ ] **Persistence**: Cerrar la pestaña del navegador y volver a entrar; el usuario debe seguir logueado.

---

## 📐 Decisiones de Arquitectura Tomadas

### 1. Separación Staff vs. Clientes (Fidelización)
Se ha decidido que la tabla `User` gestionada por `FastAPI Users` será **exclusiva para el personal operativo** (meseros, gerentes, admins). Los clientes externos para el sistema de puntos se manejarán en una tabla `Customer` independiente en fases posteriores. Esto garantiza:
- **Seguridad**: Un fallo en la PWA de clientes no compromete el acceso al POS.
- **Rendimiento**: Login de staff ultra rápido al tener una tabla pequeña.

### 2. Identidad Híbrida para el Bridge
Para soportar **Gerentes Regionales** sin depender 100% de internet:
- Cada sucursal es "Soberana": Tiene su propia tabla de usuarios.
- El Panel Central "Habilita" gerentes enviando un comando al Bridge.
- La sucursal crea un registro local con `is_remote=True`.
- Esto permite que el gerente se loguee **incluso si la sucursal se queda sin internet** (Local-First).
