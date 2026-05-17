# Draft: Refactorización Arquitectónica - Registro de Proveedores de Eventos

Este documento describe la estrategia para desacoplar totalmente el sistema de eventos de Blackshot, pasando de un modelo de "God Object" (donde el servicio de eventos conoce a todos los demás) a un modelo de "Registro de Proveedores" (donde cada módulo es responsable de sus propios datos).

## 1. El Problema Actual (Acoplamiento)

Actualmente, `pos_core/events/service.py` contiene una función llamada `_fetch_topic_data` que utiliza una cadena masiva de `if/elif`. Esto provoca:
- **Dependencias Circulares**: El módulo de eventos debe importar Ventas, Tablas, Analíticas, Inventario e IoT.
- **Fragilidad**: Si un módulo cambia su esquema, el error suele saltar en el módulo de eventos.
- **Mantenibilidad**: Agregar un nuevo tópico de WebSocket requiere modificar el núcleo del sistema de eventos.

## 2. Solución Propuesta: Patrón Registry

Introducir un sistema de registro donde los tópicos se definan de forma dinámica.

### Componente A: El Registro (`events/registry.py`)
Un diccionario centralizado que mapea un nombre de tópico con una función proveedora.

```python
# Pseudo-código del registro
TOPIC_REGISTRY = {}

def register_provider(topic: str, func: Callable):
    TOPIC_REGISTRY[topic] = func
```

### Componente B: El Proveedor (en cada módulo)
Cada módulo (ej: `sales`) define cómo se deben ver sus datos para un broadcast.

```python
# pos_core/sales/providers.py
async def provide_kitchen_orders(db):
    orders = await get_active_orders(db)
    return [format_for_websocket(o) for o in orders]
```

## 3. Fases de Implementación

### Fase 1: Infraestructura
- Crear `pos_core/events/registry.py`.
- Refactorizar `events/service.py` para que `_fetch_topic_data` consulte el `TOPIC_REGISTRY` en lugar de usar `if/elif`.

### Fase 2: Migración por Módulos
Mover la lógica de formateo de datos (los DTOs de WebSocket) desde el servicio de eventos hacia sus respectivos dominios:
1. **Sales**: Mover `kitchen_orders` y `recent_orders`.
2. **Tables**: Mover el tópico `tables`.
3. **Analytics**: Mover `dashboard_stats`.
4. **Inventory**: Mover el tópico `inventory`.

### Fase 3: Registro Dinámico
Implementar un sistema de carga (hooks) para que cuando la aplicación FastAPI inicie, cada módulo registre sus proveedores automáticamente.

```python
# main.py o __init__.py de cada módulo
from pos_core.sales.providers import provide_kitchen_orders
register_provider("kitchen_orders", provide_kitchen_orders)
```

## 4. Beneficios Esperados

1. **Aislamiento Total**: Puedes borrar el módulo de Inventario y el sistema de WebSockets ni se entera; simplemente el tópico "inventory" deja de estar disponible.
2. **Escalabilidad**: Agregar nuevos módulos (ej: Intercom avanzado, Lealtad, Facturación) no requiere tocar una sola línea de código en el paquete `events`.
3. **Testeabilidad**: Se pueden testear los proveedores de datos de forma independiente sin levantar todo el sistema de WebSockets.

---
**Estado del Plan:** DRAFT (Pendiente de aprobación para ejecución)
**Autor:** Antigravity AI
**Fecha:** 2026-05-04
