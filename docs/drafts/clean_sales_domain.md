# Plan de Limpieza y Desacoplamiento: Dominio de Ventas vs Cocina

## 1. El Problema Actual
El módulo de Ventas (`pos_core/sales`) está actuando como el "cerebro" operativo, gestionando estados como `PREPARING` y `READY`, y proveyendo datos agregados de cocina. Esto viola el principio de EDA y ensucia el dominio de Ventas con lógica que no le corresponde (logística de cocina).

## 2. Objetivo
Devolver a Ventas su propósito original: **Registrar transacciones financieras**.
Trasladar a Cocina su propósito operativo: **Gestionar el ciclo de vida del pedido (Comanda)**.

## 3. Acciones de Limpieza

### A. Dominio de Ventas (Limpieza)
- **Eliminar Estados Operativos**: El modelo `Order` en Ventas no debería preocuparse por si algo se está preparando. Solo debería tener estados comerciales: `PENDING` (por cobrar), `PAID` (cobrado), `CANCELLED` (anulado).
- **Remover Proveedores Agregados**: El proveedor `recent_orders` que actualmente vive en `sales/providers.py` debe ser trasladado a Cocina.
- **Eliminar Servicios de Ciclo de Vida**: `order_lifecycle_service.py` debe ser desmantelado. La creación de la orden solo emite un evento y Cocina se encarga del resto.

### B. Dominio de Cocina (Empoderamiento)
- **Gestor de la Verdad Operativa**: Cocina será el encargado de proveer la lista de "Órdenes Activas" para los meseros.
- **Nuevos Proveedores**: Crear un proveedor en Cocina que tome las órdenes activas del turno y las enriquezca con el estado de los tickets de cocina.
- **Nuevos Listeners**: Cocina escuchará `sales.order_created` para inicializar sus tickets y gestionará la entrega.

### C. Flujo Event-Driven (EDA Puro)
1. **Ventas** emite `sales.order_created`.
2. **Cocina** recibe el evento, crea los `KitchenTicket` y asume el control de esa orden en la pantalla de meseros y KDS.
3. **Ventas** solo vuelve a intervenir cuando el mesero pulsa "Cobrar".
4. Al cobrar, **Ventas** emite `sales.payment_received`.
5. **Cocina** escucha el pago y, si la orden ya está entregada, la archiva (desaparece de la pantalla de la seccion de ordenes por que de cocina desaparece al estar listo por que no le importa si esta entregada o si esta pagada por que no es de su competencia).

## 4. Pasos para la Refactorización (Sin romper el programa)
1. Migrar el Topic Provider `recent_orders` de `sales/providers.py` a `kitchen/providers.py`.
2. Refactorizar `OrderCard.svelte` (frontend) para que consuma la información desde el nuevo enfoque de Cocina.
3. Limpiar los servicios de Ventas eliminando referencias a estados de preparación.
4. Eliminar archivos redundantes (`order_lifecycle_service.py`).

---
**Nota:** Este plan asegura que si Cocina falla, Ventas sigue pudiendo cobrar, y si Ventas falla, Cocina sigue pudiendo cocinar. Independencia total.
