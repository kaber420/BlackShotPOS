# Plan de Refactorización: Módulo de Inventario

El archivo `src/routes/(app)/inventory/+page.svelte` ha superado las 1,000 líneas de código, lo que dificulta su mantenimiento y viola el principio de responsabilidad única. Este plan detalla la estrategia para atomizar el módulo en componentes especializados.

## 1. Objetivos

*   **Modularidad:** Separar la lógica de negocio de la presentación.
*   **Mantenibilidad:** Reducir el tamaño del archivo principal a un numero manejable de lineas.    
*   **Estandarización:** Crear componentes reutilizables para modales y vistas.

## 2. Nueva Arquitectura de Componentes

Crearemos el directorio `src/lib/components/inventory/` para alojar los nuevos componentes.

### 2.1 Modales Extraídos

1.  **`IngredientModal.svelte`**:
    *   **Responsabilidad:** Creación y edición de materia prima (`Ingredient`).
    *   **Props:** `isOpen`, `editingIngredient`, `categories`, `onClose`, `onSave`.
2.  **`InventoryAdjustmentModal.svelte`**:
    *   **Responsabilidad:** Registro de mermas, entradas por compra y ajustes de stock.
    *   **Props:** `isOpen`, `ingredient`, `onClose`, `onSave`.
3.  **`InventoryCategoryModal.svelte`**:
    *   **Responsabilidad:** Gestión del catálogo de categorías de inventario.
    *   **Props:** `isOpen`, `onClose`, `onRefresh`.
4.  **`ModifierGroupModal.svelte`**:
    *   **Responsabilidad:** Gestión de grupos de opciones (ej. "Tipos de Leche").
    *   **Props:** `isOpen`, `group`, `onClose`, `onSave`.
5.  **`ModifierModal.svelte`**:
    *   **Responsabilidad:** Configuración avanzada de una opción individual (vínculo con ingrediente, precio extra, etc.).

### 2.2 Componentes de Vista (Opcional)

1.  **`InventoryGrid.svelte`**: Renderizado de las tarjetas en modo cuadrícula.
2.  **`InventoryList.svelte`**: Renderizado de la tabla de materiales.

## 3. Estrategia de Implementación

### Fase 1: Preparación (Estructura)
*   Crear el directorio `src/lib/components/inventory/`.
*   Identificar las dependencias de estado (stores o runes) que deben compartirse.

### Fase 2: Extracción de Modales (Prioridad Alta)
*   Mover el HTML y la lógica de cada modal del archivo principal a su nuevo componente.
*   Simplificar el archivo principal reemplazando los modales inline por las nuevas etiquetas de componentes.

### Fase 3: Limpieza de Lógica
*   Mover las constantes (`UNIT_OPTIONS`, `MEASURE_TYPES`) a un archivo de configuración o al componente correspondiente.
*   Centralizar las llamadas a servicios si es posible.

## 4. Beneficios Esperados

*   **Carga más rápida:** Svelte puede optimizar mejor componentes pequeños.
*   **Depuración sencilla:** Es más fácil localizar un error en un archivo de 100 líneas que en uno de 1,000.
*   **Colaboración:** Permite que varios desarrolladores trabajen en distintas partes del módulo sin conflictos.

---
**Estado:** Propuesto
**Responsable:** Antigravity AI
