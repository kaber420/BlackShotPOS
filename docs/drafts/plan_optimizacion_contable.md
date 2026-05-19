# Plan de Optimización Contable y Correcciones en BlackShot POS

Este plan detalla las propuestas para solucionar las inconsistencias identificadas durante la auditoría del módulo contable y el motor de cobros en BlackShot POS, mejorando el rendimiento y la precisión de los datos en tiempo real.

---

## 1. Resumen de Hallazgos y Soluciones Propuestas

### A. Descuadre en Tiempo Real de Caja Chica (Sobrepagos)
*   **Problema:** Al registrar un sobrepago en efectivo (ej. pagar una cuenta de `$80` con un billete de `$100`), la base de datos registra correctamente la deuda saldada de `$80` y el vuelto de `$20`. Sin embargo, el evento `"sales.payment_received"` envía el monto bruto recibido (`100.0`). El listener de contabilidad incrementa el total esperado de caja (`expected_cash`) por `$100`, inflándolo erróneamente en tiempo real hasta que el turno se cierra y se recalcula.
*   **Solución:** Modificar la publicación del evento en `payment_service.py` para que envíe `payment.amount` (el abono neto real de `$80`) en lugar de `amount` (el billete recibido bruto de `$100`).

### B. Patrón de Consultas N+1 en Historial de Turnos (`list_shifts`)
*   **Problema:** El listado histórico de turnos ejecuta las funciones `calculate_shift_totals` y una consulta de propinas individual para cada uno de los turnos en un bucle `for`. Si se solicitan 50 turnos, el sistema realiza **150 consultas SQL adicionales** individuales.
*   **Solución:** Rediseñar `list_shifts` en `pos_core/accounting/service.py` para precargar todos los totales de ventas y propinas de los turnos solicitados en una única consulta agregada agrupada por `shift_id` (`bulk query`), eliminando las consultas N+1 por completo.

### C. Conflicto de Datos en Suite de Pruebas (`test_accounting_enhanced.py`)
*   **Problema:** La suite falla con un error `IntegrityError` debido a la inserción de claves duplicadas si la categoría `"Comida"` o el producto `"Taco"` ya existen en la base de datos de desarrollo.
*   **Solución:** Modificar la preparación de datos en la prueba para que verifique primero si la categoría y el producto existen (usando `select`), y los cree únicamente si es necesario.

---

## 2. Plan Técnico Detallado de Modificaciones

### Modificación 1: Módulo de Ventas (`pos_core/sales/payment_service.py`)

**Archivo:** [payment_service.py](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/pos_core/sales/payment_service.py)
**Línea aproximada:** 81

```python
# ANTES
await event_bus.publish("sales.payment_received", {
    "order_id": order.id,
    "table_id": order.table_id,
    "shift_id": order.shift_id,
    "payment_id": payment.id,
    "amount": amount,  # <-- Envía el monto recibido bruto (ej. 100.0)
    "method": payment.method,
    "tip_amount": tip_amount,
    "vacate_table": vacate_table
})

# DESPUÉS
await event_bus.publish("sales.payment_received", {
    "order_id": order.id,
    "table_id": order.table_id,
    "shift_id": order.shift_id,
    "payment_id": payment.id,
    "amount": payment.amount,  # <-- Envía el abono real neto (ej. 80.0)
    "method": payment.method,
    "tip_amount": tip_amount,
    "vacate_table": vacate_table
})
```

---

### Modificación 2: Módulo Contable (`pos_core/accounting/service.py`)

**Archivo:** [service.py](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/pos_core/accounting/service.py)
**Línea aproximada:** 243

Se rediseñará la función `list_shifts` para cargar la información financiera utilizando consultas agrupadas eficientes en base de datos.

```python
async def list_shifts(session: AsyncSession, limit: int = 50, offset: int = 0) -> list:
    # 1. Obtener la lista base de turnos
    stmt = select(Shift).order_by(Shift.start_time.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    shifts = result.scalars().all()

    shift_ids = [s.id for s in shifts]
    if not shift_ids:
        return []

    # 2. ÚNICA CONSULTA: Obtener ventas y propinas agrupadas por shift_id y método de pago
    pay_stmt = (
        select(
            Order.shift_id,
            Payment.method,
            sqlfunc.coalesce(sqlfunc.sum(Payment.amount), 0.0).label("amount_sum"),
            sqlfunc.coalesce(sqlfunc.sum(Payment.tip_amount), 0.0).label("tip_sum")
        )
        .join(Payment, Payment.order_id == Order.id)
        .where(Order.shift_id.in_(shift_ids))
        .group_by(Order.shift_id, Payment.method)
    )
    pay_res = await session.execute(pay_stmt)

    # 3. Mapear resultados en memoria
    sales_map = {sid: {PaymentMethod.CASH: 0.0, PaymentMethod.CARD: 0.0, PaymentMethod.TRANSFER: 0.0} for sid in shift_ids}
    tips_map = {sid: 0.0 for sid in shift_ids}

    for shift_id, method, amount_sum, tip_sum in pay_res.all():
        if shift_id in sales_map:
            sales_map[shift_id][method] = float(amount_sum or 0.0)
        if shift_id in tips_map:
            tips_map[shift_id] += float(tip_sum or 0.0)

    # 4. Construir respuesta mapeada sin consultas adicionales (0 consultas adicionales en bucle)
    out = []
    for shift in shifts:
        duration_minutes: Optional[int] = None
        if shift.end_time and shift.start_time:
            start = shift.start_time.replace(tzinfo=timezone.utc) if shift.start_time.tzinfo is None else shift.start_time
            end = shift.end_time.replace(tzinfo=timezone.utc) if shift.end_time.tzinfo is None else shift.end_time
            duration_minutes = int((end - start).total_seconds() // 60)

        s_totals = sales_map.get(shift.id, {PaymentMethod.CASH: 0.0, PaymentMethod.CARD: 0.0, PaymentMethod.TRANSFER: 0.0})
        cash_sales = s_totals.get(PaymentMethod.CASH, 0.0)
        card_sales = s_totals.get(PaymentMethod.CARD, 0.0)
        transfer_sales = s_totals.get(PaymentMethod.TRANSFER, 0.0)
        tips_total = tips_map.get(shift.id, 0.0)

        out.append({
            "id": shift.id,
            "register_id": shift.register_id,
            "status": shift.status,
            "start_time": shift.start_time.isoformat() if shift.start_time else None,
            "end_time": shift.end_time.isoformat() if shift.end_time else None,
            "duration_minutes": duration_minutes,
            "initial_cash": shift.initial_cash,
            "expected_cash": shift.expected_cash,
            "actual_cash": shift.actual_cash,
            "difference_cash": shift.difference_cash,
            "sales": {
                "cash": round(cash_sales, 2),
                "card": round(card_sales, 2),
                "transfer": round(transfer_sales, 2),
                "total": round(cash_sales + card_sales + transfer_sales, 2),
            },
            "tips_total": round(tips_total, 2),
        })

    return out
```

---

### Modificación 3: Suite de Pruebas (`tests/test_accounting_enhanced.py`)

**Archivo:** [test_accounting_enhanced.py](file:///home/kaberromero/Documentos/proyectos/BlackShotPOS/tests/test_accounting_enhanced.py)
**Líneas afectadas:** 54-61

```python
# ANTES
cat = Category(name="Comida")
session.add(cat)
await session.flush()

prod = Product(name="Taco", price=50.0, category_id=cat.id)
session.add(prod)
await session.flush()

# DESPUÉS
cat_stmt = select(Category).where(Category.name == "Comida")
cat = (await session.execute(cat_stmt)).scalar_one_or_none()
if not cat:
    cat = Category(name="Comida")
    session.add(cat)
    await session.flush()

prod_stmt = select(Product).where(Product.name == "Taco")
prod = (await session.execute(prod_stmt)).scalar_one_or_none()
if not prod:
    prod = Product(name="Taco", price=50.0, category_id=cat.id)
    session.add(prod)
    await session.flush()
```

---

## 3. Plan de Verificación

1.  **Ejecución de Pruebas Automatizadas:**
    Ejecutar secuencialmente las tres suites de pruebas para certificar el correcto funcionamiento de las validaciones de robustez, flujos de caja chica y motor de cobros:
    ```bash
    .venv/bin/python tests/test_accounting_fix.py
    .venv/bin/python tests/test_accounting_robustness.py
    .venv/bin/python tests/test_accounting_enhanced.py
    ```
2.  **Verificación de Desempeño (Consultas SQL):**
    Comprobar mediante logs de consola que el listado de turnos se ejecuta de forma inmediata con una única consulta SQL de agregación para las propinas y ventas de todos los turnos.
