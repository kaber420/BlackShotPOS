import asyncio
import os
import sys
from uuid import uuid4

# Añadir la raíz del proyecto al path para importaciones
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.ext.asyncio import AsyncSession
from pos_core.database import async_session_maker
from pos_core.accounting.models import CashMovementType, CashRegister, Shift, CashMovement
from pos_core.accounting import service as accounting_service
from pos_core.auth.models import User
from pos_core.sales.models import Order, Payment, PaymentMethod, OrderType, OrderItem
from pos_core.catalog.models import Category, Product, ProductVariant
from pos_core.inventory.models import Ingredient
from pos_core.tables.models import Table
from pos_core.settings.models import BusinessSettings
from pos_core.iot.models import IoTDevice
from pos_core.customers.models import Customer
from bs_sync.models import SyncEvent
from pos_core.sales import order_service, payment_service
from pos_core.kitchen.models import ProductionArea
from sqlmodel import select

async def test_accounting_enhanced():
    async with async_session_maker() as session:
        print("\n🧪 Probando Cash Management Mejorado...")
        
        # 1. Preparar datos base (Caja y Usuario)
        reg_stmt = select(CashRegister).where(CashRegister.name == "Caja Test")
        register = (await session.execute(reg_stmt)).scalar_one_or_none()
        if not register:
            register = await accounting_service.create_cash_register(session, "Caja Test")
            print(f"✅ Caja creada ID: {register.id}")
        
        user_stmt = select(User).limit(1)
        user = (await session.execute(user_stmt)).scalar_one_or_none()
        if not user:
            user = User(id=uuid4(), email="test@blackshot.app", hashed_password="xxx", is_active=True)
            session.add(user)
            await session.commit()
            await session.refresh(user)
            print(f"✅ Usuario test creado ID: {user.id}")

        # 2. Abrir Turno
        print(f"🚀 Abriendo turno con $500...")
        shift = await accounting_service.open_shift(session, initial_cash=500.0, register_id=register.id, user_id=user.id)
        print(f"✅ Turno abierto ID: {shift.id}")

        # 3. Simular Ventas
        print("💰 Simulando ventas...")
        
        # Crear un producto para las ventas
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

        # Venta Efectivo: $100 (2 Tacos)
        order1 = await order_service.create_order(session, OrderType.TAKEAWAY)
        await order_service.add_item_to_order(session, order1.id, prod.id, quantity=2)
        await payment_service.add_payment(session, order1.id, PaymentMethod.CASH, amount=100.0)
        
        # Venta Tarjeta: $250 (5 Tacos)
        order2 = await order_service.create_order(session, OrderType.TAKEAWAY)
        await order_service.add_item_to_order(session, order2.id, prod.id, quantity=5)
        await payment_service.add_payment(session, order2.id, PaymentMethod.CARD, amount=250.0)

        # 4. Registrar Movimientos
        print("💸 Registrando movimientos...")
        # Entrada: $200 (Refuerzo)
        await accounting_service.add_cash_movement(
            session, shift.id, amount=200.0, type=CashMovementType.INCOME, reason="Refuerzo", user_id=user.id
        )
        # Salida: $50 (Pago basura)
        await accounting_service.add_cash_movement(
            session, shift.id, amount=50.0, type=CashMovementType.EXPENSE, reason="Basura", user_id=user.id
        )

        # 5. Cerrar Turno
        print("🔒 Cerrando turno...")
        # Cerramos con $760 (sobran $10)
        closed_shift = await accounting_service.close_shift(
            session, 
            shift.id, 
            actual_cash=760.0, 
            actual_card=250.0, 
            notes="Sobró un billete de 10"
        )

        print("\n📊 RESULTADOS DEL CORTE:")
        print(f"   - Expected Cash: ${closed_shift.expected_cash}")
        print(f"   - Actual Cash:   ${closed_shift.actual_cash}")
        print(f"   - Difference:    ${closed_shift.difference_cash}")
        print(f"   - Expected Card: ${closed_shift.expected_card}")
        
        assert closed_shift.expected_cash == 750.0
        assert closed_shift.actual_cash == 760.0
        assert closed_shift.difference_cash == 10.0
        assert closed_shift.expected_card == 250.0
        assert closed_shift.notes == "Sobró un billete de 10"

        # 6. Reporte
        report = await accounting_service.get_shift_report(session, closed_shift.id)
        print(f"✅ Reporte generado: {len(report['movements'])} movimientos")
        assert len(report["movements"]) == 2
        
        print("\n✨ ¡PRUEBA DE CASH MANAGEMENT EXITOSA!")

if __name__ == "__main__":
    asyncio.run(test_accounting_enhanced())
