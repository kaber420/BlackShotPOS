# Especificación Técnica: Optimización de Inventario BlackShot

Este documento define la arquitectura y los procedimientos técnicos para la optimización del sistema de inventario. Se centra en la integridad transaccional, el manejo de concurrencia y la sincronización de datos de bajo nivel.

## 1. Integridad Transaccional y Rendimiento (Backend)

### Patrón de Sesión Atómica en `stock_service.py`
Se eliminará el acoplamiento de persistencia en las funciones internas para evitar "Partial Commits".
- **Refactorización:** 
    - Las funciones `_subtract_from_batches` y `_deplete_recursive` recibirán la `AsyncSession` pero **no** ejecutarán `commit()`.
    - `process_inventory_depletion` actuará como el único controlador de la transacción, ejecutando un único `await session.commit()` al final.
    - Se implementará un bloque `try/except` global que ejecute `await session.rollback()` ante cualquier error durante la recursión de recetas, garantizando que el stock no se descuente parcialmente si la orden falla al final.

### Consolidación de Notificaciones (SSE/WebSocket)
- **Acción:** El `trigger_broadcast("inventory")` se moverá fuera del bucle de ingredientes. Se disparará una única vez por cada venta procesada exitosamente, reduciendo el tráfico de red y el re-renderizado innecesario en los clientes POS.

---

## 2. Manejo de Concurrencia (Bloqueos de Base de Datos)

### Implementación de Pessimistic Locking
Para evitar colisiones de stock en entornos multi-caja (Race Conditions):
- **Acción:** Se utilizará la cláusula `with_for_update()` en las consultas de SQLModel/SQLAlchemy al leer ingredientes para descuento.
- **Detalle:** `stmt = select(Ingredient).where(Ingredient.id == id).with_for_update()`. Esto bloquea la fila específica hasta que el `commit` final se complete, obligando a otras transacciones a esperar su turno, garantizando cálculos exactos.

---

## 3. Consistencia de Datos y Reconciliación de Lotes

### Algoritmo de Ajuste por Conteo Físico (`delta` handling)
El ajuste de stock debe mantener la paridad absoluta entre el total y los lotes.
- **Cálculo del Delta:** `delta = nuevo_stock - stock_actual`.
- **Lógica de Ajuste Negativo (Merma/Faltante):**
    1. Obtener lotes activos ordenados por `expiration_date` (FEFO) y `arrival_date`.
    2. Iterar restando la cantidad del delta. 
    3. Si un lote se agota, marcar `current_quantity = 0` y continuar con el siguiente hasta cubrir el delta.
- **Lógica de Ajuste Positivo (Sobrante):**
    1. Crear un registro en `IngredientBatch` marcado como "Ajuste de Sistema".
    2. Asignar fecha de caducidad nula o según política de la categoría.
- **Validación Final:** Una restricción de software (o trigger de DB) debe verificar que `SUM(batches.current_quantity) == ingredient.current_stock`.

---

## 4. Frontend y Experiencia de Usuario (Svelte 5)

### Optimistic UI Updates
Mejorar la percepción de velocidad sin comprometer la integridad:
- **Estado Local:** Al realizar un ajuste, el `$state` del componente se actualiza inmediatamente.
- **Gestión de Errores:** Si la API falla, se utiliza un sistema de `revert` para restaurar el estado previo y se notifica al usuario mediante un Toast de error.

#
- **Filtros Operativos:** Implementar un selector de "Estado de Insumo" con opciones: `Bajo Stock`, `Próximo a Vencer`, `Sin Stock`.

---

## 5. Casos de Borde y Excepciones
- **Recetas Circulares:** Implementar un detector de profundidad máxima (max depth = 5) en la recursión de recetas para evitar loops infinitos.
- **Stock Negativo:** Crear un flag global `ALLOW_NEGATIVE_STOCK`. Si es `False`, la función de depleción lanzará una excepción `InsufficientStockError` que abortará toda la transacción de venta.
