"""
pos_core/sales/payment_service.py
==================================
Servicio de Pagos: responsabilidad única de registrar transacciones financieras.

REGLA DE ORO:
  Este módulo NO debe importar ni conocer pos_core.tables.
  La coordinación "pagar + liberar mesa" es responsabilidad del Router (orquestador).
"""
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from .models import Payment, PaymentMethod, OrderStatus
from .repository import order_repo, item_repo
from pos_core.exceptions import OrderNotFoundError, InvalidOrderStateError
from pos_core.inventory.service import process_inventory_depletion
from bs_sync.service import enqueue_event


async def add_payment(
    session: AsyncSession,
    order_id: int,
    method: PaymentMethod,
    amount: float,
) -> Payment:
    """
    Registra un pago y marca la orden como pagada (is_paid=True).
    
    LÓGICA DE NEGOCIO ACTUALIZADA:
    - Si la orden ya está ENTREGADA, se mueve a status PAID (terminal).
    - Si la orden está en PENDING/PREPARING, se mantiene su status operativo
      para que siga apareciendo en Cocina (KDS), pero con la marca de pagado.
    - Si la orden era PENDING, se dispara la depleción de inventario al pagar.
    """
    order = await order_repo.get_by_id(session, order_id)
    if not order:
        raise OrderNotFoundError(order_id)
    if order.is_paid:
        raise InvalidOrderStateError("Esta orden ya fue pagada.")

    # 1. Registrar el pago
    payment = await order_repo.create_payment(session, order_id, method, amount)
    order.is_paid = True

    # 2. Manejo de Inventario: Si estaba en PENDING, descontar stock ahora que hay dinero de por medio
    if order.status == OrderStatus.PENDING:
        order_items = await item_repo.get_items_for_order(session, order_id)
        if order_items:
            await process_inventory_depletion(session, order_items)
            # Avanzamos los ítems a PREPARING para que cocina sepa que ya puede empezar
            for item in order_items:
                if item.status == OrderStatus.PENDING:
                    item.status = OrderStatus.PREPARING
            order.status = OrderStatus.PREPARING

    # 3. La orden mantiene su status operativo (PENDING/PREPARING/READY/DELIVERED)
    # No la movemos a un estado terminal 'PAID' para no perder el contexto de servicio.

    await order_repo.save(session, order)
    
    # Encolar evento para sincronización SaaS
    await enqueue_event(session, "sales.payment_added", {
        "order_id": order.id,
        "payment_id": payment.id,
        "amount": payment.amount,
        "method": payment.method,
        "timestamp": str(payment.timestamp)
    })

    await session.commit()
    await session.refresh(payment)
    return payment
