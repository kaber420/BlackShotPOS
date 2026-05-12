# Evolución de Módulo: Inventario (Event-Driven)

## 1. Integración con el Bus de Eventos
El módulo de Inventario dejará de ser llamado directamente por otros módulos. Ahora reaccionará a los eventos del sistema.

### Eventos Escuchados:
- `sales.order_preparing`: Dispara el descuento de stock (depletion) de los insumos según la receta.
- `sales.order_delivered`: Confirmación final de consumo.
- `inventory.adjustment_manual`: Registra mermas o entradas manuales.

## 2. El Inventory Worker
Para garantizar la integridad en SQLite, todas las escrituras de stock se centralizan en este Worker.

### Funcionamiento:
1. El Worker escucha el evento de consumo.
2. Recupera los lotes (Batches) necesarios siguiendo la lógica **FEFO**.
3. Realiza la resta atómica del stock global y del lote específico.
4. Si hay éxito, emite un evento de broadcast para actualizar la UI del POS.

## 3. Beneficios
- **Integridad**: Evita los "Lost Updates" al procesar una sola escritura a la vez.
- **Desacoplamiento**: El módulo de ventas no necesita saber nada de lotes o recetas.
