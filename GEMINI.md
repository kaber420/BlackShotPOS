# Gemini - Project Overview: Blackshot Ecosystem

Este documento proporciona un resumen de alto nivel del ecosistema Blackshot para que los asistentes de IA puedan comprender su propósito, arquitectura y tecnologías.

## 1. Resumen del Proyecto

**Blackshot** ha evolucionado de un simple POS a un ecosistema de gestión centralizada para cafeterías. Permite operar sucursales de forma local (offline-first para ventas) mientras centraliza la administración, reportes y catálogos en un núcleo central (Central Core).

## 2. Pila Tecnológica (Tech Stack)

*   **Backend (POS & Central):**
    *   **Framework:** FastAPI (Python)
    *   **Base de Datos:** SQLite (Local para POS, Central para Central Core)
    *   **ORM:** SQLModel (sobre SQLAlchemy)
    *   **Comunicación:** SSE (Server-Sent Events) para actualizaciones en tiempo real y HTTP/REST para sincronización de datos.

*   **Frontend:**
    *   **POS Branch:** SvelteKit + Svelte 5 Runes.
    *   **Blackshot Central:** FastAPI + Jinja2 Templates + Vanilla JS/CSS (Admin Dashboard).

## 3. Arquitectura y Componentes Clave

### Estructura del Proyecto

- `pos_core/`: Lógica de negocio del POS local (inventario, ventas, gestión de mesas).
- `central_core/`: Sistema central de gestión. Maneja **Regiones**, **Sucursales**, **Catálogos Globales** y agregación de ventas.
- `bs_sync/`: Agente de sincronización que reside en el POS y empuja datos a la Central.
- `bs_frontend/`: Aplicación frontend del POS.

### Características Notables

*   **Gestión Multi-Sucursal (Central):**
    *   Organización jerárquica: Región -> Sucursal.
    *   Monitoreo de ventas en tiempo real vía SSE.
    *   Gestión de Usuarios Globales y Regionales.

*   **Catálogo Global:**
    *   Definición de productos y categorías maestras que se pueden distribuir a las sucursales.

*   **Sincronización Inteligente:**
    *   El agente `bs_sync` asegura que cada venta local se registre en la central con detalle de ítems vendidos, permitiendo auditoría y analíticas precisas.

*   **POS Operativo:**
    *   Gestión de Inventario con Recetas y Variantes.
    *   Grupos de Modificadores dinámicos.
    *   Cierres de caja (Corte Z) y auditoría de cancelaciones.

## 4. Cómo Ejecutar el Ecosistema

### Blackshot POS (Local)
1. Instalar dependencias en el root: `pip install -e .`
2. Poblar datos: `python scripts/seed_data.py`
3. Iniciar API: `blackshot`
4. Iniciar Frontend: `cd bs_frontend && npm run dev`

### Blackshot Central (Gestión)
1. Navegar a `central_core/`.
2. Instalar dependencias: `pip install -e .`
3. Poblar datos iniciales: `python seed_central.py`
4. Iniciar Central: `blackshot-central` (Corre en puerto 8001 por defecto).

### Sincronización
1. Con el entorno activo, ejecutar el agente: `python -m bs_sync.agent`