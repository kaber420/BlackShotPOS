# Plan Detallado: Bus de Eventos Unificado (Fase 4)

Este documento detalla la reestructuración del sistema de notificaciones de BlackShotPOS para alcanzar una arquitectura de **Bus de Eventos Unificado**. El objetivo es separar la lógica de negocio de la lógica de comunicación, eliminando redundancias y optimizando el uso de la base de datos.

## 1. El Concepto: Separación de Responsabilidades

Actualmente, el módulo de ventas (`sales/router.py`) está "contaminado" con lógica de notificaciones IoT. Sabe cómo mapear estados de órdenes a strings amigables para el TablePad y gestiona sus propias tareas de fondo.

**La nueva arquitectura propone:**
- **Módulo de Ventas:** Se limita a procesar transacciones y emitir un evento genérico de "datos actualizados".
- **Módulo de Eventos:** Actúa como un orquestador inteligente que consume los datos una sola vez y decide qué enviar a cada plataforma (Web vs IoT).

## 2. Cambios Arquitectónicos

### A. Bus de Eventos (pos_core/events/service.py)
Se implementará un despachador dual dentro de `trigger_broadcast`. 

1.  **Lectura Única:** Se realiza una única consulta a la base de datos para obtener el estado actual (ej. lista de mesas).
2.  **Mapeo IoT Dinámico:** 
    - Se añade una función `_map_data_to_iot(topic, data)` que contiene las reglas de traducción (ej. `OrderStatus.READY` -> `"LISTO"`).
    - Esta función extrae solo los campos necesarios para el ESP32 (ID, estatus, progreso, nombre corto).
3.  **Broadcast Simultáneo:** El sistema envía los datos completos al `pos_broadcaster` y los datos ligeros al `iot_broadcaster` en el mismo ciclo de ejecución.

### B. Limpieza de Ventas (pos_core/sales/router.py)
Se eliminará toda la lógica de "parche" que intentaba notificar al IoT manualmente.

1.  **Eliminación de `notify_iot_item`:** Esta función interna desaparece por completo.
2.  **Simplificación de Endpoints:** Los endpoints de actualización de estado ya no llamarán a `trigger_iot_broadcast`. Simplemente llamarán a `trigger_standard_broadcasts()`.
3.  **Reducción de Latencia:** Al no crear tareas de fondo (`asyncio.create_task`) que abren nuevas sesiones de BD, el tiempo de respuesta del API mejora y se eliminan riesgos de bloqueos en SQLite.

### C. Repositorio (pos_core/sales/repository.py)
- Se optimizará `OrderItemRepository` para que la carga de relaciones (modificadores) sea opcional, permitiendo que el Bus de Eventos obtenga datos básicos de forma aún más rápida cuando sea posible.

## 3. Beneficios Esperados

- **Zero Redundant Queries:** Las notificaciones IoT pasan de costar N consultas a costar **CERO** consultas adicionales (reutilizan la lectura de la Web).
- **Single Source of Truth:** Los estados y traducciones se gestionan en un solo lugar (`events/service.py`).
- **Escalabilidad:** Añadir un nuevo tipo de dispositivo (ej. una pantalla para clientes) solo requiere añadir un mapeo en el Bus de Eventos, sin tocar la lógica de ventas.

## 4. Pasos de Implementación

1.  **Fase de Infraestructura:** Actualizar `events/service.py` con la lógica de mapeo y despacho dual.
2.  **Fase de Limpieza:** Eliminar código redundante en `sales/router.py`.
3.  **Fase de Optimización:** Ajustar el repositorio de ventas para cargas condicionales.
4.  **Fase de Verificación:** Pruebas de integración asegurando que un cambio en cocina se refleje instantáneamente tanto en la Tablet del mesero como en el TablePad de la mesa.
