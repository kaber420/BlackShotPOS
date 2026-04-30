"""
pos_core/sales/payment_service.py
==================================
Servicio de Pagos: responsabilidad única de registrar transacciones financieras.

REGLA DE ORO:
  Este módulo NO debe importar ni conocer pos_core.tables.
  La coordinación "pagar + liberar mesa" es responsabilidad del Router (orquestador).
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from .models import Payment, PaymentMethod, OrderStatus
from .repository import order_repo, item_repo
from pos_core.exceptions import OrderNotFoundError, InvalidOrderStateError
from pos_core.inventory.services.stock_service import process_inventory_depletion
from bs_sync.service import enqueue_event


async def add_payment(
    session: AsyncSession,
    order_id: int,
    method: PaymentMethod,
    amount: float,
    received_amount: Optional[float] = None,
    tip_amount: float = 0.0,
) -> Payment:
    """
    Registra un pago (total o parcial) y opcionalmente una propina.
    Actualiza el estado de la orden si se cubre el total.
    """
    # Cargamos con relaciones para calcular el balance_due
    order = await order_repo.get_with_relations(session, order_id)
    if not order:
        raise OrderNotFoundError(order_id)
    
    current_balance = order.balance_due
    if current_balance <= 0 and tip_amount <= 0:
         raise InvalidOrderStateError("Esta orden ya está liquidada y no se especificó propina.")

    # 1. Validar montos
    # Si el monto pagado es mayor al saldo, el excedente podría ser propina o cambio.
    # Por simplicidad, el 'amount' es lo que se abona a la deuda.
    applied_to_order = min(amount, current_balance)
    
    # Si el usuario envió más de lo que se debe, y no especificó tip_amount, 
    # podríamos asumir que la diferencia es propina o simplemente registrarlo como pago.
    # Pero seguiremos la instrucción: amount es el abono, tip_amount es la propina.
    
    actual_received = received_amount if received_amount is not None else (amount + tip_amount)
    change = max(0.0, actual_received - (amount + tip_amount))

    # 2. Registrar el pago
    payment = await order_repo.create_payment(
        session, 
        order_id, 
        method, 
        amount=amount, # El abono real a la cuenta
        received_amount=actual_received,
        change_amount=change,
        tip_amount=tip_amount
    )
    
    # Forzar actualización de la relación de pagos para el cálculo de balance_due
    # (SQLModel/SQLAlchemy a veces necesita esto si no se hace commit)
    if payment not in order.payments:
        order.payments.append(payment)

    # 3. Actualizar estado de la orden
    if order.balance_due <= 0:
        order.status = OrderStatus.PAID
    elif order.status == OrderStatus.PENDING:
        # Si se hizo un pago parcial, la orden ya no está 'pendiente' de iniciar
        order.status = OrderStatus.PREPARING

    # 4. Manejo de Inventario: Descontar stock al recibir el primer pago si estaba PENDING
    if order.status == OrderStatus.PREPARING and any(i.status == OrderStatus.PENDING for i in order.items):
        await process_inventory_depletion(session, order.items)
        for item in order.items:
            if item.status == OrderStatus.PENDING:
                item.status = OrderStatus.PREPARING

    await order_repo.save(session, order)
    
    # 5. Sincronización Central
    await enqueue_event(session, "sales.payment_added", {
        "order_id": order.id,
        "payment_id": payment.id,
        "amount": amount, 
        "tip_amount": tip_amount,
        "method": payment.method,
        "is_final_payment": order.status == OrderStatus.PAID,
        "balance_remaining": order.balance_due
    })

    await session.commit()
    await session.refresh(payment)
    return payment
