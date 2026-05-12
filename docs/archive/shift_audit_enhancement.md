# Plan de Mejora: Auditoría de Turnos (Detalle de Órdenes)

**Estado:** Borrador / Pendiente de Aprobación
**Responsable:** Antigravity AI
**Fecha:** 11 de Mayo, 2026

## 1. Contexto y Objetivos
Actualmente, el reporte de auditoría de turnos (`Corte de Caja`) muestra un resumen financiero y una lista de órdenes. Sin embargo, para auditar qué se vendió exactamente, el usuario debe consultar las órdenes por separado o confiar en los totales globales.

El objetivo es permitir que el administrador vea el **desglose de productos** (incluyendo variantes y modificadores) directamente en la tabla de órdenes del reporte de turno, manteniendo una interfaz limpia mediante un sistema de expansión bajo demanda.

## 2. Requerimientos
- **Backend**: El endpoint de reporte de turno debe incluir los ítems de cada orden con sus relaciones (`producto`, `variante`, `modificadores`).
- **Frontend**: 
    - Agregar un botón de "Ver Detalle" o un icono de expansión en cada fila de la tabla de órdenes.
    - Mostrar una sub-fila o panel expandible con la lista de artículos.
    - El detalle debe especificar: Cantidad, Nombre del Producto, Variante (ej. Grande/Chico) y Modificadores (ej. Leche de Almendras).

## 3. Implementación Técnica

### Backend (`pos_core/accounting/service.py`)
Se modificará la función `get_shift_report` para cargar los ítems de las órdenes usando `selectinload` para optimizar el rendimiento y evitar el problema de N+1 consultas.

### Frontend (`bs_frontend/src/routes/(app)/admin/shifts/[id]/+page.svelte`)
Se implementará un estado reactivo (`expandedOrders`) para gestionar qué filas están abiertas. Se utilizarán componentes de Svelte 5 (Runes) para una reactividad fluida.

## 4. Diseño de Interfaz (UX)
- La tabla principal se mantiene idéntica para no saturar la vista.
- Al expandir, se muestra una lista con estilo "minimalista" y premium, alineada con el diseño actual de BlackShot.
- Se incluirán indicadores visuales (badges) para variantes y modificadores para una lectura rápida.

## 5. Próximos Pasos
1. Implementación de los cambios en el servicio de contabilidad (Backend).
2. Actualización de la vista de auditoría en el frontend.
3. Validación de datos con órdenes reales que contengan modificadores.
