# Plan de Corrección: Órdenes del Turno Activo

Este documento detalla la corrección para el problema de desaparición de órdenes en el POS.

## Análisis del Problema
Actualmente, el sistema filtra y oculta las órdenes del turno activo en cuanto son marcadas como PAGADAS y ENTREGADAS. Esto rompe la funcionalidad del "Historial" y de la vista de "Todas" las órdenes para el operador.

## Código a Modificar
Archivo: `pos_core/kitchen/providers.py`

**Lógica actual (Líneas 125-130):**
Excluye órdenes que cumplen ambos estados (`PAID` y `DELIVERED`).

```python
# FILTRO DE VISIBILIDAD: Desaparece si está PAGADA y ENTREGADA
is_paid = o.status == OrderStatus.PAID
is_all_delivered = all(s == "DELIVERED" for s in item_statuses) if item_statuses else True

if not (is_paid and is_all_delivered):
    data.append(order_dict)
```

## Solución Propuesta
Eliminar el filtro restrictivo para permitir que todas las órdenes recuperadas por el servicio (que ya están limitadas al turno activo) se envíen al frontend.

**Lógica nueva:**
```python
# Se eliminan los checks de is_paid e is_all_delivered
data.append(order_dict)
```

## Resultado Esperado
- **Filtro "Historial":** Mostrará correctamente todas las órdenes del turno que ya han sido liquidadas (`PAID` y `DELIVERED`).
- **Filtro "Todas":** Mostrará el resumen completo de la operación del turno sin exclusiones.
- **Filtros Operativos (Pendientes/Cocina):** Seguirán funcionando con normalidad, pero sin el riesgo de que las órdenes se pierdan del estado global del frontend al cambiar de estado.
- **Consistencia:** Se garantiza que la interfaz del POS siempre tenga la misma información que la base de datos para el turno activo.
- **Privacidad:** Se mantiene la restricción de que un operador no pueda ver órdenes de turnos ajenos (otros `shift_id`).
