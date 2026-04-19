# Plan: Registro de Eficiencia y Estadísticas de Meseros

Este plan detalla los cambios necesarios para medir la carga de trabajo y la rapidez de los meseros, permitiendo identificar quiénes son los más activos y eficientes.

## Cambios Propuestos

### 1. Base de Datos (`pos_core/sales/models.py`)

Se agregarán campos de rastreo y marcas de tiempo para medir el ciclo de vida de cada orden.

- **`Order` Model:**
    - `waiter_uuid: Optional[str]` - ID del creador.
    - `waiter_name: Optional[str]` - Nombre del creador (para auditoría rápida).
    - `preparing_at: Optional[datetime]` - Inicio de cocina.
    - `ready_at: Optional[datetime]` - Fin de cocina (Listo).
    - `delivered_at: Optional[datetime]` - Entrega final.

- **`OrderItem` Model:**
    - `delivered_by_uuid: Optional[str]` - Quién entregó este plato.
    - `delivered_by_name: Optional[str]`
    - `preparing_at: Optional[datetime]`, `ready_at: Optional[datetime]`, `delivered_at: Optional[datetime]` (Para medir eficiencia por platillo individual).

### 2. Lógica de Negocio (`pos_core/sales/service.py` & `router.py`)

- **Creación:** Al crear la orden, se inyectará el `user` proveniente del token JWT en los campos `waiter_uuid/name`.
- **Transiciones de Estado:**
    - Al pasar de `PENDING` a `PREPARING`, se grabará `preparing_at`.
    - Al pasar a `READY`, se grabará `ready_at`.
    - Al pasar a `DELIVERED`, se grabará `delivered_at` y se registrará el `user` que realizó la acción en el campo `delivered_by`.

### 3. Analíticas (`pos_core/sales/analytics_router.py`)

Se implementará un nuevo endpoint `@router.get("/waiters/performance")` que calculará:
- **Carga de Trabajo:** Órdenes totales por mesero.
- **Eficiencia de Servicio:** Tiempo promedio entre que la cocina marca `READY` y el mesero marca `DELIVERED` (cuánto tarda el mesero en llevar la comida).
- **Ventas Totales:** Suma de ventas cerradas por mesero.

### 4. Frontend (Dashboard)

- **Nueva Sección:** "Desempeño de Equipo".
- **Visualización:** Una tabla o tarjetas con:
    - Ranking de actividad (más órdenes).
    - Ranking de rapidez (menor tiempo de entrega).
    - Total de ventas generadas hoy.

---

## Verificación Plan

### Automatizada
- Pruebas unitarias para asegurar que los timestamps se guardan correctamente al cambiar estados.

### Manual
1. Abrir sesión con el usuario "Mesero A".
2. Crear una orden.
3. Desde Cocina, marcar como Listo.
4. "Mesero A" marca como Entregado.
5. Verificar en el Panel de Analíticas que el tiempo de entrega y la orden se asignaron correctamente a "Mesero A".
