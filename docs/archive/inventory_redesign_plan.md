# Plan de Rediseño de Inventario y Estandarización de UI

Este documento detalla la estrategia para mejorar el sistema de inventario de BlackShotPOS, introduciendo la categorización de materiales y estandarizando los patrones de búsqueda, filtrado y visualización.

## 1. Objetivos

*   **Categorización Flexible:** Permitir al usuario clasificar materiales (Insumos, Desechables, etc.) para un mejor control.
*   **Eficiencia Operativa:** Implementar buscador y filtros rápidos.
*   **Escalabilidad:** Añadir paginación para manejar grandes volúmenes de insumos.
*   **UX Premium:** Ofrecer la opción de alternar entre vista de Cuadrícula (visual) y Lista (detallada/compacta).

## 2. Cambios en el Backend (Core)

### 2.1 Modelo de Datos (`pos_core/inventory/models.py`)
Añadiremos el campo `category` a la base de los ingredientes.
```python
category: str = Field(default="Insumo", index=True)
```

### 2.2 Migración de Base de Datos
Crearemos un script de migración manual (`migrations/migrate_ingredient_category.py`) que:
1. Verifique si la columna `category` existe mediante `PRAGMA table_info`.
2. Ejecute `ALTER TABLE ingredient ADD COLUMN category VARCHAR DEFAULT 'Insumo'`.
3. Verifique la integridad de los datos post-migración.

### 2.3 Servicios y API
*   **Parámetros de Query:** El endpoint `GET /ingredients` aceptará:
    *   `search`: Filtro por coincidencia parcial en nombre (ILIKE/contains).
    *   `category`: Filtro exacto por clase.
    *   `limit`: Cantidad de registros por página (default 20).
    *   `offset`: Salto de registros para paginación.
*   **Respuesta:** Devolverá un objeto con `{ items: [...], total: 100, page: 1, pages: 5 }`.

## 3. Cambios en el Frontend (UI/UX)

### 3.1 Gestión de Categorías (Clases)
*   **Input Inteligente:** En el modal de creación/edición, el campo "Categoría" usará un componente de autocompletado que sugiera clases ya existentes (ej. "Lácteos", "Desechables") para mantener el orden, pero permitirá escribir nuevas.

### 3.2 Herramientas de Navegación y Búsqueda
*   **Buscador Superior:**
    *   Ubicación: Parte superior derecha de la sección.
    *   Funcionalidad: Filtrado instantáneo conforme se escribe (debounce de 300ms).
    *   Botón de limpieza (X) integrado.
*   **Filtros de Categoría:**
    *   Fila de "Píldoras" (chips) horizontales con scroll.
    *   Opción "Todos" siempre al inicio.
    *   Contador de elementos por categoría (ej. "Desechables (12)").

### 3.3 Visualización Dual (Grid vs List)
*   **Selector de Vista:** Un toggle minimalista junto al buscador.
*   **Vista Cuadrícula (Grid):**
    *   Tarjetas con nombre grande, unidad y stock resaltado.
    *   Indicador visual de progreso (Stock Actual vs Mínimo).
    *   Badge de advertencia si el stock es bajo o hay caducidad cercana.
*   **Vista Lista (Table):**
    *   Columnas: Nombre, Clase, Stock, Unidad, Mínimo, Estado (Badge).
    *   Acción rápida: Botón de "Ajuste rápido" directamente en la fila.

### 3.4 Paginación Detallada
*   **Selector de Cantidad:** El usuario podrá elegir ver **10, 20 o 50** elementos por página.
*   **Controles:** 
    *   Botones de "Primero", "Anterior", "Siguiente" y "Último".
    *   Indicador de estado: "Mostrando 1-20 de 150 materiales".
    *   La paginación se mantendrá sincronizada con los filtros y la búsqueda.

## 4. Próximos Pasos

Una vez validado este patrón en el Inventario, se procederá a replicarlo en:
1. **Gestión de Menú (Productos):** Añadir filtros por categoría de venta y buscador de SKUs.
2. **Historial de Órdenes:** Filtrar por fecha, cajero o estado (Pagada/Cancelada).
3. **Logs de Auditoría:** Búsqueda por actor o tipo de evento.

---
**Estado:** Borrador (Draft) - Detallado
**Fecha:** 4 de Mayo, 2026
**Responsable:** Antigravity AI
