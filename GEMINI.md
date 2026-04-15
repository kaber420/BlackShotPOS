# Gemini - Project Overview: Blackshot POS

Este documento proporciona un resumen de alto nivel del proyecto Blackshot POS para que los asistentes de IA puedan comprender su propósito, arquitectura y tecnologías.

## 1. Resumen del Proyecto

**Blackshot POS** es un sistema de Punto de Venta (POS) para cafeterías. Su objetivo es gestionar las operaciones diarias, desde la toma de pedidos y la gestión de inventario hasta el procesamiento de pagos y la visualización de reportes. El proyecto está evolucionando desde un MVP hacia una solución robusta y segura, con planes para una arquitectura SaaS.

## 2. Pila Tecnológica (Tech Stack)

*   **Backend:**
    *   **Framework:** FastAPI (Python)
    *   **Base de Datos:** SQLite
    *   **ORM / Data Mapper:** SQLModel (sobre SQLAlchemy)
    *   **Autenticación:** Un módulo custom llamado `omni_auth` está actualmente en uso, con un plan de migración a **Kinde** para mayor seguridad y escalabilidad (ver `docs/STRATEGY_AUTH_KINDE.md`).
    *   **Tiempo Real:** Actualmente usa una mezcla de polling y un WebSocket simple, con un plan de migración a una arquitectura Pub/Sub unificada (ver `drafts/websocket_pubsub_plan.md`).

*   **Frontend:**
    *   **Framework:** SvelteKit
    *   **Gestión de Estado:** Svelte 5 Runes (`$state`)
    *   **Librerías Clave:** `marked` para renderizar Markdown (recetas).

*   **Despliegue:**
    *   El servidor se inicia con `uvicorn`.
    *   Existen planes para contenerizar la aplicación usando Docker (`ROADMAP_V2.md`).

## 3. Arquitectura y Características Clave

### Estructura del Proyecto

El proyecto sigue una estructura de monorepo:
- `pos_core/`: Lógica de negocio principal del POS (inventario, ventas, etc.).
- `omni_auth/`: Módulo de autenticación y gestión de usuarios (planificado para ser reemplazado por Kinde).
- `bs_frontend/`: La aplicación frontend en SvelteKit.
- `scripts/`: Utilidades para migración de base de datos y sembrado de datos (seeding).
- `docs/`: Documentación estratégica y de planificación.
- `drafts/`: Planes de implementación detallados para nuevas características.

### Características Notables

*   **Gestión de Inventario y Menú:**
    *   Manejo de Productos, Categorías, Ingredientes y Recetas.
    *   Soporte para **Variantes de Producto** (ej. Chico, Mediano, Grande) con precios y recetas específicas.
    *   **Grupos de Modificadores** (ej. "Tipo de Leche") para personalizar los pedidos.
    *   Campo `recipe_markdown` en los productos para almacenar instrucciones de preparación con formato.

*   **Roles y Permisos Granulares:**
    *   El sistema utiliza un modelo híbrido: los **Roles** (`admin`, `manager`, `waiter`, etc.) actúan como *presets* de permisos.
    *   Los permisos individuales pueden ser sobreescritos por usuario y se almacenan en un campo `metadata` JSON en la tabla `users`.
    *   Esto permite una flexibilidad operativa máxima (ej. un mesero que puede o no cobrar).
    *   La lógica de resolución de permisos está centralizada en `pos_core/roles.py`.

*   **Órdenes y Operaciones:**
    *   Flujo completo de creación, envío a cocina, actualización de estado y pago de órdenes.
    *   Pantalla de Cocina (KDS) que se actualizará en tiempo real.
    *   Gestión de mesas.

## 4. Roadmap y Dirección Futura

El `ROADMAP_V2.md` define las siguientes fases clave:

1.  **Seguridad y Despliegue:** Migrar la autenticación a **Kinde**, endurecer la API y crear una configuración Docker para un despliegue reproducible y seguro.
2.  **Control Operativo:** Implementar cierres de caja (reporte Z), un panel de analíticas de ventas y un sistema de auditoría para cancelaciones.
3.  **Fidelización de Clientes:** Crear un sistema de puntos y recompensas basado en una PWA, sin depender de servicios de terceros.
4.  **Experiencia de Usuario:** Mejorar la comunicación en tiempo real con WebSockets, añadir soporte para impresoras térmicas (ESC/POS) y optimizar la UI para dispositivos móviles.

## 5. Cómo Ejecutar el Proyecto

1.  Asegurar que las dependencias de Python y Node.js estén instaladas.
2.  Configurar las variables de entorno en un archivo `.env`.
3.  Ejecutar las migraciones de la base de datos si es necesario (ej. `scripts/migrate_add_recipe.py`).
4.  Poblar la base de datos con datos de prueba usando `scripts/seed_data.py`.
5.  Iniciar el backend de FastAPI a través del CLI: `python -m pos_core.cli`.
6.  Navegar al directorio `bs_frontend` e iniciar el servidor de desarrollo de SvelteKit.