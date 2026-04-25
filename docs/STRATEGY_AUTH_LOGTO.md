# 🛡️ Estrategia de Autenticación: Migración a Logto (Self-hosted)

Este documento detalla el plan para migrar el sistema de autenticación custom (`omni_auth`) hacia **Logto**, permitiendo un control total sobre los datos de identidad y preparación para un modelo SaaS multi-tenant.

## 1. Motivación
*   **Soberanía de Datos**: Los usuarios y sus credenciales viven en nuestra propia infraestructura (PostgreSQL gestionado por Dokploy).
*   **Open Source**: Sin dependencia de proveedores SaaS propietarios como Kinde o Auth0.
*   **Multi-tenancy Nativo**: Soporte robusto para Organizaciones (locales/cafeterías).
*   **Escalabilidad**: Sin límites de Usuarios Activos Mensuales (MAU) impuestos por licencias externas.

## 2. Pasos de Integración

### Fase 1: Despliegue en Dokploy
1.  Desplegar **PostgreSQL** para Logto.
2.  Desplegar **Logto** usando Docker.
3.  Configurar el dominio base (ej. `auth.blackshot.com`).
4.  Crear una aplicación **Traditional Web** para SvelteKit y un **API Resource** para FastAPI.

### Fase 2: SvelteKit (Frontend)
1.  Instalar `@logto/sveltekit`.
2.  Configurar `src/hooks.server.ts`:
    ```typescript
    import { handleLogto } from '@logto/sveltekit';
    import { config } from '$lib/logto-config';

    export const handle = handleLogto(config);
    ```
3.  Implementar rutas de `/login`, `/logout` y `/callback`.
4.  Obtener el `AccessToken` para las llamadas a la API.

### Fase 3: FastAPI (Backend)
1.  Implementar validación de JWT usando la URL de JWKS de Logto: `https://auth.blackshot.com/oidc/jwks`.
2.  Middleware de Autorización:
    *   Verificar `iss` (Issuer) y `aud` (Audience).
    *   Extraer `sub` (ID de usuario) y `org_ids` (Organizaciones a las que pertenece).
3.  Reemplazar las dependencias de `get_current_user` para que usen la validación de Logto.

### Fase 4: Migración de Datos
1.  Modificar la tabla `users` en la DB local para usar el ID de Logto como llave foránea.
2.  Sincronizar metadatos adicionales (nombres, roles específicos del POS) mediante Webhooks de Logto o en el primer inicio de sesión.

## 3. Configuración Multi-tenant
*   Cada local/cafetería se registrará como una **Organization** en Logto.
*   Los usuarios serán asignados a una o más organizaciones con roles específicos (Admin, Mesero, Cocina).
*   El backend filtrará todos los recursos (órdenes, inventario) usando el `organization_id` presente en el token.

## 4. Seguridad
*   Habilitar **MFA** (Multi-Factor Authentication) para cuentas de administrador.
*   Configurar **CORS** estrictos para que solo el dominio del POS pueda comunicarse con Logto.
