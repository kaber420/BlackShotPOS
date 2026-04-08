# 🛡️ Estrategia de Autenticación: Migración a Kinde

Este documento detalla el plan para migrar el sistema de autenticación custom (`omni_auth`) hacia **Kinde**, con el fin de preparar el sistema para ser expuesto a internet de forma segura (SaaS ready).

## 1. Motivación
*   **Seguridad**: Delegar el manejo de contraseñas, recuperación de cuentas y sesiones a un proveedor especializado.
*   **Compliance**: Cumplir con estándares de seguridad sin desarrollo adicional.
*   **Escalabilidad**: Manejar miles de usuarios con el plan gratuito (hasta 10k MAU).

## 2. Pasos de Integración

### Fase 1: Configuración en Kinde
1.  Crear cuenta en [Kinde.com](https://kinde.com).
2.  Configurar "Blackshot POS" como una **SvelteKit Application**.
3.  Configurar el backend como una **API Service** vinculada.
4.  Definir los Roles y Permisos (`admin`, `manager`, `staff`).

### Fase 2: SvelteKit (Frontend)
1.  Instalar `@kinde-oss/kinde-auth-sveltekit`.
2.  Configurar `src/hooks.server.ts`:
    ```typescript
    import { sessionHooks } from '@kinde-oss/kinde-auth-sveltekit';
    export const handle = sessionHooks;
    ```
3.  Protección de rutas usando `event.locals.kindeAuth`.
4.  Inyectar el `Access Token` en las llamadas a la API de FastAPI.

### Fase 3: FastAPI (Backend)
1.  Instalar `python-jose[cryptography]` para validación de JWT.
2.  Implementar middleware/dependencia de seguridad:
    *   Descargar las llaves públicas de Kinde (JWKS).
    *   Validar la firma, el `issuer` y el `audience`.
3.  Reemplazar `verify_omni_token` por la nueva validación.

### Fase 4: Limpieza
1.  Eliminar carpeta `omni_auth/`.
2.  Eliminar `omni_auth.db`.
3.  Migrar referencias a IDs de usuario en `pos_database.db` para usar el `sub` (ID único) de Kinde.

## 3. Seguridad Adicional
*   **CORS**: Configurar CORS estrictos en FastAPI para permitir solo el dominio de producción del frontend.
*   **HSTS**: Habilitar Strict Transport Security en el servidor una vez se despliegue con SSL.
