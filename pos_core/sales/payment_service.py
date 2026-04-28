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
    
    LÓGICA DE CONTADURÍA:
    - amount: El ingreso real (revenue), limitado al total de la orden.
    - received_amount: El efectivo/monto total que entregó el cliente.
    - change_amount: El cambio devuelto (received - total).
    """
    # Cargamos con relaciones para calcular el total
    order = await order_repo.get_with_relations(session, order_id)
    if not order:
        raise OrderNotFoundError(order_id)
    if order.is_paid:
        raise InvalidOrderStateError("Esta orden ya fue pagada.")

    # 1. Calcular totales reales
    total_revenue = order.total_price
    received = amount
    change = max(0.0, received - total_revenue)

    # 2. Registrar el pago con desglose
    payment = await order_repo.create_payment(
        session, 
        order_id, 
        method, 
        amount=total_revenue,  # La ganancia real
        received_amount=received,
        change_amount=change
    )
    order.is_paid = True

    # 3. Manejo de Inventario: Si estaba en PENDING, descontar stock ahora que hay dinero de por medio
    if order.status == OrderStatus.PENDING:
        # Los ítems ya vienen precargados por get_with_relations
        if order.items:
            await process_inventory_depletion(session, order.items)
            # Avanzamos los ítems a PREPARING para que cocina sepa que ya puede empezar
            for item in order.items:
                if item.status == OrderStatus.PENDING:
                    item.status = OrderStatus.PREPARING
            order.status = OrderStatus.PREPARING

    await order_repo.save(session, order)
    
    # 4. Encolar evento para sincronización SaaS
    # Detalle de productos para analíticas centralizadas
    detailed_items = [
        {
            "name": item.product.name,
            "quantity": item.quantity,
            "price": item.unit_price
        }
        for item in order.items if item.status != OrderStatus.CANCELLED
    ]

    # IMPORTANTE: Enviamos el total_revenue como 'amount' para que el Central cuadre sus cuentas.
    await enqueue_event(session, "sales.payment_added", {
        "order_id": order.id,
        "payment_id": payment.id,
        "amount": total_revenue, 
        "received_amount": received,
        "change_amount": change,
        "method": payment.method,
        "timestamp": str(payment.timestamp),
        "items": detailed_items,
        "items_count": sum(i.quantity for i in order.items if i.status != OrderStatus.CANCELLED)
    })

    await session.commit()
    await session.refresh(payment)
    return payment
