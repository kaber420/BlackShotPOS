# 📋 Plan: Logística de Comandas Multi-Estación (KDS)

Este plan detalla los cambios necesarios para transformar la pantalla de cocina actual en un sistema multi-estación inteligente que reconozca áreas de producción (Cocina, Barra, etc.).

## 🎯 Objetivo
Permitir que cada estación de trabajo (tablet/pantalla) se configure para un área específica, filtrando el contenido visual y restringiendo las acciones a solo lo que le compete, mejorando la coordinación en horas pico.

## 🛠️ Cambios Propuestos

### 1. Backend (Modelos y Schemas)
- **OrderItemRead:** Debe incluir el `production_area_id` (calculado desde la categoría del producto) para que el frontend no tenga que hacer búsquedas recursivas.

### 2. Frontend (Configuración de Estación)
- **Estado Global:** Añadir `currentStationAreaId` en `appState` o `posSocket`.
- **Persistencia:** Guardar la elección en `localStorage` para que la tablet "recuerde" que es la de "Barra" incluso si se recarga la página.

### 3. Interfaz KDS (`kitchen/+page.svelte`)
- **Selector de Área:** Un dropdown o tabs en el header para elegir:
    - 🟢 Todas las Áreas (Vista de Gerente).
    - ☕ Barra.
    - 🍳 Cocina / Parrilla.
- **Filtrado de Órdenes:** Si una orden no tiene ítems del área seleccionada, se oculta.

### 4. Tarjeta de Orden (`OrderCard.svelte`)
- **Items Ajenos:** 
    - Se muestran con opacidad reducida (`opacity-40`).
    - Se eliminan los botones de acción ("Empezar", "Listo").
    - Se añade una etiqueta informativa (ej: "-> Ir a Barra").
- **Items Propios:** Se muestran resaltados y con botones de acción habilitados.

### 5. Impresión Vinculada
- Al imprimir una comanda desde una estación específica, el sistema usará automáticamente la configuración de impresora (IP/Puerto) definida para esa `ProductionArea` en la base de datos.

---

## 🚦 Plan de Pruebas
1. **Configuración:** Definir 2 áreas en el admin (Cocina y Barra).
2. **Prueba Cruzada:** Crear una orden mixta.
3. **Validación de Filtro:** Verificar que en la pantalla de "Barra" solo el café es accionable.
4. **Validación de Sync:** Al marcar el café como listo en Barra, la pantalla de Cocina debe mostrarlo como "Listo" instantáneamente.
