# Plan de Arquitectura: Portal de Clientes (Customer Portal)

Este documento analiza las diferentes opciones arquitectónicas para la creación del **Portal de Clientes** de Blackshot, donde los clientes podrán iniciar sesión, ver sus puntos de lealtad, historial de visitas y gestionar su saldo a favor.

---

## 1. Opciones Arquitectónicas

Existen tres caminos principales para implementar la interfaz de usuario (UI) del portal de clientes, cada uno con implicaciones directas en seguridad, mantenimiento y resiliencia.

### Opción A: Aplicación Separada (Standalone App) - *Recomendada*
Crear un nuevo proyecto frontend (ej. `bs_customer_portal` en SvelteKit o React) que viva en un repositorio o carpeta separada. Esta aplicación se comunica **exclusivamente con la API del Central Core**.

*   **Pros:**
    *   **Máxima Seguridad:** El código, las dependencias y el despliegue están 100% aislados del POS local y del Dashboard Administrativo.
    *   **Escalabilidad:** Si miles de clientes entran al mismo tiempo, solo se escala el portal y el Central Core, sin afectar la operación local de las cafeterías.
    *   **Flexibilidad:** Permite convertirse fácilmente en una PWA (Progressive Web App) o aplicación móvil nativa a futuro.
*   **Contras:**
    *   Requiere configurar un nuevo entorno de despliegue (hosting como Vercel, Netlify o un contenedor Docker separado).

### Opción B: Compartido con el POS Local (`bs_frontend`)
Añadir rutas públicas (ej. `/cliente/*`) dentro del proyecto SvelteKit actual que usan los cajeros.

*   **Pros:**
    *   Reutilización máxima de componentes de UI y estilos (Tailwind/CSS).
    *   Cero configuración adicional de repositorios.
*   **Contras:**
    *   **Riesgo Crítico de Seguridad:** Implica exponer el servidor del POS (que debe operar en la red local de la sucursal) a Internet. 
    *   **Rendimiento:** Un pico de tráfico de clientes revisando sus puntos podría alentar el sistema de caja y la toma de comandas, afectando la operación en tiempo real.
    *   Contradice la premisa de "Offline-First" y aislamiento de sucursales.

### Opción C: Unido al Central Core (Módulo Integrado)
Servir el portal directamente desde el proyecto `central_core`, ya sea usando plantillas (Jinja2) o integrando un frontend unificado junto con el Dashboard de Administración.

*   **Pros:**
    *   Una sola base de código para todo lo que está "en la nube".
    *   Latencia mínima entre el frontend y la base de datos `GlobalCustomer`.
*   **Contras:**
    *   Mezcla dominios de negocio (B2C para clientes vs B2B para administradores).
    *   Si un ataque vulnera el portal de clientes, el panel de administración central queda potencialmente expuesto.

---

## 2. Comparativa y Veredicto

| Criterio | Opción A (Separado) | Opción B (POS Frontend) | Opción C (Central Core) |
| :--- | :---: | :---: | :---: |
| **Seguridad de Sucursales** | Alta (Aislado) | Muy Baja (Expuesto) | Alta (Aislado) |
| **Aislamiento de Admins** | Alto | N/A | Bajo |
| **Esfuerzo de Configuración** | Medio | Bajo | Medio |
| **Preparado para App Móvil** | Sí | No | Difícil |

**Veredicto:** La **Opción A (Separado)** es la única que cumple estrictamente con los estándares de seguridad de Blackshot y mantiene la invulnerabilidad del POS local. El portal debe ser un frontend "tonto" que consume la API segura del `Central Core`.

---

## 3. Plan de Implementación (Basado en Opción A)

Si se aprueba el enfoque separado, las siguientes fases guiarán el desarrollo:

### Fase 1: Preparación del Backend (Central Core)
1.  Crear router de autenticación JWT público en `central_core/api/customers_auth.py` (`/api/customers/login`, `/api/customers/me`).
2.  Desarrollar endpoints de solo lectura para el portal: `/api/customers/transactions`, `/api/customers/loyalty`.
3.  Configurar CORS estricto en el Central Core para permitir solo el dominio del nuevo portal.

### Fase 2: Creación del Proyecto Frontend
1.  Inicializar `bs_customer_portal` usando SvelteKit y **pnpm** (siguiendo las normativas del proyecto).
2.  Configurar un sistema de diseño visual (UI) orientado al consumidor final (más visual, dinámico y "premium" que el panel de administración).
3.  Implementar el flujo de Autenticación (Login con Teléfono/Usuario + Password o envío de OTP).

### Fase 3: Integración de Funcionalidades Clave
1.  **Dashboard Principal:** Mostrar el `loyalty_code` en formato **Código QR** renderizado dinámicamente en pantalla.
2.  **Billetera (Wallet):** Visualización de `points` y `credit_balance`.
3.  **Historial:** Lista de últimas compras sincronizadas desde las sucursales.

### Fase 4: Despliegue
1.  Crear `Dockerfile` multi-stage para el portal de clientes.
2.  Desplegar el frontend en la nube (ej. Vercel o Docker Server) apuntando las variables de entorno al dominio público del `Central Core`.
