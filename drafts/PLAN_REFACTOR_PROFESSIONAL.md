# Plan de Refactorización Profesional: Blackshot POS

Este documento detalla los puntos críticos de "deuda técnica" en el sistema y propone una hoja de ruta para elevar la calidad del código de "funcional" a "profesional y robusto".

## 1. Problemas Identificados (Deuda Técnica)

### A. Serialización Manual (El "Spaguetti" de JSON)
*   **Problema:** Actualmente, funciones como `format_order_json` construyen diccionarios a mano. Esto duplica el esfuerzo de mantenimiento: si se añade un campo a la base de datos, hay que actualizar el modelo, la función de formato y el frontend.
*   **Riesgo:** Alta probabilidad de errores `KeyError` o `AttributeError` (como el ocurrido con los timestamps).
*   **Solución:** Implementar **Pydantic Schemas (DTOs)**. Definir modelos de respuesta claros y dejar que FastAPI/Pydantic gestionen la serialización automáticamente.

### B. Acoplamiento de Responsabilidades (Servicios vs API)
*   **Problema:** Los archivos de servicios (ej. `sales/service.py`) mezclan lógica de cálculo financiero con lógica de presentación para la API.
*   **Riesgo:** El código se vuelve difícil de testear de forma aislada.
*   **Solución:** Separar la lógica puramente matemática/operativa de la lógica de "empaquetado" de datos.

### C. Gestión de Fechas (Timezones)
*   **Problema:** Aunque se ha corregido la inconsistencia naive/aware, la lógica está dispersa en múltiples `@field_serializer` y reemplazos manuales.
*   **Solución:** Crear un tipo de dato personalizado o una base de modelo que aplique la normalización UTC de forma global y transparente para todo el proyecto.

### D. Crecimiento Descontrolado de Archivos
*   **Problema:** `service.py` está acumulando funciones de ventas, reportes, gestión de ítems y auditoría.
*   **Solución:** Modularizar por sub-dominios (ej. `pos_core/sales/reports_service.py`, `pos_core/sales/order_manager.py`).

## 2. Propuesta de Refactorización

### Fase 1: Estandarización de Modelos de Respuesta (Schemas)
1.  Crear `pos_core/sales/schemas.py`.
2.  Definir `OrderRead`, `OrderItemRead`, `PaymentRead` con todas las validaciones necesarias.
3.  Eliminar `format_order_json` y usar `OrderRead.model_validate(order).model_dump()` o simplemente retornar el objeto y dejar que FastAPI use el `response_model`.

### Fase 2: Normalización de Auditoría
*   Centralizar el registro de auditoría (`AuditLog`) mediante decoradores o middleware, eliminando llamadas manuales repetitivas en cada cambio de estado de orden.

### Fase 3: Robustez de WebSocket
*   Refactorizar `trigger_broadcast` para que no dependa de funciones de "formato" manuales, sino que utilice los mismos Schemas definidos en la Fase 1, garantizando paridad total entre la API REST y el WebSocket.

---

**Estado:** Pendiente de autorización para iniciar Fase 1.
