# Walkthrough: Restauración y Estabilización de la Arquitectura EDA

Este documento resume las acciones tomadas para corregir el flujo de eventos entre Ventas y Cocina, manteniendo un desacoplamiento total de dominios.

## 1. Problemas Resueltos
- **Falla en el Autodescubrimiento**: El sistema `pkgutil.walk_packages` omitía silenciosamente el módulo de Cocina. Se reemplazó por un escaneo manual via `os.walk` en `pos_core/events/discovery.py` que es 100% confiable.
- **Incompatibilidad de Base de Datos (PostgreSQL)**: Las marcas de tiempo de Cocina usaban objetos `aware` (con zona horaria) que chocaban con las columnas `TIMESTAMP WITHOUT TIME ZONE` de Postgres. Se normalizaron a `naive UTC`.
- **Eliminación de Acoplamiento en Ventas**: Se borraron los listeners en el dominio de Ventas que escuchaban a Cocina, restaurando el patrón de "Emisión Pura".
- **Limpieza de Punto de Entrada**: Se eliminaron los "hacks" de importación manual en `main.py`, confiando plenamente en el nuevo sistema de descubrimiento.

## 2. Flujo de Datos Actual
1. **Ventas** añade un producto a una orden.
2. El servicio de Ventas emite el evento `sales.items_added`.
3. El **InternalEventBus** entrega el evento a todos los suscriptores registrados (Cocina, Auditoría, etc.).
4. **Cocina** recibe el evento, consulta el área de producción del catálogo y genera los `KitchenTicket`.
5. Se dispara un broadcast de WebSocket hacia el tópico `kitchen_orders`.
6. El **KDS** recibe la actualización y muestra la orden.

## 3. Verificación Realizada
Se ejecutó un script de integración end-to-end que simuló la carga de listeners y la emisión de un evento, confirmando la creación exitosa del ticket en la base de datos PostgreSQL sin errores de sesión ni de tipos de datos.
