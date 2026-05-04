# Roadmap de Optimización Backend: BlackShotPOS

Este documento divide la optimización del backend en fases lógicas para una implementación segura y progresiva.

## Fase 1: Cimentación de Datos (Índices)
*Objetivo: Preparar la base de datos para consultas rápidas y búsquedas eficientes.*

- [x] **Indexación de Catálogo:**
    - `Product.category_id`: Acelera el filtrado por categoría.
    - `Product.is_active`: Optimiza la carga del menú operativo.
    - `Category.production_area_id`: Mejora el ruteo a impresoras/KDS.
- [x] **Indexación de Ventas:**
    - `Order.status`: Vital para la pantalla de cocina (KDS) y pedidos recientes.
    - `Order.table_id`: Rapidez al buscar cuentas por mesa.
    - `Order.created_at`: Optimiza el ordenamiento cronológico.
    - `OrderItem.order_id`: Acelera la carga de detalles de una orden.
- [x] **Indexación Financiera:**
    - `Payment.order_id`: Relación rápida entre pagos y cuentas.
    - `Payment.timestamp`: Reportes de ventas por rango de tiempo.

## Fase 2: Eficiencia en el Catálogo (Paginación y Búsqueda)
*Objetivo: Reducir el consumo de memoria y ancho de banda al manejar listas de productos.*

- [x] **Backend Service Update:**
    - Implementar `limit` y `offset` en `product_service.get_products`.
    - Añadir lógica de filtrado por texto (`search`) usando `LIKE` o `contains`.
    - Soporte para búsqueda por SKU (Código de barras).
- [x] **API Endpoint Update:**
    - Modificar `GET /catalog/products` para aceptar parámetros de consulta.
    - Asegurar que las relaciones (`selectinload`) se carguen solo para los ítems devueltos.

## Fase 3: Optimización del Sistema de Eventos
*Objetivo: Eliminar el overhead innecesario en las notificaciones en tiempo real.*

- [x] **Refactor de `trigger_standard_broadcasts`:**
    - Cambiar la lógica para abrir una **única sesión de base de datos** y pasarla a todos los tópicos.
    - Evitar el ciclo de apertura/cierre de conexiones SQLite 4 veces seguidas por cada venta.
- [x] **Mejora en `trigger_broadcast`:**
    - Permitir que reciba una sesión opcional para reutilizar conexiones existentes.

## Fase 4: Bus de Eventos Unificado y Limpieza
*Objetivo: Eliminar código ineficiente y tareas de fondo redundantes.*

- [x] **Cleanup en `sales/router.py`:**
    - [x] Eliminar la función interna `notify_iot_item` que duplicaba sesiones.
    - [x] Integrar la lógica de notificación IoT directamente en el flujo principal del Bus de Eventos de forma ligera.
- [x] **Ajuste de `OrderItemRepository`:**
    - [x] Carga opcional de relaciones para optimizar consultas de solo estado.

---

### ¿Cómo proceder?
Recomiendo empezar por la **Fase 1**, ya que no rompe ninguna funcionalidad existente y prepara el terreno para las demás.
