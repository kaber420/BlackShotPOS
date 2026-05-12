# RFC: Creación del Dominio de Cocina (Kitchen & Operations)

## 1. Visión General
Actualmente, el módulo de **Ventas (Sales)** actúa como un "Pulpo" que gestiona no solo la transacción financiera, sino también el flujo operativo del restaurante (estados de preparación, asignación de cocineros, tiempos de cocina). 

Este documento propone la creación de un módulo independiente `pos_core/kitchen` que asuma la responsabilidad total del **Flujo de Trabajo** del restaurante, permitiendo que Ventas sea un emisor puro de transacciones.

## 2. El Problema: Acoplamiento en Ventas
Actualmente, el modelo `OrderItem` en el dominio de Ventas contiene campos que son puramente operativos:
- `status` (PENDING, PREPARING, READY, DELIVERED)
- `cook_uuid` / `cook_name`
- `preparing_at` / `ready_at` / `delivered_at`

Esto obliga a que los servicios de Ventas tengan lógica de "Cocina", lo cual viola el principio de responsabilidad única y ensucia el dominio comercial con detalles de implementación de la producción.

## 3. Propuesta: Módulo `pos_core/kitchen`

### 3.1. Responsabilidades
- **Gestión de Comandas:** Seguimiento del ciclo de vida de cada plato.
- **Áreas de Producción:** Administración de colas de trabajo por área (Parrilla, Barra, etc.).
- **Métricas de Eficiencia:** Registro de tiempos de preparación y desempeño por cocinero.
- **Hardware de Impresión:** Orquestación de impresoras térmicas (actualmente en un limbo).

### 3.2. Modelo de Datos Sugerido
```python
class KitchenTicket(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int # Referencia a la venta
    item_id: int  # Referencia al item original
    product_name: str
    production_area_id: int
    
    status: KitchenStatus # PENDING, PREPARING, READY
    cook_uuid: Optional[str]
    
    received_at: datetime
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
```

## 4. Flujo Event-Driven (EDA)

1.  **Emisión (Sales):** Cuando una orden es confirmada o pagada, Ventas emite `sales.order_created` o `sales.payment_received`.
2.  **Reacción (Kitchen):** El listener de Cocina captura el evento, consulta el Catálogo para ver a qué áreas pertenecen los productos, y crea los `KitchenTicket`.
3.  **Operación (Kitchen):** El cocinero interactúa con el API de `/kitchen`. Al terminar un plato, el módulo emite `kitchen.item_ready`.
4.  **Notificación (UI/Sales):** El frontend (o un listener de notificaciones) reacciona a `kitchen.item_ready` para avisar al mesero. Ventas ya no necesita saber qué pasó en la cocina.

## 5. Plan de Ejecución
1.  **Fase 1 (Músculo):** Crear la estructura de `pos_core/kitchen` (models, repository, services).
2.  **Fase 2 (Trasplante):** Mover la lógica de `ProductionArea` y el servicio de impresión de comandas al nuevo módulo.
3.  **Fase 3 (Limpieza):** Eliminar los campos de cocina de `OrderItem` y refactorizar el KDS para que consuma del nuevo endpoint `/api/v1/kitchen`.

---
**Estado:** Borrador de Arquitectura  
**Objetivo:** Limpiar el módulo de Ventas y profesionalizar la operativa de cocina.
