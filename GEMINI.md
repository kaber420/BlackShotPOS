# Gemini - Project Overview: Blackshot Ecosystem

> [!IMPORTANT]
> **REGLA DE ORO:** El asistente de IA tiene **estrictamente prohibido** realizar cambios o ediciones en el código fuente sin la autorización explícita del usuario. Siempre se debe presentar un plan y esperar aprobación.

> [!IMPORTANT]
> **PROHIBICIÓN ABSOLUTA DE NPM:** El uso de `npm` para cualquier interacción, instalación o ejecución de scripts en el frontend está **estrictamente prohibido**. Se debe utilizar obligatoria y exclusivamente **`pnpm`** (ej. `pnpm install`, `pnpm dev`). Esto es de vital importancia para garantizar la seguridad del árbol de dependencias y la consistencia en auditorías automatizadas de IA. No utilizar `npm` bajo ninguna circunstancia.

Este documento proporciona un resumen de alto nivel del ecosistema Blackshot para que los asistentes de IA puedan comprender su propósito, arquitectura y tecnologías actuales.

---

## 1. Resumen del Proyecto

**Blackshot** ha evolucionado de un simple POS a un ecosistema de gestión centralizada para cafeterías y sucursales. Permite operar sucursales de forma local (**offline-first** para ventas) mientras centraliza la administración, auditoría, reportes financieros y catálogos globales en un núcleo centralizado (**Central Core**).

---

## 2. Pila Tecnológica (Tech Stack)

*   **Backend (POS & Central Core):**
    *   **Entorno:** Python 3 (uso obligatorio de `.venv`)
    *   **Framework:** FastAPI (Python)
    *   **Base de Datos:** PostgreSQL para el POS (usando `asyncpg` para operaciones asíncronas) y SQLite para el Central Core.
    *   **ORM:** SQLModel (sobre SQLAlchemy)
    *   **Comunicación:** SSE (Server-Sent Events) para actualizaciones en tiempo real y HTTP/REST para sincronización de datos robusta.

*   **Frontend:**
    *   **POS Branch:** SvelteKit + Svelte 5 Runes.
    *   **Gestor de Paquetes:** **`pnpm` (Obligatorio, prohibido npm)**.
    *   **Blackshot Central:** FastAPI + Jinja2 Templates + Vanilla JS/CSS (Admin Dashboard).

---

## 3. Arquitectura y Componentes Clave

### Estructura del Proyecto

- `pos_core/`: Lógica de negocio del POS local (inventario, ventas, mesas, caja chica).
    - `pos_core/events/`: Bus de eventos central (`bus.py`) que implementa una arquitectura orientada a eventos (**EDA**) para el desacoplamiento total y comunicación reactiva y asíncrona entre módulos (Sales, Audit, IoT, Accounting).
    - `pos_core/accounting/`: Módulo de contabilidad local que incluye la gestión completa de la **Caja Chica (Petty Cash)**.
- `central_core/`: Sistema centralizado de gestión para administrar **Regiones**, **Sucursales**, **Catálogos Globales** y agregación de analíticas de ventas.
- `bs_sync/`: Agente de sincronización seguro que reside en el POS y empuja datos estructurados a la Central.
- `bs_frontend/`: Aplicación frontend moderna del POS en SvelteKit.
- `tests/`: Pruebas unitarias, de integración y de flujo del sistema, no se usa pytest.
- `migrations/`: Scripts de migración manual y control de versiones de bases de datos.
- `scripts/`: Utilidades, sembrado de datos iniciales y automatización.
    - `scripts/seeds/`: Scripts de sembrado de datos iniciales (`seed_data.py`, `seed_central.py`).
    - `scripts/tools/`: Herramientas de diagnóstico y simuladores de hardware/red.

### Características Notables y Módulos Recientes

*   **Arquitectura Orientada a Eventos (EDA):**
    *   Implementación de un Event Bus en el backend que elimina las dependencias duras y acoplamiento directo entre dominios de negocio (ej. Ventas no depende directamente de Cocina o Inventario, sino que reacciona a eventos emitidos).

*   **Módulo de Caja Chica (Petty Cash):**
    *   Permite control detallado de flujos manuales de dinero (ingresos y gastos) a través de categorías estructuradas.
    *   Trazabilidad completa: asocia de forma auditable la identidad del usuario del sistema responsable de cada movimiento.
    *   Integración financiera total en el reporte de **Corte Z** y en reportes de turnos históricos.

*   **Seguridad NKEY & Desacoplamiento de Directorios:**
    *   Autenticación robusta basada en **NKEY** para el agente de sincronización `bs_sync` que conecta de forma segura el POS y Central Core.
    *   Aislamiento físico y lógico estricto de las carpetas de datos de Central y Sucursales Locales, evitando cualquier colisión de directorios.

*   **Soporte de Impresión Térmica (ESC/POS):**
    *   Integración directa para la impresión automática de tickets de venta y comandas en la cocina mediante protocolos ESC/POS sobre hardware local o de red.

*   **Configuración de Red y CORS Dinámico:**
    *   **Inyección Dinámica de IP:** Al arrancar, el backend (`main.py`) detecta automáticamente la IP local activa en la red y la añade a los hosts permitidos (`ALLOWED_HOSTS`) y a los orígenes de CORS (`ALLOWED_ORIGINS`).
    *   **Alineación Dinámica de Puertos:** Resuelve el CORS y Trusted Hosts utilizando dinámicamente los puertos reales configurados en el `.env` (`PORT` y `FRONTEND_PORT`), junto con fallbacks de desarrollo (`5173`, `5174`), sin hardcodear puertos de producción y eliminando la necesidad de reconfigurar archivos manuales si cambia la IP local de red.

*   **Gestión Multi-Sucursal (Central):**
    *   Organización jerárquica: Región -> Sucursal.
    *   Monitoreo de ventas en tiempo real vía SSE.
    *   Gestión de Usuarios Globales y Regionales.

*   **Catálogo Global:**
    *   Definición de productos y categorías maestras que se distribuyen controladamente a las sucursales locales.

---

## 4. Cómo Ejecutar el Ecosistema

### Blackshot POS (Local)

1. **Activar entorno virtual:**
   ```bash
   source .venv/bin/activate
   ```
2. **Instalar dependencias del Backend:**
   ```bash
   pip install -e .
   ```
3. **Poblar datos de prueba iniciales:**
   ```bash
   python scripts/seeds/seed_data.py
   ```
4. **Iniciar la API local:**
   ```bash
   blackshot run
   # O si deseas ejecutar con el agente de sincronización activo:
   blackshot run sync
   ```
5. **Instalar dependencias del Frontend (⚠️ USAR ÚNICAMENTE PNPM):**
   ```bash
   cd bs_frontend
   pnpm install
   ```
6. **Iniciar el Frontend:**
   ```bash
   pnpm dev
   ```

### Blackshot Central (Gestión Centralizada)

1. **Navegar a la carpeta central:**
   ```bash
   cd central_core/
   ```
2. **Instalar dependencias:**
   ```bash
   pip install -e .
   ```
3. **Poblar base de datos de Central Core:**
   ```bash
   python ../scripts/seeds/seed_central.py
   ```
4. **Iniciar Central Core:**
   ```bash
   blackshot-central
   # Se ejecuta en http://localhost:8001 por defecto.
   ```

### Sincronización

1. **Iniciar el agente sincronizador de forma manual:**
   Con el entorno virtual activo:
   ```bash
   python -m bs_sync.agent
   ```