# Especificación de Protocolo IoT v3.0 (Seguimiento Granular)

**Estado:** Propuesta para Equipo de POS / Backend
**Objetivo:** Permitir el seguimiento individual de cada artículo dentro de una orden para eliminar ambigüedad y mejorar la experiencia del comensal.

---

## 1. El Concepto de Identidad Única
Actualmente, el TablePad agrupa artículos por nombre o índice. En órdenes con múltiples artículos idénticos (ej. 3 Cervezas), no hay forma de saber cuál de las tres ha sido servida o preparada.

**Requerimiento POS:** Cada artículo de la orden debe viajar con un `id` único (ID de instancia de compra) que persista durante toda la sesión.

---

## 2. Cambios en Mensajes Recibidos (POS → IoT)

### A. Nueva Orden (`order_new`)
Se introduce el campo `id` obligatorio dentro de cada objeto del array `items`.

```json
{
  "event": "order_new",
  "data": {
    "order_id": 108,
    "table_id": 1,
    "status": "PREPARANDO",
    "items": [
      {
        "id": 15024,      // ID Único de este platillo específico
        "name": "Latte en las rocas",
        "qty": 1,
        "status": "PREPARANDO"
      },
      {
        "id": 15025,      // ID Único diferente al anterior
        "name": "Latte en las rocas",
        "qty": 1,
        "status": "EN COLA"
      }
    ]
  }
}
```

### B. Actualización de Artículo (`order_update` Granular)
Para actualizar un solo plato sin afectar al resto de la orden, el POS debe enviar el `item_id`.

```json
{
  "event": "order_update",
  "data": {
    "order_id": 108,
    "item_id": 15024,       // El terminal buscará este ID para actualizar
    "item_status": "LISTO", // Estado específico del platillo
    "progress": 100
  }
}
```

> [!IMPORTANT]
> **Compatibilidad Legacy**: Si el mensaje `order_update` se envía sin `item_id`, el TablePad asumirá que es una actualización global y marcará toda la orden (todos los platos) con el nuevo estado.

---

## 3. Beneficios Técnicos y Operativos
1. **Precisión Total**: El cliente visualiza el progreso real de su pedido plato por plato.
2. **Reducción de Latencia Cognitiva**: Los meseros no necesitan explicar "cuál de los lattes está listo", el dispositivo lo indica por ID.
3. **Sincronización KDS**: El estado del KDS (Kitchen Display System) se refleja 1:1 en la mesa del cliente.

---

## 4. Notas de Implementación (POS)
- Los IDs deben ser únicos al menos dentro del ciclo de vida de la mesa/sesión.
- Se recomienda usar el ID de la tabla `order_items` de la base de datos para garantizar unicidad.
- El campo `item_status` debe mapear con los estados estándar del TablePad: `EN COLA`, `PREPARANDO`, `LISTO`, `ENTREGADO`.
