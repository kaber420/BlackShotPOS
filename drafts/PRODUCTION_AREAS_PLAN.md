# Plan: Áreas de Producción (Cocina vs Bar vs Otros)

## Resumen
Actualmente el sistema tiene los modelos de base para `ProductionArea`, pero no se están utilizando plenamente. El objetivo es permitir que el sistema separe las comandas por área, permitiendo tener pantallas o impresoras específicas para la cocina, barra, etc.

Se busca una flexibilidad total: poder asignar áreas por **Categoría** (para configuración rápida) y por **Producto** (para excepciones específicas).

## Lógica de Asignación (Jerarquía)
Para determinar a qué área va un ítem de la orden:
1.  **Prioridad 1 (Producto):** Si el producto tiene un `production_area_id` definido, se usa ese.
2.  **Prioridad 2 (Categoría):** Si el producto no tiene área, se usa el `production_area_id` de su categoría.
3.  **Default:** Si ninguno tiene, se asigna a un área por defecto (ej. "General" o "Cocina").

## Cambios Propuestos

### 1. Modelos y API (Backend)
- **[MODIFICAR]** `pos_core/catalog/models.py`:
    - Agregar `production_area_id: Optional[int]` a `ProductBase`.
    - Actualizar `ProductRead` para incluir el área.
    - Asegurar que `OrderItem` en las respuestas de la API pueda resolver el área final (calculada).
- **[Asegurar]** Routers de `catalog` para CRUD completo de `ProductionArea`.

### 2. Panel de Administración (Frontend)
- **[NUEVA VISTA]** `/admin/production-areas`: Gestión de áreas (Nombre, IP Impresora, Tipo).
- **[MODIFICAR]** Formulario de Categorías: Selector de área de producción.
- **[MODIFICAR]** Formulario de Productos: Selector de área de producción (opcional, actúa como override).

### 3. Pantalla de Cocina / KDS (Frontend)
- **[MODIFICAR]** `src/routes/(app)/kitchen/+page.svelte`:
    - Añadir un selector en la parte superior para elegir el área de esta pantalla (ej. "Barra").
    - Filtrar los tickets/ítems basándose en el área calculada del producto.
    - Persistir la selección en `localStorage`.

### 4. Sistema de Impresión (Backend)
- **[MODIFICAR]** `pos_core/printing/service.py`:
    - Al procesar un ticket de cocina, agrupar los `OrderItems` por su área de producción final.
    - Generar y enviar un ticket independiente a cada impresora configurada por área.

## Plan de Ejecución Sugerido

1.  **Migración de Base de Datos**: Añadir el campo a la tabla de productos.
2.  **Backend CRUD**: Refinar endpoints de áreas y productos.
3.  **Frontend Admin**: Implementar la configuración de áreas en categorías y productos.
4.  **Lógica de Negocio**: Implementar la función de "resolución de área" (Product > Category).
5.  **Frontend KDS**: Implementar los filtros por área.

## Preguntas Abiertas
- ¿Deseas que un mismo producto pueda ir a DOS áreas simultáneamente (ej. Cocina y Barra)? (Actualmente el plan asume 1:1).
- ¿Si un ticket tiene productos de Barra y Cocina, el mesero recibe un aviso de que saldrán por separado?
- ¿La configuración de impresoras debe incluir soporte para múltiples copias (ej. una para cocina y otra para el mesero)?

