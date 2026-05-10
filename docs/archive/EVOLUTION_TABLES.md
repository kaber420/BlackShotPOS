# Evolución de Módulo: Mesas (Event-Driven)

## 1. Visión y Desacoplamiento
El objetivo es que el módulo de Mesas sea el único responsable de gestionar el estado de las entidades `Table`. El módulo de Ventas no debe modificar la base de datos de mesas directamente ni importar sus modelos.

## 2. Flujo de Trabajo Basado en Eventos
Se preserva el flujo de trabajo actual, pero se desacopla mediante el `InternalEventBus`.

### Eventos y Reacciones:

- **`sales.order_created`**: 
  - *Contexto*: Se abre una nueva cuenta en una mesa.
  - *Acción*: Mesa pasa a `OCCUPIED`. Se registra `occupied_at` (timestamp actual).
  
- **`sales.order_cancelled` / `sales.order_deleted`**:
  - *Contexto*: La orden se cancela o se elimina (si estaba vacía).
  - *Acción*: Mesa pasa a `FREE`. Se limpia `occupied_at`.

- **`sales.payment_added`**:
  - *Contexto*: Se registra un pago.
  - *Metadato*: `vacate_table: bool`.
  - *Acción*: Si `vacate_table` es `True`, la mesa pasa a `FREE`. Esto permite pagos parciales o anticipados sin liberar la mesa automáticamente.

- **`sales.table_transferred`**:
  - *Contexto*: Una orden se mueve de la Mesa A a la Mesa B.
  - *Acción*: 
    1. Mesa A pasa a `FREE`.
    2. Mesa B pasa a `OCCUPIED`.
    3. El `occupied_at` de la Mesa A se transfiere a la Mesa B para mantener la métrica de tiempo de servicio real.

- **`table.manual_vacate`**:
  - *Contexto*: El administrador libera una mesa manualmente desde el dashboard.
  - *Acción*: Mesa pasa a `FREE`.

## 3. Lógica de Negocio Preservada
Este plan **no altera** el comportamiento del POS:
1. **No hay liberación automática por pago**: Se respeta la decisión del mesero/cajero (flag `vacate_table`).
2. **Consistencia de Tiempo**: Las transferencias no reinician el reloj de la mesa.
3. **División de Cuentas**: Al dividir una orden, ambas permanecen vinculadas a la misma mesa, por lo que el estado no cambia hasta que la última orden sea liberada o pagada con salida.

## 4. Beneficios Técnicos
- **Eliminación de Importaciones Circulares**: Ventas ya no necesita importar `Table` ni `table_service`.
- **Atomicidad**: El estado de la mesa es una consecuencia garantizada de la vida de la orden.
- **Extensibilidad**: Otros módulos (ej: IoT para luces en mesa) pueden escuchar estos mismos eventos sin tocar el código de Ventas.
