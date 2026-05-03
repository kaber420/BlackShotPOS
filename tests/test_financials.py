import asyncio
import os
import sys
from datetime import datetime, timezone

# Añadir el directorio raíz al path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from pos_core.database import async_session_maker
from pos_core.sales.services.order_lifecycle_service import create_order, get_order_with_relations
from pos_core.sales.services.order_item_service import add_item_to_order
from pos_core.sales.payment_service import add_payment
from pos_core.sales.models import OrderType, PaymentMethod, OrderStatus
from pos_core.inventory.models import Product, Tax
from pos_core.tables.models import Table
from pos_core.customers.models import Customer

async def test_financials():
    print("--- Iniciando Test de Lógica Financiera ---")
    
    async with async_session_maker() as session:
        # 1. Crear Orden
        order = await create_order(session, OrderType.DINE_IN, waiter_name="Test Waiter")
        print(f"Orden creada: ID {order.id}")
        
        # 2. Buscar productos (creados por seed_data.py)
        from sqlmodel import select
        p_ame = (await session.execute(select(Product).where(Product.name == "Americano"))).scalar_one()
        p_cro = (await session.execute(select(Product).where(Product.name == "Croissant"))).scalar_one()
        
        # 3. Agregar items
        print(f"Agregando Americano (Precio: {p_ame.price}, Tax ID: {p_ame.tax_id})")
        item1 = await add_item_to_order(session, order.id, p_ame.id, quantity=1)
        
        print(f"Agregando Croissant (Precio: {p_cro.price}, Tax ID: {p_cro.tax_id})")
        item2 = await add_item_to_order(session, order.id, p_cro.id, quantity=1)
        
        # 4. Verificar Totales
        order = await get_order_with_relations(session, order.id)
        print(f"Subtotal: {order.subtotal} (Esperado: 75.0)")
        print(f"Impuestos: {order.tax_amount} (Esperado: {35 * 0.16} = 5.6)")
        print(f"Total: {order.total_amount} (Esperado: 80.6)")
        
        # 5. Pago Parcial
        print("\n--- Realizando Pago Parcial ---")
        p1 = await add_payment(session, order.id, PaymentMethod.CASH, amount=50.0)
        order = await get_order_with_relations(session, order.id)
        print(f"Pago 1: {p1.amount}")
        print(f"Saldo pendiente: {order.balance_due} (Esperado: 30.6)")
        print(f"Estado de la orden: {order.status}")
        
        # 6. Pago Final + Propina
        print("\n--- Realizando Pago Final con Propina ---")
        p2 = await add_payment(session, order.id, PaymentMethod.CARD, amount=30.6, tip_amount=10.0)
        order = await get_order_with_relations(session, order.id)
        print(f"Pago 2: {p2.amount}, Propina: {p2.tip_amount}")
        print(f"Saldo pendiente: {order.balance_due} (Esperado: 0.0)")
        print(f"Estado de la orden: {order.status} (Esperado: PAID)")
        
        print("\n--- Test Finalizado con Éxito ---")

if __name__ == "__main__":
    asyncio.run(test_financials())
