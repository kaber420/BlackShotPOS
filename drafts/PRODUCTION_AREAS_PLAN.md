# Plan: Áreas de Producción (Cocina vs Bar vs Otros)

## Resumen
Actualmente el sistema tiene los modelos de base para `ProductionArea`, pero no se están utilizando plenamente en el frontend ni en la lógica de impresión. El objetivo es permitir que el sistema separe las comandas por área, permitiendo tener una pantalla/impresora para la cocina y otra para la barra.

## Cambios Propuestos

### 1. Modelos y API (Backend)
- Los modelos ya existen en `pos_core/catalog/models.py`.
- Asegurar que los routers de `catalog` permitan el CRUD de `ProductionArea`.
- Verificar que el endpoint de `OrderItem` incluya la información del área de producción (vía Categoría).

### 2. Panel de Administración (Frontend)
- **[NUEVA VISTA]** `/admin/production-areas`: Pantalla para crear y configurar áreas (ej. Cocina, Barra, Repostería).
- **[MODIFICAR]** Formulario de Categorías: Permitir asignar una Categoría a un Área de Producción específica.

### 3. Pantalla de Cocina / KDS (Frontend)
- **[MODIFICAR]** `src/routes/(app)/kitchen/+page.svelte`:
    - Añadir un selector (Dropdown) en la parte superior para elegir el área (ej. "Mostrar todo", "Solo Barra", "Solo Cocina").
    - Filtrar los tickets mostrados basándose en la selección.
    - Persistir la selección en `localStorage` para que cada pantalla "recuerde" qué área debe atender.

### 4. Sistema de Impresión (Backend)
- **[MODIFICAR]** `pos_core/printing/service.py`:
    - Al recibir una orden para "imprimir en cocina", el servicio debe agrupar los ítems por su `production_area`.
    - En lugar de enviar un solo ticket a una impresora global, debe enviar cada grupo a la IP/Puerto configurada en su respectiva `ProductionArea`.

## Plan de Ejecución Sugerido

1. **Investigación**: Verificar si ya existen endpoints de API para `ProductionArea`.
2. **Backend**: Implementar la lógica de agrupación en el servicio de impresión.
3. **Frontend Admin**: Crear la interfaz para gestionar las áreas.
4. **Frontend Kitchen**: Implementar el filtro dinámico en la pantalla de cocina.

## Preguntas Abiertas
- ¿Deseas que un ticket se imprima en múltiples áreas si contiene productos de ambas, o prefieres tickets separados totalmente independientes? (Lo ideal es tickets separados).
- ¿La configuración de impresoras USB/Bluetooth también se manejará por área o solo las de red?
