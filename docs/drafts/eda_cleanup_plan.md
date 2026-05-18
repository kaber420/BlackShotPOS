# RFC: Limpieza Final de Aislamiento de Dominio (EDA)

> **Fecha:** 2026-05-17  
> **Autor:** Auditoría automatizada  
> **Estado:** Pendiente de ejecución

## 1. Contexto

Se realizó una auditoría completa de los 10 dominios de negocio en `pos_core` para verificar que respeten los límites de dominio tras la migración a Event-Driven Architecture (EDA). Se analizaron todos los imports cruzados, llamadas directas a servicios ajenos y mutaciones fuera de dominio.

## 2. Resultado de la Auditoría

| Módulo | Estado | Detalle |
|---|---|---|
| Sales | ✅ Limpio | Publica eventos, no toca otros dominios |
| Inventory | ✅ Limpio | Solo reacciona a eventos, lectura en listeners |
| Kitchen | ✅ Limpio | Providers de solo lectura + listeners EDA |
| Accounting | ✅ Limpio | Queries de solo lectura para reportes de turno |
| Customers | ✅ Limpio | Cero dependencias cruzadas |
| Communications | ✅ Limpio | Solo referencia a `ProductionArea` (shared kernel) |
| Catalog | ✅ Aceptable | Shared kernel con inventory/kitchen |
| Analytics | ⚠️ Transversal | Diseñado para leer de todos los dominios (correcto) |
| **Audit** | 🔴 Violación | Router con endpoints de cancelación que pertenecen a Sales |
| **IoT** | 🔴 Violación | WebSocket llama directamente a Sales y Tables |

### Nota sobre Catalog

El CRUD de `ProductionArea` está en `catalog/production_router.py` pero el modelo vive en `kitchen/models.py`. Es una decisión de diseño (las áreas de producción se configuran junto con el catálogo). No es una violación grave, pero se documenta aquí para consideración futura.

### Nota sobre Analytics

Analytics es un módulo de **lectura transversal** por diseño. Importa modelos de `sales`, `kitchen`, `accounting` y `catalog` pero **nunca muta datos** de ningún dominio. Solo hace queries SQL de agregación para dashboards y reportes. Esto es correcto.

---

## 3. Violaciones a Resolver

### 3.1 Audit → Sales (Llamada directa a servicio ajeno)

**Archivo:** `pos_core/audit/router.py`

**Problema:** El router de auditoría contiene dos endpoints que llaman directamente al servicio de ventas:

```python
# audit/router.py
from pos_core.sales.models import Order, OrderStatus               # L9
from pos_core.sales.services import order_action_service            # L12

# L43 — LLAMADA DIRECTA
order = await order_action_service.cancel_order(db, order_id, ...)

# L70 — LLAMADA DIRECTA
item = await order_action_service.cancel_order_item(db, order_id, item_id, ...)
```

Cancelar una orden es responsabilidad del dominio de **Sales**, no de Audit. Audit solo debe *observar* y registrar eventos.

**Plan:**

1. **Mover** los endpoints `POST /orders/{order_id}/cancel` y `POST /orders/{order_id}/items/{item_id}/cancel` de `audit/router.py` → `sales/router.py`.
2. **Limpiar** `audit/router.py` eliminando las importaciones de `pos_core.sales.services` y los modelos de ventas. Audit queda solo con `GET /audits`.
3. **Verificar** que el listener EDA existente (`audit/listeners.py` escuchando `sales.order_cancelled` y `sales.item_cancelled`) siga registrando la auditoría automáticamente.
4. **Actualizar** el frontend para que apunte a las nuevas rutas bajo `/api/sales/...` en lugar de `/api/audits/...`.

### 3.2 IoT → Sales + Tables (Llamadas directas a servicios ajenos)

**Archivo:** `pos_core/iot/websocket_handler.py`

**Problema 1 — `clear_table`:** El WebSocket IoT llama directamente a `tables.vacate_table_service()`:

```python
# iot/websocket_handler.py L82-84
elif action == "clear_table":
    from pos_core.tables.service import vacate_table_service
    await vacate_table_service(db, table_id)
```

**Problema 2 — `sync_orders`:** IoT llama directamente a `sales.get_orders()`:

```python
# iot/websocket_handler.py L8-10
from pos_core.sales.services.order_lifecycle_service import get_orders
from pos_core.sales.schemas import OrderRead
from pos_core.sales.models import OrderStatus
```

**Plan:**

#### a) Desacoplar `clear_table`
1. En `websocket_handler.py`, reemplazar la llamada directa por publicación de evento:
   ```python
   elif action == "clear_table":
       await event_bus.publish("iot.clear_table_requested", {
           "table_id": table_id,
           "device_id": device_id
       })
   ```
2. Crear un listener en `pos_core/tables/listeners.py` que escuche `iot.clear_table_requested` y ejecute `vacate_table_service`.
3. Eliminar el import de `pos_core.tables.service` del handler de IoT.

#### b) Desacoplar `sync_orders`
1. Crear un `topic_provider` dedicado (ej. `iot_table_orders`) en `pos_core/iot/` o reusar el sistema de broadcast existente para que IoT reciba datos de órdenes activas sin importar directamente de Sales.
2. Alternativa intermedia: si la complejidad es alta, documentar esta dependencia como **lectura aceptable** (similar a como Kitchen lo hace en `recent_orders` provider) y mover el import dentro de la función para reducir el acoplamiento a nivel de módulo.
3. Eliminar los imports de nivel superior de `pos_core.sales.*` en `websocket_handler.py`.

---

## 4. Archivos Afectados

| Archivo | Acción |
|---|---|
| `pos_core/audit/router.py` | Eliminar endpoints de cancelación, limpiar imports |
| `pos_core/sales/router.py` | Recibir los endpoints de cancelación con `reason` |
| `pos_core/iot/websocket_handler.py` | Reemplazar llamadas directas por eventos |
| `pos_core/tables/listeners.py` | Agregar listener para `iot.clear_table_requested` |
| `bs_frontend/` | Actualizar rutas de API si cambian los paths |

## 5. Verificación

- [ ] Los endpoints de cancelación funcionan desde su nueva ubicación en Sales.
- [ ] El listener de auditoría sigue registrando cancelaciones automáticamente.
- [ ] El comando `clear_table` desde TablePad IoT sigue liberando la mesa correctamente vía evento.
- [ ] El sync de órdenes IoT sigue funcionando sin imports directos de Sales (o con import aceptable documentado).
- [ ] Ejecutar el flujo completo: crear orden → agregar items → pagar → verificar que todos los listeners reaccionen.
